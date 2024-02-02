const Kafka = require('node-rdkafka');
const { Octokit } = require("@octokit/rest");

const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
if (!GITHUB_TOKEN) {
    console.error("GitHub token not found in environment variables.");
    process.exit(1);
}

const octokit = new Octokit({ auth: GITHUB_TOKEN });

const kafkaProducer = new Kafka.Producer({
    'metadata.broker.list': 'localhost:9092'
});

// Function to fetch and send public events
async function fetchAndSendEvents() {
    try {
        const { data: events } = await octokit.activity.listPublicEvents();

        events.forEach(event => {
            // Uncomment the following lines if you want to send the event timestamp
            // let createdAt = new Date(event.created_at);
            // let createdAtMicro = createdAt.getTime() * 1000;

            const eventData = {
                type: event.type,
                repo: event.repo.name,
                actor: event.actor.login,
                // Uncomment the following line if using createdAtMicro
                // created_at: createdAtMicro
            };

            kafkaProducer.produce('github_events', null, Buffer.from(JSON.stringify(eventData)));
            console.log(`Sent GitHub events: ${event.type}, ${event.repo}, ${event.actor.login}`);
        });
    } catch (error) {
        console.error(`Error fetching GitHub events: ${error}`);
    }
}

kafkaProducer.on('ready', function() {
    console.log("Kafka Producer is ready");
    setInterval(fetchAndSendEvents, 10000); // Fetch every 10 seconds
});

kafkaProducer.connect();

process.on('SIGINT', function() {
    console.log("Stopping...");
    kafkaProducer.disconnect();
});

