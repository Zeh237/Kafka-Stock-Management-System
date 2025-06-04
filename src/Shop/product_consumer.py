import json
from datetime import datetime

from flask import current_app
from src import db
from src.Shop.model import Products, Inventory
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductConsumer:
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

    def handle_product_message(self, msg):
        """Process a single product creation message"""
        try:
            message_value = json.loads(msg.value().decode('utf-8'))
            logger.info(f"Processing product message: {message_value}")

            if message_value.get('command_type') != 'CreateProductCommand':
                logger.warning(f"Unexpected command type: {message_value.get('command_type')}")
                return

            payload = message_value.get('payload', {})
            
            # Create Product
            new_product = Products(
                id=payload['product_id'],
                name=payload['name'],
                price=payload['price'],
                description=payload['description'],
                image_url=payload['image_url'],
                created_at=datetime.fromisoformat(payload['created_at'].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(payload['updated_at'].replace('Z', '+00:00'))
            )

            # Create Inventory
            new_inventory = Inventory(
                product_id=payload['product_id'],
                quantity=payload.get('initial_stock_quantity', 0),
                low_stock_threshold=10,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            # Save to database in a transaction
            db.session.add(new_product)
            db.session.add(new_inventory)
            db.session.commit()

            logger.info(f"Successfully created product {new_product.id} and inventory record")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
        except KeyError as e:
            logger.error(f"Missing required field in message: {e}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing product message: {e}", exc_info=True)

    def start_consuming(self, topic_name='product_commands'):
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
                    message_handler=self.handle_product_message,
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