import os
import logging
from flask import Flask, current_app
from src.config import Config
from src.kafka.connection import KafkaConnection
from src.Shop.product_consumer import ProductConsumer
from src.Shop.order_consumer import OrderConsumer
from src.Shop.model import Products, Inventory, Orders
from src import db, migrate
import threading
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_consumer_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.logger.info(f"Consumer microservice starting up with config: {config_class.__name__}")

    db.init_app(app)
    migrate.init_app(app, db)
    
    return app

def run_consumer_in_context(app, consumer_instance, topic_name):
    with app.app_context():
        consumer_instance.start_consuming(topic_name=topic_name)

if __name__ == '__main__':
    os.environ['FLASK_APP'] = 'consumer_app.py'

    app = create_consumer_app()

    with app.app_context():
        app.logger.info("Consumer microservice: Ensuring database tables are in place.")

        app.kafka_connection = KafkaConnection()
        app.logger.info("Consumer microservice: KafkaConnection instance created.")

        product_consumer_topic = 'product_commands'
        order_consumer_topic = 'order_commands'
        
        all_topics_to_check = [product_consumer_topic, order_consumer_topic]
        existing_topics = []
        try:
            existing_topics = app.kafka_connection.list_topics()
            if existing_topics:
                app.logger.info(f"Consumer microservice: Found existing Kafka topics: {', '.join(existing_topics)}")
            else:
                app.logger.warning("Consumer microservice: Could not retrieve existing Kafka topics.")
        except Exception as e:
            app.logger.error(f"Consumer microservice: Error listing Kafka topics: {e}", exc_info=True)

        for topic_name in all_topics_to_check:
            if topic_name not in existing_topics:
                app.logger.info(f"Consumer microservice: Attempting to create Kafka topic '{topic_name}'...")
                success = app.kafka_connection.create_topic(topic_name, num_partitions=3, replication_factor=1)
                if success:
                    app.logger.info(f"Consumer microservice: Kafka topic '{topic_name}' created successfully.")
                else:
                    app.logger.error(f"Consumer microservice: Failed to create Kafka topic '{topic_name}'. Consumer might not function correctly.")
            else:
                app.logger.info(f"Consumer microservice: Kafka topic '{topic_name}' already exists. Skipping creation.")

        product_consumer = ProductConsumer()
        app.logger.info("Consumer microservice: ProductConsumer instance created.")
        order_consumer = OrderConsumer()
        app.logger.info("Consumer microservice: OrderConsumer instance created.")
        
        product_consumer_thread = threading.Thread(
            target=run_consumer_in_context,
            args=(app, product_consumer, product_consumer_topic,),
            daemon=True
        )
        order_consumer_thread = threading.Thread(
            target=run_consumer_in_context,
            args=(app, order_consumer, order_consumer_topic,),
            daemon=True
        )

        app.logger.info("Consumer microservice: Starting consumer threads.")
        product_consumer_thread.start()
        order_consumer_thread.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            app.logger.info("Consumer microservice: Shutting down consumer threads due to interrupt.")
        finally:
            product_consumer.shutdown()
            order_consumer.shutdown()
            app.logger.info("Consumer microservice: All consumers shut down.")

    logger.info("Consumer microservice application finished (this message might not be seen if consumer runs indefinitely).")