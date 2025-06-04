import logging
from flask import current_app, render_template, request, redirect, url_for, flash
from src.Shop.validation import ProductCreateCommand
import os
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime
from src.Shop.model import Products, Inventory
from src import db
import time


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'src', 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class ShopViews:
    def __init__(self):
        pass

    def _get_kafka_producer(self):
        return current_app.kafka_producer
    
    def _get_kafka_connection(self):
        return current_app.kafka_connection

    def create_product(self):
        """
        Handles product creation to Kafka.
        """
        if request.method == 'GET':
            return render_template('shop/create_product.html', form_data={})

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
                        "initial_stock_quantity": product_data.stock_quantity,
                        "created_at": datetime.utcnow().isoformat() + 'Z',
                        "updated_at": datetime.utcnow().isoformat() + 'Z'
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
                time.sleep(2)
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
    
    def home(self):
        return render_template('shop/home.html')

    def update_product(self):
        """update product"""
        pass

    def delete_product(self, product_id):
        if request.method == 'POST':
            producer = self._get_kafka_producer()
            kafka_conn = self._get_kafka_connection()
            
            try:
                product = Products.query.get(product_id)
                if not product:
                    flash("Product not found", "warning")
                    return redirect(url_for('shop.list_products'))

                inventory_item = Inventory.query.filter_by(product_id=product_id).first()

                # Deleting image file from file system
                if product.image_url:
                    absolute_image_path = os.path.join(os.getcwd(), 'src', 'static', product.image_url)
                    if os.path.exists(absolute_image_path):
                        os.remove(absolute_image_path)

                # Delete from DB
                db.session.delete(product)
                if inventory_item:
                    db.session.delete(inventory_item)
                db.session.commit()

                # Sending Kafka Delete Command
                command_message = {
                    "command_id": str(uuid.uuid4()),
                    "command_type": "DeleteProductCommand",
                    "timestamp": datetime.utcnow().isoformat() + 'Z',
                    "payload": {
                        "product_id": product_id
                    }
                }
                kafka_conn.produce_message(
                    producer,
                    topic='product_commands',
                    message_obj=command_message,
                    key=product_id
                )

                flash("Product deleted successfully!", "success")
                return redirect(url_for('shop.list_products'))

            except Exception as e:
                db.session.rollback()
                flash(f"An unexpected error occurred during product deletion: {str(e)}", "error")
                return redirect(url_for('shop.get_product', product_id=product_id))
        
        return "Method Not Allowed", 405

    def list_products(self):
        """list products"""
        try:
            products_with_inventory = db.session.query(
                Products,
                Inventory.quantity
            ).outerjoin(Inventory, Products.id == Inventory.product_id).all()

            # Format the data for the template
            products_for_template = []
            for product, quantity in products_with_inventory:
                product_dict = {
                    'id': product.id,
                    'name': product.name,
                    'price': product.price,
                    'description': product.description,
                    'image_url': product.image_url,
                    'created_at': product.created_at,
                    'updated_at': product.updated_at,
                    'stock_quantity': quantity if quantity is not None else 0
                }
                products_for_template.append(product_dict)
                print(products_for_template)
            return render_template('shop/list_products.html', products=products_for_template)
        except Exception as e:
            logger.error(f"Error listing products: {str(e)}", exc_info=True)
            flash("An unexpected error occurred while retrieving products.", "error")
            return render_template('shop/list_products.html', products=[])

    def get_product(self, product_id):
        """get product"""
        try:
            product_with_inventory = db.session.query(
                Products,
                Inventory.quantity
            ).outerjoin(Inventory, Products.id == Inventory.product_id)\
            .filter(Products.id == product_id)\
            .first()

            if not product_with_inventory:
                flash("Product not found", "warning")
                return redirect(url_for('shop.list_products'))

            product, quantity = product_with_inventory
            stock_quantity = quantity if quantity is not None else 0

            return render_template('shop/product_details.html', product=product, stock_quantity=stock_quantity)
        except Exception as e:
            logger.error(f"Error getting product {product_id}: {str(e)}", exc_info=True)
            flash("An unexpected error occurred while retrieving the product.", "error")
            return redirect(url_for('shop.list_products'))