from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from src.config import Config
from src.kafka.connection import KafkaConnection
from src.redis.redis_connection import RedisConnection
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    """
    Application factory function.
    Creates and configures a Flask application instance, initializes database,
    and sets up Kafka topics and a producer.
    """
    app = Flask(__name__, static_folder=os.path.join(os.getcwd(), 'src', 'static'))
    app.config.from_object(config_class)
    app.logger.info(f"Application starting up with config: {config_class.__name__}")

    # Initialize extensions with the application instance
    db.init_app(app)
    migrate.init_app(app, db)

    from src.Shop.routes import shop_bp
    app.register_blueprint(shop_bp, url_prefix='/shop')

    with app.app_context():
        from src.Shop.model import Products, Orders, Inventory
        db.create_all()
        app.logger.info("Database tables checked/created.")

        kafka_conn = KafkaConnection()
        app.logger.info("KafkaConnection instance created.")

        app.redis_connection = RedisConnection()
        app.logger.info("RedisConnection instance created.")

        # Topics needed for the system
        required_topics = [
            'product_commands',     # Flask app produces commands here (create, update, delete product)
            'product_events',       # Product Command Processor publishes actual events here
            'order_commands',       # Customer Flask app produces order commands here
            'order_events',         # Order Command Processor publishes actual order events here
            'inventory_events',     # Order Command Processor / Inventory Service publishes stock changes here
            'analytics_events'      # (Optional) For aggregated data for the dashboard
        ]

        existing_topics = kafka_conn.list_topics()
        if existing_topics:
            app.logger.info(f"Found existing Kafka topics: {', '.join(existing_topics)}")
        else:
            app.logger.warning("Could not retrieve existing Kafka topics. Attempting to create all required topics.")

        # Create each required Kafka topic if it doesn't already exist
        for topic in required_topics:
            if topic in existing_topics:
                app.logger.info(f"Kafka topic '{topic}' already exists. Skipping creation.")
            else:
                app.logger.info(f"Attempting to create Kafka topic '{topic}'...")
                success = kafka_conn.create_topic(topic, num_partitions=3, replication_factor=1)
                if success:
                    app.logger.info(f"Kafka topic '{topic}' created successfully.")
                else:
                    app.logger.error(f"Failed to create Kafka topic '{topic}'. Application might not function correctly.")
    
        app.kafka_producer = kafka_conn.create_producer()
        app.kafka_connection = kafka_conn
        if app.kafka_producer:
            app.logger.info("Kafka Producer initialized and attached to app.")
        else:
            app.logger.error("Failed to initialize Kafka Producer. Commands cannot be sent to Kafka.")

    return app