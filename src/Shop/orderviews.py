import logging
from flask import current_app, render_template, request, redirect, url_for, flash
from src.Shop.validation import OrderCreateCommand, ProductCreateCommand
import os
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime
from src.Shop.model import Orders, Products
from src import db
import time


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OrderViews:
    def __init__(self):
        pass

    def _get_kafka_producer(self):
        return current_app.kafka_producer
    
    def _get_kafka_connection(self):
        return current_app.kafka_connection
    
    def create_order(self, product_id, price):
        """
        Create a new order to kafka
        """
        try:
            print(price, product_id)
            if request.method == 'GET':
                return render_template('shop/create_order.html', product_id = product_id, price = int(price))
            elif request.method == 'POST':
                producer = self._get_kafka_producer()
                kafka_conn = self._get_kafka_connection()
                product = Products.query.get(product_id)
                if not product:
                    flash("Product not found", "warning")
                    return render_template('shop/create_order.html', form_data=request.form), 400
                try:
                    order_data = OrderCreateCommand(
                        product_id=product_id,
                        quantity=int(request.form.get('quantity', 0)),
                        total_price=float(price)*int(request.form.get('quantity', 0))
                    )
                except ValueError as e:
                    flash(f"Validation error: {str(e)}", "warning")

                order_id = str(uuid.uuid4())
                if not producer or not kafka_conn:
                    flash("System error: Unable to process request", "error")
                    return render_template('shop/create_order.html', form_data=request.form), 500
                
                command_message = {
                    "command_id": str(uuid.uuid4()),
                    "timestamp": datetime.utcnow().isoformat() + 'Z',
                    "command_type": "CreateOrderCommand",
                    "payload": {
                        "order_id": order_id,
                        "product_id": order_data.product_id,
                        "quantity": order_data.quantity,
                        "total_price": order_data.total_price,
                        "created_at": datetime.utcnow().isoformat()+'Z',
                        "updated_at": datetime.utcnow().isoformat()+'Z'
                    }
                }

                kafka_conn.produce_message(
                        producer,
                        topic='order_commands',
                        message_obj=command_message,
                        key=order_id
                    )

                logger.info(f"Created order command for {order_id}")
                flash("order creation request received!", "success")
                time.sleep(2)
                return redirect(url_for('shop.list_orders'))
        except Exception as e:
            logger.error(f"Order creation failed: {str(e)}", exc_info=True)
            flash("An unexpected error occurred. Please try again.", "error")
            return render_template('shop/create_order.html', form_data=request.form), 500

    def list_orders(self):
        """list orders"""
        try:
            orders = Orders.query.all()
            return render_template('shop/list_orders.html', orders=orders)
        except Exception as e:
            logger.error(f"Error listing orders: {str(e)}", exc_info=True)
            flash("An unexpected error occurred while retrieving orders.", "error")
            return render_template('shop/list_orders.html', orders=[])

    def get_order(self, order_id):
        """get order"""
        try:
            order = Orders.query.get(order_id)
            if not order:
                flash("Order not found", "warning")
                return redirect(url_for('order.list_orders'))
            return render_template('shop/order_details.html', order=order)
        except Exception as e:
            logger.error(f"Error getting order {order_id}: {str(e)}", exc_info=True)
            flash("An unexpected error occurred while retrieving the order.", "error")
            return redirect(url_for('shop.list_orders'))

    def update_order(self):
        pass

    def delete_order(self, order_id):
        """delete order"""
        try:
            producer = self._get_kafka_producer()
            kafka_conn = self._get_kafka_connection()

            order = Orders.query.get(order_id)
            if not order:
                flash("Order not found", "warning")
            db.session.delete(order)
            db.session.commit()

            # Sending Kafka Delete Command
            command_message = {
                    "command_id": str(uuid.uuid4()),
                    "command_type": "DeleteOrderCommand",
                    "timestamp": datetime.utcnow().isoformat() + 'Z',
                    "payload": {
                        "order_id": order_id
                    }
                }
            
            kafka_conn.produce_message(
                    producer,
                    topic='order_commands',
                    message_obj=command_message,
                    key=order_id
                )
            flash("Order deleted successfully!", "success")
            return redirect(url_for('shop.list_orders'))
        except Exception as e:
            logger.error(f"Error deleting order {order_id}: {str(e)}", exc_info=True)
            flash("An unexpected error occurred while deleting the order.", "error")
            return redirect(url_for('shop.list_orders'))
