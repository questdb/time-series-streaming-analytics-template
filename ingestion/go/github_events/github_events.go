package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/IBM/sarama"
	"github.com/google/go-github/v32/github"
	"golang.org/x/oauth2"
)

const (
	kafkaTopic    = "github_events"     // Kafka topic to produce messages to
	kafkaBroker   = "localhost:9092"    // Kafka broker address
	fetchInterval = 10 * time.Second    // Time interval between fetches
)

func main() {
	// Fetch GitHub token from environment variable
	githubToken := os.Getenv("GITHUB_TOKEN")
	if githubToken == "" {
		log.Fatalf("GitHub token not found in environment variables.")
	}

	ctx := context.Background()

	// GitHub client setup
	ts := oauth2.StaticTokenSource(
		&oauth2.Token{AccessToken: githubToken},
	)
	tc := oauth2.NewClient(ctx, ts)
	client := github.NewClient(tc)

	// Kafka producer setup
	config := sarama.NewConfig()
	config.Producer.Return.Successes = true
	producer, err := sarama.NewSyncProducer([]string{kafkaBroker}, config)
	if err != nil {
		log.Fatalf("Failed to start Sarama producer: %v", err)
	}
	defer producer.Close()

	// Main loop
	for {
		events, _, err := client.Activity.ListEvents(ctx, nil)
		if err != nil {
			log.Printf("Error fetching GitHub events: %v", err)
			continue
		}

		for _, event := range events {
			// Uncomment the following lines if you want to send the event timestamp 
			// rather than allow QuestDB to use the server timestamp
			// createdAt := event.GetCreatedAt()
			// createdAtMicro := createdAt.UnixNano() / 1000

			eventData := map[string]interface{}{
				"type":  event.GetType(),
				"repo":  event.GetRepo().GetName(),
				"actor": event.GetActor().GetLogin(),
				// Uncomment the following line if using createdAtMicro
				// "created_at": createdAtMicro,
			}

			data, err := json.Marshal(eventData)
			if err != nil {
				log.Printf("Error marshaling event data: %v", err)
				continue
			}

			msg := &sarama.ProducerMessage{
				Topic: kafkaTopic,
				Value: sarama.StringEncoder(data),
			}

			partition, offset, err := producer.SendMessage(msg)
			if err != nil {
				log.Printf("Failed to send message: %v", err)
			} else {
				fmt.Printf("Message sent to partition %d at offset %d\n", partition, offset)
			}
		}
		time.Sleep(fetchInterval)
	}
}

