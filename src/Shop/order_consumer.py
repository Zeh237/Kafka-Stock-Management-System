import json
from datetime import datetime

from flask import current_app
from src import db
from src.Shop.model import Products, Inventory, Orders
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OrderConsumer:
    def __init__(self):
        self.kafka_conn = None
        self.consumer = None
        self.running = False

    def _get_kafka_connection(self):
        return current_app.kafka_connection

    def initialize(self):
        """Initialize the consumer connection"""
        self.kafka_conn = self._get_kafka_connection()
        if not self.kafka_conn:
            return False
        
        self.consumer = self.kafka_conn.create_consumer()
        if not self.consumer:
            return False
        
        return True
    
    def handle_order_message(self, msg):
        """Process a single order creation message"""
        try:
            message_value = json.loads(msg.value().decode('utf-8'))
            logger.info(f"Processing order message: {message_value}")

            if message_value.get('command_type') not in ['CreateOrderCommand', 'UpdateOrderCommand', 'DeleteOrderCommand']:
                logger.warning(f"Unexpected command type: {message_value.get('command_type')}")
                return

            payload = message_value.get('payload', {})

            if message_value.get('command_type') == 'CreateOrderCommand':
                # Create orders
                new_product = Orders(
                    id=payload['order_id'],
                    product_id=payload['product_id'],
                    quantity=payload['quantity'],
                    total_price=int(payload['total_price']),
                    created_at=datetime.fromisoformat(payload['created_at'].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(payload['updated_at'].replace('Z', '+00:00'))
                )

                # update inventory
                inventory_item = Inventory.query.filter_by(product_id=payload['product_id']).first()
                if inventory_item:
                    inventory_item.quantity =inventory_item.quantity - payload['quantity']
                    inventory_item.updated_at = datetime.fromisoformat(payload['updated_at'].replace('Z', '+00:00'))

                db.session.add(inventory_item)
                db.session.add(new_product)
                logger.info(f"Successfully created product {new_product.id} and inventory record")

            db.session.commit()

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
        except KeyError as e:
            logger.error(f"Missing required field in message: {e}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing product message: {e}", exc_info=True)

    def start_consuming(self, topic_name='order_commands'):
        """Start consuming messages from Kafka using the KafkaConnection's consume_messages method."""
        if not self.initialize():
            logger.error("Failed to initialize Kafka consumer. Aborting consumption.")
            return False

        try:
            self.kafka_conn.subscibe_to_topic(self.consumer, topic_name)
            self.running = True
            logger.info(f"Starting to consume messages from topic: {topic_name}")

            self.kafka_conn.consume_messages(
                consumer=self.consumer,
                message_handler=self.handle_order_message,
                timeout=1.0,
                stop_event=None
            )

        except Exception as e:
            logger.error(f"An unexpected error occurred during consumer operation: {e}", exc_info=True)
        finally:
            self.shutdown()
            logger.info("ProductConsumer consumption loop has ended.")

    def shutdown(self):
        """Cleanup resources"""
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")