import argparse
import requests
from kafka import KafkaConsumer, TopicPartition
import fastavro
from io import BytesIO
import time

def fetch_schema(schema_registry_url, subject):
    response = requests.get(f"{schema_registry_url}/subjects/{subject}/versions/latest")
    schema = response.json()['schema']
    return fastavro.parse_schema(eval(schema))

def consume_messages(broker, topic, group_id, schema_registry_url, offset):
    consumer = KafkaConsumer(
        bootstrap_servers=[broker],
        auto_offset_reset=offset,
        enable_auto_commit=True,
        group_id=group_id,
        value_deserializer=lambda x: x)

    while True:
        try:
            # Attempt to assign partitions to check if the topic exists
            partitions = consumer.partitions_for_topic(topic)
            if partitions is None:
                raise ValueError(f"Topic {topic} does not exist. Will retry...")
            consumer.assign([TopicPartition(topic, p) for p in partitions])

            schema = fetch_schema(schema_registry_url, f"{topic}-value")

            for message in consumer:
                message_bytes = BytesIO(message.value)
                message_bytes.seek(5)  # Skip magic byte and schema ID
                record = fastavro.schemaless_reader(message_bytes, schema)
                print(record)

        except ValueError as e:
            print(e)
            consumer.close()
            time.sleep(10)  # Wait before retrying
            # Reinitialize the consumer to retry
            consumer = KafkaConsumer(
                bootstrap_servers=[broker],
                auto_offset_reset=offset,
                enable_auto_commit=True,
                group_id=group_id,
                value_deserializer=lambda x: x)
        except KeyboardInterrupt:
            break

    consumer.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kafka Avro Consumer")
    parser.add_argument('--topic', required=True, help="Kafka topic to subscribe to")
    parser.add_argument('--broker', default='localhost:9092', help="Kafka broker address (default: localhost:9092)")
    parser.add_argument('--group-id', default='default_group', help="Kafka consumer group ID (default: default_group)")
    parser.add_argument('--schema-registry', default='http://localhost:8081', help="Schema Registry URL (default: http://localhost:8081)")
    parser.add_argument('--offset', default='earliest', choices=['earliest', 'latest'],
                        help='Offset reset policy. "earliest" reads from the beginning, "latest" reads new messages only. (default: earliest)')

    args = parser.parse_args()

    consume_messages(args.broker, args.topic, args.group_id, args.schema_registry, args.offset)
