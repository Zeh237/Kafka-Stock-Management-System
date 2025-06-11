import os
import redis
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RedisConnection:
    def __init__(self):
        self.host = os.getenv('REDIS_HOST', 'localhost')
        self.port = int(os.getenv('REDIS_PORT', 6379))
        self.db = int(os.getenv('REDIS_DB', 0))
        self.password = os.getenv('REDIS_PASSWORD', None)
        self.client = None

    def connect(self):
        self.client = redis.StrictRedis(
            host=self.host,
            port=self.port,
            db=self.db,
            decode_responses=True,
        )
        self.client.ping()
        return True
    
    def set_data(self, key, value, ex=None, nx=False, xx=False):
        """
        Sets a key-value pair in Redis
        """
        if not self.client:
            logger.error("Redis client not connected.")
            return False
        try:
            if not isinstance(value, str):
                value = json.dumps(value)
            return self.client.set(key, value, ex=ex, nx=nx, xx=xx)
        except Exception as e:
            logger.error(f"Error setting data in Redis for key '{key}': {e}")
            return False

    def get_data(self, key):
        """
        Retrieves data from Redis by key
        """
        if not self.redis_client:
            logger.error("Redis client not connected.")
            return None
        try:
            data = self.redis_client.get(key)
            if data:
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    return data
            return None
        except Exception as e:
            logger.error(f"Error getting data from Redis for key '{key}': {e}")
            return None

    def close(self):
        """Closes the Redis connection"""
        if self.redis_client:
            self.redis_client = None
            logger.info("Redis client reference cleared.")
