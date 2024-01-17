# streaming-analytics-template

Template to quickstart streaming analytics using Apache Kafka for ingestion, QuestDB for time-series storage and analytics, Grafana for near real-time dashboards, and Jupyter Notebook for data science

This template is a work in progress and not ready to be used yet.

## Deploying the template


* Local installation using docker-compose. Recommended for quick low-friction demo, as long as you have docker/docker-compose installed locally and are comfortable using them
* Local installation using docker but doing step-by-step. Recommended to learn more about the details and how everything fits together


## Docker-compose local deployment

Docker compose will provision an environment with  Apache Kafka, Apache Kafka Connect,  Questdb, Grafana, and Jupyter Notebook. The whole process will take about 1-2 minutes, depending on yout internet speed downloading the container images.

```
git clone https://github.com/javier/streaming-analytics-template.git
cd streaming-analytics-template
docker-compose up
```

After starting, all the components should be available, but you will not see data until you proceed to the next step, ingestion.


The grafana web interface will be available at http://localhost:13000/d/qdb-ilp-demo/device-data-questdb-demo?orgId=1&refresh=5s.
User is "demo" and password is "quest".

The QuestDB console is available at http://localhost:19000. Default user not needed, but it is "admin", with password "quest"

The Jupyter notebook will be available at http://localhost:18888 


Stop the demo via:

```
docker-compose down
```


## Data Ingestion

You probably want to send data to Kafka  and from there to QuestDB, but if you want to skip Kafka and send directly to QuestDB, you can skip to the next section

### Ingesting streaming data into Kafka using Go, Java, or Python

### Ingesting streaming data directly into QuestDB using Go, Java, or Python


