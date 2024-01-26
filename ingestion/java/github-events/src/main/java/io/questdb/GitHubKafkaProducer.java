package io.questdb;

import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.Producer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.kohsuke.github.GHEventInfo;
import org.kohsuke.github.GitHub;

import java.io.IOException;
import java.util.Properties;

public class GitHubKafkaProducer {

    public static void main(String[] args) throws IOException {
        String githubToken = "iTOKEN";  // Replace with your GitHub token
        String kafkaTopic = "github_events";       // Kafka topic to produce messages to
        String kafkaBroker = "localhost:9092";     // Kafka broker address

        GitHub github = GitHub.connectUsingOAuth(githubToken);

        Properties props = new Properties();
        props.put("bootstrap.servers", kafkaBroker);
        props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
        props.put("value.serializer", "org.apache.kafka.common.serialization.StringSerializer");
    
        try (Producer<String, String> producer = new KafkaProducer<>(props)) {
            while (true) {  // Loop to continuously fetch events
                for (GHEventInfo event : github.getEvents()) {
                    long createdAtMicro = event.getCreatedAt().getTime() * 1000;
                    String message = String.format("{\"type\": \"%s\", \"repo\": \"%s\", \"actor\": \"%s\", \"created_at_microseconds\": %d}",
                            event.getType(), event.getRepository().getName(), event.getActorLogin(), createdAtMicro);

                    producer.send(new ProducerRecord<>(kafkaTopic, message));
                    System.out.println("Sent message: " + message);
                }
                
                try {
                    Thread.sleep(10000); // Sleep for 10 seconds
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}


