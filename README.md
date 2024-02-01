# Time Series Streaming Analytics Template

This repository can be used as a template for near real-time analytics using open source technologies.

It will collect public events from the GitHub API, send them to a message broker (Apache Kafka), persist them into a fast time-series database (QuestDB), and visualize them on a dashboard (Grafana). It also provides a web-based development environment (Jupyter Notebook) for data science and machine learning, and monitoring metrics are captured by a server agent (telegraf) and stored into the time-series database (QuestDB).

All the components can be started with a single `docker-compose` command, or can be deployed independently. The included components are:

- Ingestion scripts in Python, Java, Golang, Rust, and NodeJS. These scripts read public data from the GitHub events API
and send them to Apache Kafka
- Apache Kafka, message broker for reliable high-performance event ingestion and temporary storage.
- Kafka Connect, component to pipe data between Apache Kafka and QuestDB.
- QuestDB, fast time-series database for permanent storage and for both real-time and batch analytics.
- Telegraf, server agent to collect metrics from Kafka and QuestDB and store them in QuestDB for monitoring.
- Grafana, observability platform to connect to QuestDB and display business and monitoring dashboards in real time.
- Jupyter Notebook, web-based interactive platform to explore and prepare data, and to train forecasting models.

_Note_: All the components use the bare minimum configuration needed to run this template. Make sure you double check the configuration and adjust accordingly if you are planning to run this in production.

## Pre-requisites

In order to run the ingestion scripts, you need a Github Token. I recommend using a token with read access to public repositories only. https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens

Once you have the token, you can set is as an environment variable and it will be picked up by all the scripts (and by docker-compose for the Jupyter Notebook environment)

`export GITHUB_TOKEN=<YOUR_TOKEN>`

An unsafer alternative would be pasting the token directly in the script.

## Starting up via Docker-compose

This is the recommended way to start all the components, as they will have all dependencies and configuration ready. If you prefer to start each component separately, read the _Starting and configuring components individually_ section below.

From the root directory of this repository, execute:

`docker-compose up`

This might take a few moments, as it needs to download several docker images and initialize them. For reference, a cold
start on my laptop over a wired connection it takes between 30 seconds and 1 minute. Subsequent starts should be way
faster. The downloaded images will use about 1Gb on your disk.

After a few moments, you should see the logs stabilize and stop scrolling fast. There will always be some activity, as the stack collects and store some metrics, but those appear only every few seconds. At that
point the project is fully available.

## End-to-end ingestion and visualization

To ingest data using NodeJS, Golang, Rust, or JAVA, please go to the `ingestion` section of this document for details. In this section we will use the Jupyter Notebook environment to ingest data using Python.

Navigate to `http://localhost:8888/notebooks/SendGithubEventsToKafka.ipynb`.

This notebook will use the GitHub API to collect public events, will send the events to Apache Kafka using a topic named `github_events`, then wait 10 seconds to avoid any API rates. It will
keep sending data until you click stop or exit the notebook.

Before you run the notebook, make sure you had set the `GITHUB_TOKEN` environment variable. Or
you can just paste it where it says `<YOUR_GITHUB_TOKEN>`.

The data you send to Kafka will be passed to QuestDB, where it will be stored into a table named `github_events`. We will explore the database later.

For now, you can navigate to the live dashboard at `http://localhost:3000/d/github-events-questdb/github-events-dashboard?orgId=1&refresh=5s`. User is `admin` and password `quest`.

You should see how data gets updated. The dashboard auto refreshes every 5 seconds, but data is only collected every 10 seconds, so it will take ~10 seconds to see new results on the charts. For the first few minutes some of the charts might look a bit empty, but after enough data is collected it should look better.

At this point you can see you already have a running system in which you are capturing data and
running it through an end-to-end data analytics platform.

Let's explore a bit more.

## Checking Data on Kafka

TODO

## Checking the connector data on Kafka Connect

TODO

## Querying Data on QuestDB

TODO

### Querying data from Jupyter Notebooks

TODO

## Data Science and Machine Learning with Jupyter Notebooks

TODO

## Ingestion

TODO

## Monitoring metrics

TODO

## Full list of components, ports, and volumes

The list of components, together with their mounted volumes and available ports are:

- broker: The Apache Kafka broker
    - volumes: It mounts a volume using the local `./monitoring/kafka-agent` for a needed .jar dependency to enable monitoring
    - port 29092 (reachable only from the other containers) for bootstrap server
    - port 9002 (reachable from the host machine using `localhost:9092`) for bootstrap server
    - port 9101 for JMX metrics
    - port 8778 for the monitoring metrics we collect with Telegraf
    - connects_to: it doesn't initiate any connections, but it gets incoming connections from `kafka-conect`, `jupyter-notebook`, and `telegraf`
- kafka-connect:
    - volumes: It mounts a volume using the local `./kafka-connect-plugins`, needed to enable ingestion into questdb
    - port 8083 for the REST API for the connect service
    - connects to: `broker:29092` and `questdb:9009`
- questdb:
    - volumes: It will mount a volume using the local `./questdb_root` folder. This folder will store all the database files. It is safe to remove the contents of the folder between restarts if you want to wipe the whole database.
    - port 9000 is the REST API and web console, available at http://localhost:9000
    - port 9009 is for sending streaming data via socket
    - port 8812 is the Postgres-wire protocol. You can connect using any postgresql driver with the user: `admin` and password `quest`
    - port 9003 is for healtcheck `http://localhost:9003` and metrics `http://localhost:9003/metrics`
    - connects to: it doesn't initiate any connections, but it gets incoming connections from `kafka-conect`, `jupyter-notebook`, and `telegraf`
- grafana: It will mount two volumes, pointing at the subfolders of `./dashboard/grafana/home_dir/`. These are used for storing the pre-provisioned credentials, connections, and dashboards, and for any new dashboards you create/
    - port 3000 is the Grafana UI.  `http://localhost:3000`. User is `admin` and password `quest`
    - connects to: `questdb:8812` for getting the data to display
- jupyter-notebook: it mounts a volume using the `./notebooks` folder. It contains the
pre-provisioned notebooks and any new notebooks you create.
    - port 8888: web interface for the Jupyter Notebook environment `http://localhost:8888`
    - connects to: The pre-provisioned scripts will connect to `questdb:8812`, `questdb:9009`, and `broker:29092`
- telegraf: it mounts a read only volume using the local folder `./monitoring/telegraf/`. This contains the configuration for metrics collection from Apache Kafka and QuestDB.
    - ports: No ports are opened for telegraf
    - connects to: It will connect to `broker:8778`, `questdb:9003`, and `questdb:9009`


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

You probably want to send data to Kafka and from there to QuestDB, but if you want to skip Kafka and send directly to QuestDB, you can skip to the next section

### Ingesting streaming data into Kafka using Go, Java, or Python

### Ingesting streaming data directly into QuestDB using Go, Java, or Python


## Starting and configuring components individually

TODO
