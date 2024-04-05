import argparse
import time
from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer
import random

# Define the Avro schema for device data
value_schema_str = """
{
   "namespace": "com.example.avro",
   "type": "record",
   "name": "DeviceData",
   "fields": [
       {"name": "device_id", "type": "string"},
       {"name": "timestamp", "type": "long"},
       {"name": "mark_model", "type": "string"},
       {"name": "status", "type": "string"},
       {"name": "energy_consumption", "type": "float"},
       {"name": "voltage", "type": "float"},
       {"name": "current", "type": "float"},
       {"name": "power_factor", "type": "float"},
       {"name": "frequency", "type": "int"}
   ]
}
"""
value_schema = avro.loads(value_schema_str)
key_schema = avro.loads('{"type": "string"}')

def generate_device_id(index):
    letters = index // (16**4) % (26**3)
    letter_part = ''.join(chr(65 + (letters // (26**i) % 26)) for i in range(3)[::-1])
    hex_part = format(index % (16**4), '04x').upper()
    return f"{letter_part}{hex_part}"

def generate_device_data(device_index, timestamp_micros, interval_seconds):
    device_id = generate_device_id(device_index)
    mark_model = f"ACME-{1 + device_index % 2000}"
    seed_interval_seconds = 3 * interval_seconds
    random.seed(device_id + str(int(timestamp_micros / (1e6 * seed_interval_seconds))))
    status = random.choices(["Active", "Inactive", "Faulty"], weights=[95, 4, 1], k=1)[0]
    energy_consumption = random.uniform(-5.0, 15.0) if status != "Faulty" else 0
    voltage = random.uniform(110, 240)
    current = random.uniform(0, 30) if status != "Faulty" else 0
    power_factor = random.uniform(0.5, 1.0)
    frequency = random.choice([50, 60])

    return {
        "device_id": device_id,
        "timestamp": timestamp_micros,
        "mark_model": mark_model,
        "status": status,
        "energy_consumption": energy_consumption,
        "voltage": voltage,
        "current": current,
        "power_factor": power_factor,
        "frequency": frequency,
    }

parser = argparse.ArgumentParser(description='Device Data Simulator')
parser.add_argument('--num-devices', type=int, default=1000, help='Number of devices (default: 1000)')
parser.add_argument('--interval', type=int, default=300, help='Interval for sending data in seconds (default: 300)')
parser.add_argument('--topic', type=str, default='smart-meter-data', help='Kafka topic to send data to (default: smart-meter-data)')
parser.add_argument('--broker', type=str, default='localhost:9092', help='Kafka broker address (default: localhost:9092)')
parser.add_argument('--schema-registry', type=str, default='http://localhost:8081', help='Schema Registry URL (default: http://localhost:8081)')
parser.add_argument('--max-messages', type=int, default=1000000, help='Maximum number of total messages to send (default: 1000000)')

args = parser.parse_args()

avro_producer = AvroProducer({
    'bootstrap.servers': args.broker,
    'schema.registry.url': args.schema_registry
}, default_key_schema=key_schema, default_value_schema=value_schema)

total_messages_sent = 0
while total_messages_sent < args.max_messages:
    for i in range(args.num_devices):
        if total_messages_sent >= args.max_messages:
            break
        timestamp_micros = int(time.time() * 1e6)
        data = generate_device_data(i, timestamp_micros, args.interval)
        avro_producer.produce(topic=args.topic, value=data, key=str(i))
        avro_producer.poll(0)
        total_messages_sent += 1
    time.sleep(args.interval)

avro_producer.flush()
print(f"Finished sending {total_messages_sent} messages.")
