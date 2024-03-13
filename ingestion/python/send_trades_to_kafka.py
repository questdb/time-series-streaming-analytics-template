from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer
import csv
import argparse
from datetime import datetime
import time

def parse_arguments():
    parser = argparse.ArgumentParser(description='Stream CSV data to Kafka with Avro serialization.')
    parser.add_argument('csv_file', type=str, help='Path to the CSV file')
    parser.add_argument('kafka_topic', type=str, help='Kafka topic to produce to')
    parser.add_argument('--kafka_broker', type=str, default='localhost:9092', help='Kafka broker address (default: localhost:9092)')
    parser.add_argument('--schema_registry', type=str, default='http://localhost:8081', help='Schema Registry URL (default: http://localhost:8081)')
    parser.add_argument('--timestamp-from-file', dest='timestamp_from_file', action='store_true', help='Use timestamp from file (default behavior)')
    parser.add_argument('--no-timestamp-from-file', dest='timestamp_from_file', action='store_false', help='Use current timestamp instead of the timestamp from file')
    parser.set_defaults(timestamp_from_file=True)
    parser.add_argument('--verbose', action='store_true', help='Print message delivery reports to stdout.')
    parser.add_argument('--delay-ms', type=int, default=50, help='Delay in milliseconds before sending each event')
    return parser.parse_args()

def get_delivery_report_func(verbose):
    def delivery_report(err, msg):
        if verbose:
            if err is not None:
                print(f'Message delivery failed: {err}')
            else:
                print(f'Message delivered to {msg.topic()} [{msg.partition()}]')
    return delivery_report

def main():
    args = parse_arguments()

    value_schema = avro.loads("""
    {
        "type": "record",
        "name": "Trade",
        "fields": [
            {"name": "symbol", "type": "string"},
            {"name": "side", "type": "string"},
            {"name": "price", "type": "double"},
            {"name": "amount", "type": "double"},
            {"name": "timestamp", "type": "long", "logicalType": "timestamp-micros"}
        ]
    }
    """)

    avro_producer = AvroProducer({
        'bootstrap.servers': args.kafka_broker,
        'schema.registry.url': args.schema_registry,
        'linger.ms': '100',  # Adjust based on your needs
        'batch.size': '65536',  # Adjust based on your needs
    }, default_value_schema=value_schema)

    delivery_report_func = get_delivery_report_func(args.verbose)

    with open(args.csv_file, mode='r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            if args.timestamp_from_file:
                timestamp_dt = datetime.strptime(row['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ")
                timestamp_micros = int(timestamp_dt.timestamp() * 1e6)
            else:
                timestamp_micros = int(time.time() * 1e6)

            value = {
                "symbol": row['symbol'],
                "side": row['side'],
                "price": float(row['price']),
                "amount": float(row['amount']),
                "timestamp": timestamp_micros
            }

            if args.delay_ms > 0:
                time.sleep(args.delay_ms / 1000.0)  # Convert milliseconds to seconds

            avro_producer.produce(topic=args.kafka_topic, value=value, on_delivery=delivery_report_func)
            avro_producer.poll(0)  # Serve delivery callback queue

    avro_producer.flush()

if __name__ == '__main__':
    main()


