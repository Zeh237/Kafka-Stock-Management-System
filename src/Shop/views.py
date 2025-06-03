import logging
from src.kafka.connection import KafkaConnection
from flask import render_template, request, redirect, url_for, flash
from src.Shop.validation import ProductCreateCommand
import os
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'assets', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class ShopViews:
    def __init__(self):
        self.kafka_connection = KafkaConnection()

    def create_product(self):
        """
        Handles product creation with robust validation before Kafka.
        Generates UUID for product and produces CreateProductCommand.
        """
        if request.method == 'GET':
            return render_template('shop/create_product.html')

        elif request.method == 'POST':
            producer = self._get_kafka_producer()
            kafka_conn = self._get_kafka_connection()
            image_path = None

            try:
                product_image = request.files.get('image')
                if not product_image:
                    flash("Product image is required", "warning")
                    return render_template('shop/create_product.html', form_data=request.form), 400

                if not allowed_file(product_image.filename):
                    flash("Invalid image type (allowed: PNG, JPG, JPEG, GIF)", "warning")
                    return render_template('shop/create_product.html', form_data=request.form), 400

                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                original_filename = secure_filename(product_image.filename)
                filename_parts = os.path.splitext(original_filename)
                unique_filename = f"{uuid.uuid4()}{filename_parts[1]}"
                image_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                product_image.save(image_path)
                image_url = f"/uploads/{unique_filename}"

                try:
                    product_data = ProductCreateCommand(
                        name=request.form.get('name', '').strip(),
                        price=float(request.form.get('price', 0)),
                        description=request.form.get('description', '').strip(),
                        stock_quantity=int(request.form.get('stock_quantity', 0)),
                        image_url=image_url
                    )
                except ValueError as e:
                    # Clean up image if validation fails
                    if image_path and os.path.exists(image_path):
                        os.remove(image_path)
                    flash(f"Validation error: {str(e)}", "warning")
                    return render_template('shop/create_product.html', form_data=request.form), 400

                product_id = str(uuid.uuid4())
                if not producer or not kafka_conn:
                    if image_path and os.path.exists(image_path):
                        os.remove(image_path)
                    flash("System error: Unable to process request", "error")
                    return render_template('shop/create_product.html', form_data=request.form), 500

                command_message = {
                    "command_id": str(uuid.uuid4()),
                    "command_type": "CreateProductCommand",
                    "timestamp": datetime.utcnow().isoformat() + 'Z',
                    "payload": {
                        "product_id": product_id,
                        "name": product_data.name,
                        "price": product_data.price,
                        "description": product_data.description,
                        "image_url": product_data.image_url,
                        "initial_stock_quantity": product_data.stock_quantity
                    }
                }

                kafka_conn.produce_message(
                    producer,
                    topic='product_commands',
                    message_obj=command_message,
                    key=product_id
                )

                logger.info(f"Created product command for {product_id}")
                flash("Product creation request received!", "success")
                return redirect(url_for('shop.list_products'))

            except Exception as e:
                logger.error(f"Product creation failed: {str(e)}", exc_info=True)
                if image_path and os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except OSError:
                        logger.error("Failed to clean up image")
                
                flash("An unexpected error occurred. Please try again.", "error")
                return render_template('shop/create_product.html', form_data=request.form), 500

        return "Method Not Allowed", 405

    def update_product(self):
        """update product"""
        pass

    def delete_product(self):
        """delete product"""
        pass

    def list_products(self):
        """list products"""
        pass

    def get_product(self):
        """get product"""
        pass