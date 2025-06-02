import logging
from src.kafka.connection import KafkaConnection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ShopViews:
    def __init__(self):
        self.kafka_connection = KafkaConnection()

    def create_product(self):
        """create product"""
        pass

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