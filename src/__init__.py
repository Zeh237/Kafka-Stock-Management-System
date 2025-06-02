from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from src.config import Config, DevelopmentConfig, TestingConfig, ProductionConfig
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    """
    Application factory function.
    Creates and configures a Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.logger.info(f"Application starting up with config: {config_class.__name__}")

    # Initialize extensions with the application instance
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        from src.Shop.model import Products, Orders, Inventory
        db.create_all()
        app.logger.info("Database tables checked/created.")

    return app
