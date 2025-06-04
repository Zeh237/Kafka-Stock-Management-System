import os
import json
from confluent_kafka import Producer, Consumer, KafkaException, KafkaError
import logging
from confluent_kafka.admin import AdminClient, NewTopic, TopicMetadata, KafkaException

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KafkaConnection:
    def __init__(self):
        pass

    def get_config(self, client_type):
        """
        Constructs and returns Kafka configuration dictionary based on environment variables.
        """
        config = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        }

        security_protocol = os.getenv('KAFKA_SECURITY_PROTOCOL')
        if security_protocol:
            config['security.protocol'] = security_protocol
            if security_protocol in ['SASL_SSL', 'SASL_PLAINTEXT']:
                sasl_mechanism = os.getenv('KAFKA_SASL_MECHANISM', 'PLAIN')
                sasl_username = os.getenv('KAFKA_SASL_USERNAME')
                sasl_password = os.getenv('KAFKA_SASL_PASSWORD')

                if not sasl_username or not sasl_password:
                    logger.warning("KAFKA_SECURITY_PROTOCOL is set, but KAFKA_SASL_USERNAME or KAFKA_SASL_PASSWORD are missing.")
                else:
                    config['sasl.mechanisms'] = sasl_mechanism
                    config['sasl.username'] = sasl_username
                    config['sasl.password'] = sasl_password

        if client_type == 'producer':
            config['acks'] = 'all'
            config['retries'] = 3
            
        if client_type == 'consumer':
            config['group.id'] = os.getenv('KAFKA_GROUP_ID', 'default_flask_app_group')
            config['auto.offset.reset'] = 'earliest'
            config['enable.auto.commit'] = True
            config['auto.commit.interval.ms'] = 5000

        return config
    
    def create_producer(self):
        """
        Creates and returns a Kafka Producer instance.
        """
        try:
            producer_config = self.get_config(client_type='producer')
            producer = Producer(producer_config)
            logger.info(f"Kafka Producer created with config: {producer_config.get('bootstrap.servers')}")
            return producer
        except KafkaException as e:
            logger.error(f"Error creating Kafka Producer: {e}")
            return None

    def create_consumer(self):
        """
        Creates and returns a Kafka Consumer instance.
        """
        try:
            consumer_config = self.get_config(client_type='consumer')
            consumer = Consumer(consumer_config)
            logger.info(f"Kafka Consumer created with config: {consumer_config.get('bootstrap.servers')}, Group ID: {consumer_config.get('group.id')}")
            return consumer
        except KafkaException as e:
            logger.error(f"Error creating Kafka Consumer: {e}")
            return None
            
    def delivery_report(self, err, msg):
        """
        Reports the delivery status of a message.
        This function is called by the producer once a message has been delivered or failed.
        """
        if err is not None:
            # Decode key if it exists, otherwise use 'N/A'
            key_info = msg.key().decode('utf-8') if msg.key() else 'N/A'
            logger.error(f"Message delivery failed for topic {msg.topic()} key {key_info}: {err}")
        else:
            logger.info(f"Message delivered to topic {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}")

    def produce_message(self, producer, topic, message_obj, key):
        """Produces a message to a kafka topic"""
        try:
            encoded_key = key.encode('utf-8') if key else None
            producer.produce(
                topic,
                key=encoded_key,
                value=json.dumps(message_obj).encode('utf-8'),
                callback=self.delivery_report
            )
            producer.poll(0)
            logger.info(f"Message queued for production to topic {topic}")
        except Exception as e:
            logger.error(f"Error producing message to Kafka: {e}", exc_info=True)

    def create_topic(self, topic_name, num_partitions=1, replication_factor=1):
        """
        Creates a Kafka topic using the AdminClient
        """
        admin_config = {k: v for k, v in self.get_config(client_type='admin').items() if k not in ['acks', 'retries', 'group.id', 'auto.offset.reset', 'enable.auto.commit', 'auto.commit.interval.ms']}

        admin_client = AdminClient(admin_config)

        new_topic = NewTopic(topic_name, num_partitions=num_partitions, replication_factor=replication_factor)

        futures = admin_client.create_topics([new_topic])

        for topic, future in futures.items():
            try:
                future.result()
                logger.info(f"Topic '{topic_name}' created successfully.")
                return True
            except KafkaException as e:
                if e.args[0].code() == KafkaError.TOPIC_ALREADY_EXISTS:
                    logger.warning(f"Topic '{topic_name}' already exists.")
                    return True
                else:
                    logger.error(f"Failed to create topic '{topic_name}': {e}")
                    return False
            except Exception as e:
                logger.error(f"An unexpected error occurred while creating topic '{topic_name}': {e}", exc_info=True)
                return 
            
    def list_topics(self):
        """
        Lists all topics in the Kafka cluster using the AdminClient.
        """
        admin_config = {k: v for k, v in self.get_config(client_type='admin').items() if k not in ['acks', 'retries', 'group.id', 'auto.offset.reset', 'enable.auto.commit', 'auto.commit.interval.ms']}
        admin_client = AdminClient(admin_config)

        try:
            metadata = admin_client.list_topics(timeout=10).topics
            topic_names = sorted(list(metadata.keys()))
            logger.info(f"Successfully listed {len(topic_names)} topics.")
            return topic_names
        except Exception as e:
            logger.error(f"An unexpected error occurred while listing topics: {e}", exc_info=True)
            return []

    def subscibe_to_topic(self, consumer, topic):
        """subscribes a consumer to a topic"""
        try:
            consumer.subscribe([topic])
            logger.info(f"Subscribed to topic {topic}")
        except Exception as e:
            logger.error(f"Error subscribing to topic {topic}: {e}")

    def consume_messages(self, consumer, message_handler, timeout, stop_event=None):
            """
            Continuously consumes messages from Kafka and processes them using a handler.
            This is a blocking call and will run until stop_event is set or KeyboardInterrupt.
            """
            if consumer is None:
                logger.error("Consumer instance is None. Cannot consume messages.")
                return

            logger.info("Starting Kafka message consumption loop...")
            try:
                # Loop until a stop_event is set (if provided) or indefinitely
                while not (stop_event and stop_event.is_set()):
                    msg = consumer.poll(timeout)

                    if msg is None: # Timeout, no message currently available
                        continue
                    
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            # End of partition event, not necessarily an error, just means no more messages for now
                            logger.debug(
                                f"Reached end of partition: {msg.topic()} [{msg.partition()}] at offset {msg.offset()}"
                            )
                        elif msg.error().code() == KafkaError._TRANSPORT:
                            # Intermittent network/transport error. confluent-kafka handles retries internally.
                            logger.warning(f"Consumer transport error: {msg.error()}. Will attempt to recover.")
                        else:
                            # Other consumer errors (e.g., deserialization error)
                            logger.error(f"Consumer error: {msg.error()}")
                            # Depending on the error, you might want to break or implement specific recovery
                    else:
                        # Proper message received
                        try:
                            message_handler(msg)
                        except Exception as e:
                            logger.error(f"Error processing message in handler: {e}. Message value: {msg.value()}", exc_info=True)
                            # Log the error but continue consuming. Decide if you want to commit this offset or not.
            except Exception as e:
                logger.error(f"An unexpected error occurred during message consumption loop: {e}", exc_info=True)
            finally:
                logger.info("Kafka message consumption loop stopped.")
                if consumer: # Ensure consumer object exists before closing
                    consumer.close()
                    logger.info("Kafka consumer closed.")