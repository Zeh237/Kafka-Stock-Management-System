import json
from datetime import datetime

from flask import current_app
from src import db
from src.Shop.model import Inventory, Orders, Products
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Analytics:
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