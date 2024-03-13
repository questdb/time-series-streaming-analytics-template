package main

import (
    "bufio"
    "bytes"
    "encoding/binary"
    "encoding/csv"
    "encoding/json"
    "flag"
    "fmt"
    "io"
    "log"
    "net/http"
    "os"
    "strconv"
    "time"

    "github.com/linkedin/goavro/v2"
    sarama "github.com/Shopify/sarama"
)

var (
    brokerFlag         = flag.String("broker", "localhost:9092", "Kafka broker address")
    topicFlag          = flag.String("topic", "trades", "Kafka topic name")
    csvFileFlag        = flag.String("csv", "./data.csv", "Path to the CSV file")
    schemaRegistryFlag = flag.String("schema-registry", "http://localhost:8081", "Schema Registry URL")
    subjectFlag        = flag.String("subject", "trades-value", "Schema subject name")
    verboseFlag        = flag.Bool("verbose", true, "Enable verbose logging")
    useCurrentTimeFlag = flag.Bool("use-current-time", false, "Use current system time instead of timestamp from file")
    delayMsFlag = flag.Int("delay-ms",50 , "Delay in milliseconds before sending each event")
)

func registerOrGetSchemaID(schemaRegistryURL, subject, schema string) (int, error) {
    client := &http.Client{}
    url := fmt.Sprintf("%s/subjects/%s/versions", schemaRegistryURL, subject)
    reqBody, err := json.Marshal(map[string]string{"schema": schema})
    if err != nil {
        return 0, err
    }

    req, err := http.NewRequest("POST", url, bytes.NewBuffer(reqBody))
    if err != nil {
        return 0, err
    }
    req.Header.Set("Content-Type", "application/vnd.schemaregistry.v1+json")

    resp, err := client.Do(req)
    if err != nil {
        return 0, err
    }
    defer resp.Body.Close()

    if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
        body, _ := io.ReadAll(resp.Body)
        return 0, fmt.Errorf("failed to register or get schema ID; response status: %s, body: %s", resp.Status, string(body))
    }

    var respBody struct {
        ID int `json:"id"`
    }
    if err := json.NewDecoder(resp.Body).Decode(&respBody); err != nil {
        return 0, err
    }

    return respBody.ID, nil
}

func main() {
    flag.Parse()

    schema := `{
        "type": "record",
        "name": "Trade",
        "namespace": "com.example",
        "fields": [
            {"name": "symbol", "type": "string"},
            {"name": "side", "type": "string"},
            {"name": "price", "type": "double"},
            {"name": "amount", "type": "double"},
            {"name": "timestamp", "type": {"type": "long", "logicalType": "timestamp-micros"}}
        ]
    }`

    schemaID, err := registerOrGetSchemaID(*schemaRegistryFlag, *subjectFlag, schema)
    if err != nil {
        log.Fatalf("Error registering or fetching schema ID: %v", err)
    }

    producer, err := sarama.NewSyncProducer([]string{*brokerFlag}, nil)
    if err != nil {
        log.Fatalf("Failed to create Kafka producer: %v", err)
    }
    defer producer.Close()

    csvFile, err := os.Open(*csvFileFlag)
    if err != nil {
        log.Fatalf("Failed to open CSV file: %v", err)
    }
    defer csvFile.Close()

    reader := csv.NewReader(bufio.NewReader(csvFile))
    _, err = reader.Read() // Read and ignore the headers
    if err != nil {
        log.Fatalf("Failed to read header from CSV file: %v", err)
    }

    codec, err := goavro.NewCodec(schema)
    if err != nil {
        log.Fatalf("Failed to create Avro codec: %v", err)
    }

    for {
        record, err := reader.Read()
        if err == io.EOF {
            break
        } else if err != nil {
            log.Fatalf("Error reading line from CSV: %v", err)
        }

        var timestampMicros int64
        if *useCurrentTimeFlag {
            // Use the current time in microseconds
            timestampMicros = time.Now().UnixNano() / 1000
        } else {
            // Parse the timestamp from the CSV file
            parsedTime, err := time.Parse(time.RFC3339Nano, record[4])
            if err != nil {
                log.Fatalf("Failed to parse timestamp: %v", err)
            }
            timestampMicros = parsedTime.UnixNano() / 1000
        }

        dataMap := map[string]interface{}{
            "symbol":    record[0],
            "side":      record[1],
            "price":     parseToDouble(record[2]),
            "amount":    parseToDouble(record[3]),
            "timestamp": timestampMicros,
        }

        binaryData, err := codec.BinaryFromNative(nil, dataMap)
        if err != nil {
            log.Fatalf("Failed to encode Avro data: %v", err)
        }

        var buf bytes.Buffer
        buf.WriteByte(0) // Magic byte
        binary.Write(&buf, binary.BigEndian, int32(schemaID))
        buf.Write(binaryData)

        if *delayMsFlag > 0 {
            time.Sleep(time.Millisecond * time.Duration(*delayMsFlag))
        }

        _, _, err = producer.SendMessage(&sarama.ProducerMessage{
            Topic: *topicFlag,
            Value: sarama.ByteEncoder(buf.Bytes()),
        })
        if err != nil {
            log.Fatalf("Failed to send message: %v", err)
        }

        if *verboseFlag {
            fmt.Printf("Sent message to %s: %+v\n", *topicFlag, dataMap)
        }
    }

    if *verboseFlag {
        fmt.Println("Finished sending messages.")
    }
}

func parseToDouble(s string) float64 {
    val, err := strconv.ParseFloat(s, 64)
    if err != nil {
        log.Fatalf("Failed to parse float: %v", err)
    }
    return val
}

