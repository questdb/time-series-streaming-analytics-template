from github import Github, GithubException
import requests
from kafka import KafkaProducer
import json
import time
from datetime import datetime


# Configuration
GITHUB_TOKEN = 'TOKEN'  # Replace with your GitHub token
KAFKA_TOPIC = 'github_events'       # Kafka topic to produce messages to
KAFKA_BROKER = 'localhost:9092'     # Kafka broker address
FETCH_INTERVAL = 10                 # Time interval between fetches in seconds
GITHUB_EVENTS_URL = 'https://api.github.com/events'

# Initialize GitHub client
g = Github(GITHUB_TOKEN, per_page=100)

# Initialize Kafka producer
producer = KafkaProducer(bootstrap_servers=[KAFKA_BROKER],
                         value_serializer=lambda m: json.dumps(m).encode('ascii'))

# Function to fetch and send public events
def fetch_and_send_events(etag=None):
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
    }
    if etag:
        headers['If-None-Match'] = etag

    response = requests.get(GITHUB_EVENTS_URL, headers=headers)

    if response.status_code == 304:  # Not Modified
        print("No new events since last check.")
        return etag
    elif response.status_code != 200:
        raise GithubException(response.status_code, response.json())

    new_etag = response.headers.get('ETag')
    events = response.json()

    for event in events:
         # Parse the created_at field to datetime object
        created_at_datetime = datetime.strptime(event.get('created_at'), '%Y-%m-%dT%H:%M:%SZ')

        # Convert datetime to epoch in microseconds
        created_at_microseconds = int(time.mktime(created_at_datetime.timetuple()) * 1e6)

        event_data = {
            'type': event.get('type'),
            'repo': event.get('repo', {}).get('name', 'None'),
            'actor': event.get('actor', {}).get('login', 'Unknown'),
            'created_at': created_at_microseconds 

            # Add more event details as needed
        }
        producer.send(KAFKA_TOPIC, event_data)
        print(f"Sent event: {event['type']} from {event.get('repo', {}).get('name', 'None')} at {event.get('created_at')}")

    return new_etag

# Main loop
etag = None
try:
    while True:
        rate_limit = g.get_rate_limit().core
        if rate_limit.remaining == 0:
            reset_time = rate_limit.reset.timestamp()
            sleep_time = max(reset_time - time.time(), 1)
            print(f"Rate limit exceeded. Sleeping for {sleep_time} seconds.")
            time.sleep(sleep_time)
        else:
            etag = fetch_and_send_events(etag)
            time.sleep(FETCH_INTERVAL)
except KeyboardInterrupt:
    print("Stopping...")

