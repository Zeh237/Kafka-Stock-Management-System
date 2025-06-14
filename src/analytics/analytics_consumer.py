import json
from datetime import datetime

from flask import current_app
import logging
from src.redis.redis_connection import RedisConnection 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Analytics:
    def __init__(self):
        self.kafka_conn = None
        self.consumer = None
        self.running = False
        self.redis_conn = None # Add Redis connection

    def _get_kafka_connection(self):
        # Assumes current_app.kafka_connection is properly set up by your Flask app
        return current_app.kafka_connection

    def initialize(self):
        """Initialize the consumer and Redis connections."""
        self.kafka_conn = self._get_kafka_connection()
        if not self.kafka_conn:
            logger.error("Kafka connection not available.")
            return False

        self.consumer = self.kafka_conn.create_consumer()
        if not self.consumer:
            logger.error("Failed to create Kafka consumer.")
            return False

        # Initialize Redis connection
        self.redis_conn = RedisConnection()
        if not self.redis_conn.connect():
            logger.error("Failed to connect to Redis.")
            return False
        
        logger.info("Analytics consumer and Redis initialized successfully.")
        return True
    
    def handle_analytics_message(self, msg):
        """
        Processes a single analytics event message and saves it to Redis.
        Includes a timestamp in the Redis key to prevent overwrites for the same event type and order.
        """
        try:
            message_value = json.loads(msg.value().decode('utf-8'))
            logger.info(f"Processing analytics message: {message_value.get('event_type')}")

            event_type = message_value.get('event_type')
            order_id = message_value.get('order_id')

            timestamp_str = message_value.get('order_created_at') or datetime.utcnow().isoformat() + 'Z'
            timestamp_for_key = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).strftime("%Y%m%d%H%M%S%f")

            if not event_type or not order_id:
                logger.warning(f"Message missing 'event_type' or 'order_id': {message_value}")
                return
            
            redis_key = f"analytics:{event_type.lower()}:{order_id}:{timestamp_for_key}"
            
            if self.redis_conn.set_data(redis_key, message_value):
                logger.info(f"Successfully saved analytics event (key: {redis_key}) to Redis.")
            else:
                logger.error(f"Failed to save analytics event (key: {redis_key}) to Redis.")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode analytics message JSON: {e}")
        except KeyError as e:
            logger.error(f"Missing expected key in analytics message: {e}")
        except Exception as e:
            logger.error(f"Error processing analytics message: {e}", exc_info=True)

    def start_consuming(self, topic_name='analytics_events'):
        """
        Start consuming messages from the analytics events Kafka topic.
        """
        if not self.initialize():
            logger.error("Failed to initialize Analytics consumer. Aborting consumption.")
            return False

        try:
            self.kafka_conn.subscibe_to_topic(self.consumer, topic_name)
            self.running = True
            logger.info(f"Starting to consume analytics messages from topic: {topic_name}")

            self.kafka_conn.consume_messages(
                consumer=self.consumer,
                message_handler=self.handle_analytics_message,
                timeout=1.0,
                stop_event=None 
            )

        except Exception as e:
            logger.error(f"An unexpected error occurred during analytics consumer operation: {e}", exc_info=True)
        finally:
            self.shutdown()
            logger.info("AnalyticsConsumer consumption loop has ended.")

    def shutdown(self):
        """Cleanup resources."""
        self.running = False
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka analytics consumer closed.")
        if self.redis_conn:
            self.redis_conn.close()
            logger.info("Redis connection for analytics consumer closed.")