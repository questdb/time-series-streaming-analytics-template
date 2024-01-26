package main

import (
	"context"
	"fmt"
	"log"
	"time"
        "encoding/json" 

	"github.com/IBM/sarama"
	"github.com/google/go-github/v32/github"
	"golang.org/x/oauth2"
)

const (
	githubToken   = "TOKEN" // Replace with your GitHub token
	kafkaTopic    = "github_events"     // Kafka topic to produce messages to
	kafkaBroker   = "localhost:9092"    // Kafka broker address
	fetchInterval = 10 * time.Second    // Time interval between fetches
)

func main() {
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
			// Convert created_at to epoch in microseconds
			createdAt := event.GetCreatedAt()
			createdAtMicro := createdAt.UnixNano() / 1000

			eventData := map[string]interface{}{
				"type":                    event.GetType(),
				"repo":                    event.GetRepo().GetName(),
				"actor":                   event.GetActor().GetLogin(),
				"created_at_microseconds": createdAtMicro,
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

