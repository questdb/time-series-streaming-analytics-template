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

def generate_device_data(device_index, timestamp_micros):
    device_id = generate_device_id(device_index)
    mark_model = f"ACME-{1 + device_index % 2000}"
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
parser.add_argument('--topic', type=str, default='smart-meters', help='Kafka topic to send data to (default: smart-meters)')
parser.add_argument('--broker', type=str, default='localhost:9092', help='Kafka broker address (default: localhost:9092)')
parser.add_argument('--schema-registry', type=str, default='http://localhost:8081', help='Schema Registry URL (default: http://localhost:8081)')
parser.add_argument('--max-messages', type=int, default=1000000, help='Maximum number of total messages to send (default: 1000000)')

args = parser.parse_args()

avro_producer = AvroProducer({
    'bootstrap.servers': args.broker,
    'schema.registry.url': args.schema_registry
}, default_key_schema=key_schema, default_value_schema=value_schema)

total_messages_sent = 0
start_time = time.time()

while total_messages_sent < args.max_messages:
    for device_index in range(args.num_devices):
        current_time = time.time()
        elapsed_time = current_time - start_time

        # Calculate the target time for this message
        target_time = total_messages_sent * (args.interval / args.num_devices)

        # Calculate the delay needed to align with the target time
        delay = target_time - elapsed_time
        if delay > 0:
            time.sleep(delay)

        timestamp_micros = int(time.time() * 1e6)
        data = generate_device_data(device_index, timestamp_micros)
        avro_producer.produce(topic=args.topic, value=data, key=str(device_index))
        avro_producer.poll(0)
        total_messages_sent += 1

        if total_messages_sent >= args.max_messages:
            break

avro_producer.flush()
print(f"Finished sending {total_messages_sent} messages.")
