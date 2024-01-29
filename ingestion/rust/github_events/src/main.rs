use rdkafka::producer::{FutureProducer, FutureRecord};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::time::Duration;
use tokio::time::sleep;

#[derive(Debug, Deserialize)]
struct GitHubEvent {
    id: String,
    #[serde(rename = "type")]
    event_type: String,
    actor: Actor,
    repo: Repo,
    // Other fields can be added here as needed
}

#[derive(Debug, Deserialize)]
struct Actor {
    login: String,
}

#[derive(Debug, Deserialize)]
struct Repo {
    name: String,
}

#[tokio::main]
async fn main() {
    let github_token = std::env::var("GITHUB_TOKEN")
        .expect("Expected GITHUB_TOKEN to be set in env!");

    let client = reqwest::Client::new();
    let producer: FutureProducer = rdkafka::config::ClientConfig::new()
        .set("bootstrap.servers", "localhost:9092")
        .set("message.timeout.ms", "5000")
        .create()
        .expect("Producer creation error");

    loop {
        let events = fetch_github_events(&client, &github_token).await;
        for event in events {
            // Construct JSON object with only the necessary fields
            let event_data = json!({
                "type": event.event_type,
                "repo": event.repo.name,
                "actor": event.actor.login,
                // Add other fields as needed
            });

            let event_json = serde_json::to_string(&event_data)
                .expect("Failed to serialize event.");

            producer.send(
                FutureRecord::to("github_events")
                    .payload(&event_json)
                    .key(&event.id),
                Duration::from_secs(0),
            ).await
            .expect("Failed to send record");

            println!("Sent event: {}", event.id);
        }

        sleep(Duration::from_secs(10)).await;
    }
}

async fn fetch_github_events(client: &reqwest::Client, token: &str) -> Vec<GitHubEvent> {
    let request_url = "https://api.github.com/events";
    let response = client.get(request_url)
        .header("Authorization", format!("token {}", token))
        .header("User-Agent", "request")
        .header("Accept", "application/vnd.github.v3+json")
        .send()
        .await
        .expect("Failed to send request");

    response.json::<Vec<GitHubEvent>>().await
        .expect("Failed to deserialize events") // Better error handling is recommended
}

