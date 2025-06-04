# consumer_app.py (consumer microservice)

import os
import logging
from flask import Flask, current_app
from src.config import Config
from src.kafka.connection import KafkaConnection
from src.Shop.product_consumer import ProductConsumer
from src.Shop.model import Products, Inventory 
from src import db, migrate

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_consumer_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.logger.info(f"Consumer microservice starting up with config: {config_class.__name__}")

    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        app.logger.info("Consumer microservice: Ensuring database tables are in place.")

        app.kafka_connection = KafkaConnection()
        app.logger.info("Consumer microservice: KafkaConnection instance created.")

        consumer_topic = 'product_commands'
        
        existing_topics = []
        try:
            existing_topics = app.kafka_connection.list_topics()
            if existing_topics:
                app.logger.info(f"Consumer microservice: Found existing Kafka topics: {', '.join(existing_topics)}")
            else:
                app.logger.warning("Consumer microservice: Could not retrieve existing Kafka topics.")
        except Exception as e:
            app.logger.error(f"Consumer microservice: Error listing Kafka topics: {e}")

        if consumer_topic not in existing_topics:
            app.logger.info(f"Consumer microservice: Attempting to create Kafka topic '{consumer_topic}'...")
            success = app.kafka_connection.create_topic(consumer_topic, num_partitions=3, replication_factor=1)
            if success:
                app.logger.info(f"Consumer microservice: Kafka topic '{consumer_topic}' created successfully.")
            else:
                app.logger.error(f"Consumer microservice: Failed to create Kafka topic '{consumer_topic}'. Consumer might not function correctly.")
        else:
            app.logger.info(f"Consumer microservice: Kafka topic '{consumer_topic}' already exists. Skipping creation.")

        product_consumer = ProductConsumer()
        app.logger.info("Consumer microservice: ProductConsumer instance created.")
        
        app.logger.info(f"Consumer microservice: Starting Kafka consumption for topic '{consumer_topic}'...")
        product_consumer.start_consuming(topic_name=consumer_topic)

    return app

if __name__ == '__main__':
    os.environ['FLASK_APP'] = 'consumer_app.py'

    consumer_app = create_consumer_app()
    logger.info("Consumer microservice application finished (this message might not be seen if consumer runs indefinitely).")