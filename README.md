# Time Series Streaming Analytics Template

This repository can be used as a template for near real-time analytics using open source technologies.

The project sends events to a message broker (Apache Kafka), persists them into a fast time-series database ([QuestDB](https://questdb.io)), and visualizes them on a dashboard (Grafana). It also provides a web-based development environment (Jupyter Notebook) for data science and machine learning, and monitoring metrics are captured by a server agent (telegraf) and stored into the time-series database (QuestDB).

The template includes workflows to capture, process and analyze crypto currency trading data, public GitHub repositories data, and (simulated) smart meters, factory plant sensors, and IoT data.

![trading data dashboard](trading_data_dashboard_screenshot.png)


The dataset with most examples available in this project is the trading dataset, which contains real crypto currency trades observed between March 1st and March 12th 2024.

All the components can be started with a single `docker-compose` command, or can be deployed independently.

_Note_: Even if the template starts multiple instances of brokers and workers for higher availability, all the components
use the bare minimum configuration needed to run this template. Make sure you double check the configuration and adjust
accordingly if you are planning to run this in production.

## Pre-requisites

A working installation of Docker and docker-compose.

### Pre-requisities only for the GitHub Dataset

In order to run the GitHub ingestion script, you need a Github Token, so the script will be able to get live data from the GitHub API.
I recommend using a [personal token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
with read access to public repositories only.

Once you have the token, you can set is as an environment variable and it will be picked up by all the scripts (and by docker-compose for the Jupyter Notebook environment)

```bash
export GITHUB_TOKEN=<YOUR_TOKEN>
docker-compose up
```
or, if using sudo with Docker:

`sudo GITHUB_TOKEN=<YOUR_TOKEN> docker-compose up`


## Starting up via Docker-compose

This is the recommended way to start all the components, as they will have all dependencies and configuration ready. If you prefer to start each component separately, read the [Starting and configuring components individually](#starting-and-configuring-components-individually) section below. We will be going through each component, but you can check later in this document all the [docker volumes and ports](#full-list-of-components-ports-and-volumes) we are configuring.

From the root directory of this repository, execute:

`docker-compose up`

This might take a few moments the first time, as it needs to download several docker images and initialize them. For reference, a cold
start on my laptop over a wired connection it takes between 30 seconds and 1 minute. Subsequent starts should be way
faster. The downloaded images will use about 1Gb on your disk.

If you notice any permissions error on the logs (typically Grafana complaining a folder is not writable), this is probably due to your system running docker
as root. You can fix this by setting the following env variable:

```
export DOCKER_COMPOSE_USER_ID=$(id -u)
```

or like this
```
sudo DOCKER_COMPOSE_USER_ID=$(id -u) docker-compose up
```


After a few moments, you should see the logs stabilize and stop scrolling fast. After a few seconds you should see
several logs from Kafka Connect registering the connectors and showing the configuration on the logs. At that point the
project is fully available.There will always be some activity, as the stack collects and store some metrics, but those
appear only every few seconds.

```mermaid
graph TD
   subgraph "Data Analytics"
    Q[QuestDB]
  end

  subgraph "Data Science and ML"
    Q -->|SELECT FROM trades and github_events| DSN[Data Science Notebook]
    Q -->|SELECT FROM trades and github_events| FM[Forecast Model]
  end


  subgraph "Data Ingestion"
    GE[Trading Events, GitHub Events, Smart Meters, Transactions] -->|Python, NodeJS, Java, Go, Rust into topics | AK[Apache Kafka]
    AK -->|github_events topic| KC
    IO[IoT Events] -->|ILP Protocol into iot_data table| Q
    IE[Trading Events] -->|ILP Protocol into trades table| Q
    PS[Plant Sensors] -->|ILP Protocol into plant_sensors table| Q
    AK -->|trades topic| KC
    AK -->|trades topic| KSR[Kafka Schema Registry]
    AK -->|smart-meters topic| KC
    AK -->|smart-meters topic| KSR
    AK -->|transactions topic| KC
    AK -->|transactions topic| KSR
    KC[Kafka Connect] -->|into github_events table| Q[QuestDB]
    KC[Kafka Connect] -->|into trades table| Q[QuestDB]
    KC[Kafka Connect] -->|into smart_meters table| Q[QuestDB]
    KC[Kafka Connect] -->|into transactions table| Q[QuestDB]
  end

  subgraph "Real-time dashboards"
    Q -->|SELECT FROM trades, github_events, smart_meters, transactions, plant_sensors, and iot_data tables| G[Grafana]
  end



  subgraph Monitoring
    Q -->|pulls Prometheus metrics| TA[Telegraf Agent]
    AK -->|pulls MX metrics| TA
    TA -->|into monitoring tables| Q
  end
```
If you want to stop the components at any point, you can just `ctrl+c` and you can restart later running `docker-compose up`. For more permanent removal, please do check the
[Stopping all the components](#stopping-all-the-components) section.


## End-to-end ingestion and visualization

### Ingesting the trading real-time data

In this section we will use the Jupyter Notebook environment to ingest data using Python. To ingest the trading dataset
using Golang, or Python from the command line, please go to the [ingestion](#ingestion) section of this document for details.

Navigate to [http://localhost:8888/notebooks/Send-Trades-To-Kafka.ipynb](http://localhost:8888/notebooks/Send-Trades-To-Kafka.ipynb).

This notebook will read the `tradesMarch.csv` file to read trading events, and will send the events to Apache Kafka in
Avro binary format using a topic named `trades`. The CSV file contains real trades from different crypto currency symbols
captured with the Coinbase API between March 1st and March 12th 2024. The raw data has been sampled in 30s intervals and
it contains almost one million rows. By default, the script will override the original date with the current date and
 will wait 50ms between events before sending to Kafka, to simulate a real time stream and provide
a nicer visualization. You can override those configurations by changing the constants in the script. It will keep
sending data until you click stop or exit the notebook, or until the end of the file is reached.

The data you send to Kafka will be then polled by Kafka Connect and passed to QuestDB, where it will be stored into a table named `trades`.

#### Ingesting trading data directly into QuesDB, skipping Kafka

Having a message broker like Kafka in front of QuestDB makes sense, as you can replay messages in the case of any error, and
also allows for interesting scenarios, like zero downtime upgrades. You can ingest data into Kafka and upgrade/restart
QuestDB, and when QuestDB is available again the data from Kafka will be inserted into the database.

But, if you are fine skipping Kafka and want to ingest directly into QuestDB, you can check the [http://localhost:8888/notebooks/Send-Trades-To-QuestDB-Directly.ipynb](http://localhost:8888/notebooks/Send-Trades-To-QuestDB-Directly.ipynb) notebook.

This notebook, sends trades from several sub-processes in parallel, as this gives you higher throughput. The script uses
QuestDB API to insert data directly

#### Visualizing the trading dataset

For now, you can navigate to the live dashboard at [http://localhost:3000/d/trades-crypto-currency/trades-crypto-currency?orgId=1&refresh=250ms](http://localhost:3000/d/trades-crypto-currency/trades-crypto-currency?orgId=1&refresh=250ms). User is `admin` and password `quest`.

You should see how data gets updated. The dashboard auto refreshes every 250 milliseconds. For the first few seconds some
 of the charts might look a bit empty, but after enough data is collected it should look better.

![trading data dashboard](trading_data_dashboard_screenshot.png)

You can now proceed to [checking Data on Kafka](#checking-data-on-kafka), unless you prefer to also ingest GitHub data. In
the next sections discuss mostly the Trading dataset, but you can easily adapt all the queries and scripts to use the
GitHub or any other dataset instead.


### Ingesting the GitHub real-time data

In this section we will use the Jupyter Notebook environment to ingest data using Python. To ingest data using NodeJS,
Golang, Rust, or JAVA, please go to the [ingestion](#ingestion) section of this document for details.

Navigate to [http://localhost:8888/notebooks/Send-Github-Events-To-Kafka.ipynb](http://localhost:8888/notebooks/Send-Github-Events-To-Kafka.ipynb).

This notebook will use the GitHub API to collect public events, will send the events to Apache Kafka using a topic named `github_events`, then wait 10 seconds to avoid any API rates. It will
keep sending data until you click stop or exit the notebook.

Before you run the notebook, make sure you had set the `GITHUB_TOKEN` environment variable. Or
you can just paste it where it says `<YOUR_GITHUB_TOKEN>`.

The data you send to Kafka will be passed to QuestDB, where it will be stored into a table named `github_events`. We will explore the database later.

For now, you can navigate to the live dashboard at [http://localhost:3000/d/github-events-questdb/github-events-dashboard?orgId=1&refresh=5s](http://localhost:3000/d/github-events-questdb/github-events-dashboard?orgId=1&refresh=5s). User is `admin` and password `quest`.

![github events dashboard](github_events_dashboard_screenshot.png)

You should see how data gets updated. The dashboard auto refreshes every 5 seconds, but data is only collected every 10 seconds, so it will take ~10 seconds to see new results on the charts. For the first few minutes some of the charts might look a bit empty, but after enough data is collected it should look better.

At this point you can see you already have a running system in which you are capturing data and
running it through an end-to-end data analytics platform.


## Checking Data on Kafka

[Apache Kafka](https://kafka.apache.org/) provides a unified, high-throughput, low-latency platform for handling real-time data feeds. Data is
organized into `topics` and store reliably for a configured retention period. Consumers can then read data from those
topics immediately, or whenever is more convenient for them.

Kafka uses a binary TCP-based protocol that is optimized for efficiency and allows Kafka to turn a bursty stream of random message writes into linear writes.

There are many open source and commercial tools to add a web interface to Apache Kafka, but Apache Kafka itself doesn't
has any interface other than its API. However, Kafka includes [several command line tools](https://docs.confluent.io/kafka/operations-tools/kafka-tools.html)
we can use to manage our cluster and to query configuration and data.

We can, for example, use the `kafka-topics` tool to list and manage topics. Since we are already running a container with
docker, we can attach to the container and invoke Kafka topics from itself, as in:

`docker exec -ti rta_kafka_broker kafka-topics --list --bootstrap-server localhost:9092`

If you run the Jupyter Notebook `Send-Trades-To-Kafka.ipynb`, the output of this command should include a topic
named `trades`.

We can also consume events from that topic by running:
`docker exec -ti rta_kafka_broker kafka-console-consumer --bootstrap-server localhost:9092 --topic trades`.

You will notice the output is very weird. When you are running any of the examples (trades, smart_meters, or transactions) that use
AVRO instead of JSON, the output will be in AVRO binary format. To check output of AVRO topics in kafka we provide a
python script under `ingestion/python`. The
script reads data from Kafka and then deserializes to a text format. You can execute using docker via:

```shell
docker exec -it rta_jupyter python /home/ingestion/kafka_avro_reader.py --topic smart-trades --broker rta_kafka_broker:29092 --schema-registry http://rta_schema_registry:8081
```

If you have been sending data using the GitHub dataset, you can just use the regular `kafka-console-consumer` as the
GitHub example uses JSON, which is human readable and text-based.

If you didn't stop the Jupyter Notebook, you should see new entries every few seconds. If you stopped it, you can
[open the trades ingestion notebook](http://localhost:8888/notebooks/Send-Trades-To-Kafka.ipynb), or the
[GitHub ingestion notebook](http://localhost:8888/notebooks/Send-Github-Events-To-Kafka.ipynb)
and run it again. New entries should appear on your console as it runs.

Notice that even if we are consuming data from the topic, the data is still being ingested into QuestDB. This is one of
the main advantages of Kafka: multiple consumers can read data from any topic without interfering with each other, and
the system keeps track of the latest event each consumer saw, so it would send by default only newer messages.

However, a consumer can choose to replay data from any point in the past, as long as it is within the retention time range for a
given topic. Or you can also choose to have multiple consumers reading data from a topic collaboratively, so each message
is sent only to a single consumer. Not only that, but if you have demanding requirements, you can add several brokers to
your cluster and partition the topics so the workload will be distributed. All of this with very high performance and
configurable redundancy.

Having Apache Kafka as the entry point for your data analytics pipeline gives you a good and reliable way of dealing with
data at any speed and helps you deal with ingestion peaks, decoupling ingestion from your analytical database. Even when
you have a very fast database, as it is the case with QuestDB, that could keep up with the ingestion rate, it might
still be a good idea to have Kafka in front so you can tolerate database restarts in the event of any upgrade, or data
replaying in case of disaster recovery or debugging.


## Checking the connector data on Kafka Connect

Apache Kafka is not a push system, [by design](https://kafka.apache.org/documentation.html#design_pull). That means
that consumers need to poll data at its own pace whenever they are ready to process a new batch of events. While this
is a good idea from an architecture perspective, implementing that in a reliable way on your consumer is not trivial.

Very conveniently, Apache Kafka comes with [Kafka Connect](https://docs.confluent.io/platform/current/connect/index.html),
a tool for scalably and reliably streaming data between Apache Kafka and other data systems.

Kafka connect can run as a standalone process or in distributed mode — for scalability and fault tolerance —, and can
also run conversions and transforms on the fly before sending data to its destination.

You need two things to stream data from Apache Kafka into another system: A connector plugin, in this case the
`kafka-questdb-connector-0.9.jar`, and a configuration file which, at the very least, will define the origin topic(s),
the data format, and the destination system.

As it happens with Apache Kafka, there is no native web interface for Kafka Connect, but it exposes a REST API — by
default on port 8083 — where we can register new configurations for our connections, or check the ones we already have.
If you are curious, you can inspect the `docker-compose.yml` file to see how it registers different configurations
on startup. But it is probably easier to just open the [Kafka-connect-inspect.ipynb](http://localhost:8888/notebooks/Kafka-connect-inspect.ipynb)
jupyter notebook and execute the cells there, that will connect to the kafka-connect container and output the list of
connector plugins available in the classpath, the registered connectors, and the configuration for each of the three.

You will notice the configurations will output data to the questdb-connector plugin, using  different Kafka topics for
the input data, and different tables on the QuestDB database for the output. You will also notice data is expected
in JSON format or AVRO format, depending on the topic. The full list of parameters available to this connector is
[documented at the QuestDB website](https://questdb.io/docs/third-party-tools/kafka/questdb-kafka/).


## Querying Data on QuestDB

 [QuestDB](https://questdb.io) is fast time-series database for high throughput and fast SQL queries with operational simplicity. It is designed to run performant analytics over billions of rows. Since we are
 working with streaming data, and streaming data tends to have a timestamp and usually requires timely
 analytics, it makes sense to use a time-series database rather than a generic one.

 QuestDB can ingest data in a number of ways: using Kafka Connect, as we are doing in this template, via
 the [QuestDB Client Libraries](https://questdb.io/docs/reference/clients/overview/) for fast ingestion,with any [Postgresql-compatible library](https://questdb.io/docs/develop/insert-data/#postgresql-wire-protocol),  issuing HTTP calls to the [REST API(https://questdb.io/docs/develop/insert-data/#http-rest-api), or simply [uploading CSV files](https://questdb.io/docs/develop/insert-data/#uploading-csv-files).

 Data is stored into tables and queried via SQL. You can issue your SQL statements with any Postgresql driver or with any HTTP client via the REST API.

QuestDB offers a web console for running queries and uploading CSVs at [http://localhost:9000](http://localhost:9000).

If you have been ingesting data with the Jupyter Notebook `Send-Trades-To-Kafka.ipynb`, you should see
one table named `trades`. If you have been ingesting other datasets, you will see a different table there. You will
eventually see other tables with monitoring data from QuestDB itself and from the Kafka broker, as we are collecting metrics
and ingesting them into QuestDB for [monitoring](#monitoring-metrics).

Other than standard SQL, QuestDB offers [SQL extensions](https://questdb.io/docs/concept/sql-extensions/) for dealing with time-series data. You can for example
run any of these queries (depending on which dataset you are using):

```SQL
SELECT timestamp, symbol, COUNT() FROM trades SAMPLE BY 5m;
SELECT timestamp, repo, COUNT() FROM github_events SAMPLE BY 5m;
```

This query returns the count of trades or github events by symbol or by repository in 5 minute intervals. Intervals can be any arbitrary amount from microseconds to years.

Data on QuestDB is stored in a columnar format, [partitioned by time](https://questdb.io/docs/concept/partitions/), and physically sorted by increasing timestamp. Ingestion and Querying don't block each other, so ingestion performance remains steady even when there is high usage of queries. With a few CPUs, you can sustain ingestions of several millions of rows per second while querying billions of rows.

All of the above makes QuestDB a great candidate for storing your streaming data.

### Querying QuestDB from a Jupyter Notebook

Since QuestDB is compatible with the Postgresql-wire protocol, we can issue queries from any programming language. You can, for example, use Python and the popular `psycopg` library to query data. Let's open the
Jupyter Notebook [http://localhost:8888/notebooks/questdb-connect-and-query.ipynb]([http://localhost:8888/notebooks/questdb-connect-and-query.ipynb) and execute the script in there.

You will notice QuestDB uses the user `admin`, password `quest`, postgresql port `8812`, and dbname `qdb` by default.


## Data Science and Machine Learning with a Jupyter Notebook

Many projects are happy analysing the past, some also want to predict what will happen based on past data. Time-series forecasting is a very frequent ask when doing streaming analytics.

Of course this is not trivial, but fortunately there are some ready-made models or algorithms that you can use as an starting point. This template provides the
Jupyter Notebooks [http://localhost:8888/notebooks/Time-Series-Forecasting-ML.ipynb](http://localhost:8888/notebooks/Time-Series-Forecasting-ML.ipynb) and [http://localhost:8888/notebooks/Time-Series-Forecasting-ML-trades.ipynb](http://localhost:8888/notebooks/Time-Series-Forecasting-ML-trades.ipynb) to show how
you can train a model with data from from the QuestDB `trades` or `github_events` table, and use that to run predictions. The notebook shows how to train two different
models: [Prophet](https://github.com/facebook/prophet?tab=readme-ov-file#installation-in-python---pypi-release) and [Linear Regression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html).

_Note_: This notebook is not a comprehensive work in time-series forecasting, but just a show of what can be achieved. In a real-life scenario you would ideally use a large amount of training data and you would probably fine-tune the model for your use case. Other popular time-series models like ARIMA might give you better results in certain scenarios. If your dataset is very big, you might also want to try LSTM models that could perform better in some cases.


## Visualizing data with Grafana

Grafana is an observability platform you can use to display business or monitoring dashboards and to generate alerts if
some conditions are met.

Grafana supports a large number of datasources. In our case, you will be using Grafana to connect to QuestDB, and
display business dashboards that get data running SQL queries behind the scenes. The grafana instance in this template
is pre-configured with a database connection using the QuestDB native connector to run queries on QuestDB. If you want
to check the details, the Grafana config, connection, and dashboards are available at the [./dashboard/grafana](./dashboard/grafana)
folder in this repository.


If you've been following the previous steps, you have already seen the trading dashboard at [http://localhost:3000/d/trades-crypto-currency/trades-crypto-currency?orgId=1&refresh=250ms](http://localhost:3000/d/trades-crypto-currency/trades-crypto-currency?orgId=1&refresh=250ms) or the GitHub one at
[http://localhost:3000/d/github-events-questdb/github-events-dashboard?orgId=1&refresh=5s](http://localhost:3000/d/github-events-questdb/github-events-dashboard?orgId=1&refresh=5s). (User is `admin` and password `quest`).


If you click at the three dots on the top right of any of the charts in that dashboard and then you click 'Explore', you will see
the SQL query powering the dashboard. For example, one of the queries in that panel is:

`SELECT timestamp as time, type, count(*) as total FROM github_events sample by 15s;`

If you click on `Edit` rather than `Explore`, you can change the chart type and configuration, but you won't be able to
save the pre-provisioned dashboard as they are protected. You can always click on the `dashboard settings` icon at the
top right of the screen, and then `save as` to have your copy so you can play around.

For details on how to integrate QuestDB and Grafana you can visit the
[QuestDB Third Party Tools](https://questdb.io/docs/third-party-tools/grafana/) docs.

## Ingestion

You have already seen how to send data to Kafka from a [Jupyter Notebook](#end-to-end-ingestion-and-visualization). If
you prefer to send data to Kafka from a stand-alone Python script, or if you want to use other programming languages,
this template provides [several scripts you can use](#ingesting-streaming-data-into-kafka-using-go-java-or-python).

If you prefer to skip sending data to Kafka and prefer to ingest directly into QuestDB, please skip to [the next section](#ingesting-streaming-data-directly-into-questdb)

### Ingesting streaming data into Kafka using Python, NodeJS, Java, Go, or Rust

The scripts will ingest the `trades` dataset sending data to a `trades` topic in Kafka. This script reads from
a .CSV file and sends data to Kafka using AVRO and the Kafka Schema Registry. You can pass `--help` for options. The
script will stop after reading the whole CSV (~1,000,000 rows)

Using the local python interpreter:

```
python send_trades_to_kafka.py ../../notebooks/tradesMarch.csv trades
```

Using the already running Jupyter container:
```
docker exec -it rta_jupyter python /home/ingestion/send_trades_to_kafka.py --kafka_broker rta_kafka_broker:29092 --schema_registry http://rta_schema_registry:8081 --no-timestamp-from-file /home/jovyan/tradesMarch.csv trades
```


Alternatively, you can  read data from the GitHub public API, and will send to a Kafka topic named `github_events`. New events
will be fetched every 10 seconds to avoid any API rate limits.

All the scripts in this section require the `GITHUB_TOKEN` environment variable.

`export GITHUB_TOKEN=<YOUR_TOKEN>`

#### Python

Open the `./ingestion/python` folder and install the requirements

```
pip install -r requirements.txt
```

Now just execute via

```
python github_events.py
```

We also offer a `smart meters` dataset, that sends data to a `smart-meters` topic in Kafka. This script generates
synthetic data and sends data to Kafka using AVRO and the Kafka Schema Registry. You can pass `--help` for options.
Options allow you to control the number of devices or the message rate. The script will stop when reaching the
`max-messages` number, which defaults to 1,000,000.


Using the local python interpreter:

```
python smart_meters_send_to_kafka.py
```

Using the already running Jupyter container:
```
docker exec -it rta_jupyter python /home/ingestion/smart_meters_send_to_kafka.py --broker rta_kafka_broker:29092 --schema-registry http://rta_schema_registry:8081
```

#### Go

Open the `./ingestion/go/github_events` folder and get the dependencies

```
go get
```

Now just execute via

```
go run .
```

Alternatively, you can ingest the `trades` dataset sending data to a `trades` topic in Kafka. This script reads from
a .CSV file and sends data to Kafka using AVRO and the Kafka Schema Registry. Change to the `./ingestion/go/trades`
folder and get the dependencies.

```
go get
```

Now just execute via

```
go run trades_sender.go --topic="trades" --csv=../../../notebooks/tradesMarch.csv --subject="trades-value"
```


#### NodeJS

In NodeJS we only expose the GitHub dataset example, but it should be easy to adapt for other datasets.

Open the `./ingestion/nodejs` folder and install the dependencies

```
npm install node-rdkafka @octokit/rest
```

Now just execute via

```
node github_events.js
```

#### Java

In Java we only expose the GitHub dataset example, but it should be easy to adapt for other datasets.

Open the `./ingestion/java/github_events` folder and build the jar file

```
mvn package
```

Now just execute via

```
java -jar target/github-events-1.0-SNAPSHOT-jar-with-dependencies.jar
```


#### Rust

In Rust we only expose the GitHub dataset example, but it should be easy to adapt for other datasets.

Open the `./ingestion/rust/github_events` folder and execute via

```
cargo run
```

The initial execution will take a few seconds as the project is built. Subsequent executions should start immediately.


### Ingesting streaming data directly into QuestDB

QuestDB is designed for high throughput, and can ingest streaming data at over 4 million events per second (using 12 CPUs and a fast drive).

If your only reason to use Kafka in front of QuestDB is for ingestion speed, it might be the case you don't need it.

Of course having Kafka as the ingestion layer gives you more flexibility, as you can easily send data to multiple
consumers — other than QuestDB —, or you can restart the QuestDB server without stopping ingestion. On the other hand,
adding Kafka means some (minor) extra latency and one more component to manage.

In the end, some teams would prefer to ingest into Kafka, and some directly into QuestDB. It all depends on your
specific use case. QuestDB supports multiple ways of ingesting data, but the fastest is by using the ILP protocol
via the [official client libraries](https://questdb.io/docs/reference/clients/overview/).

The Jupyter Notebooks [http://localhost:8888/notebooks/Send-Trades-To-QuestDB-Directly.ipynb](http://localhost:8888/notebooks/Send-Trades-To-QuestDB-Directly.ipynb)
and [http://localhost:8888/notebooks/IoTEventsToQuestDB.ipynb](http://localhost:8888/notebooks/IoTEventsToQuestDB.ipynb)
use the Python client for convenience, but the usage would be very similar using the client libraries available in
NodeJs, Java, .Net, C/C++, Rust, or Go.

The notebooks connects to port 9000 of the questdb container and sends data into a table named "trades" or "iot_data". The data is
just randomly generated to keep the demo as simple as possible.


While you are running the IoT notebook, you can see a live dashboard at
[http://localhost:3000/d/qdb-iot-demo/device-data-questdb-demo?orgId=1&refresh=500ms&from=now-5m&to=now](http://localhost:3000/d/qdb-iot-demo/device-data-questdb-demo?orgId=1&refresh=500ms&from=now-5m&to=now).
The user for Grafana login is `admin` and password `quest`.

#### Ingesting data using parallel processes

When ingesting into QuestDB, it is a good idea to send data in parallel from multiple senders, to achieve greater throughput.

If you want to experiment with inserting data faster, you can explore the Notebook [http://localhost:8888/notebooks/ParallelIoTEventsToQuestDB.ipynb](http://localhost:8888/notebooks/ParallelIoTEventsToQuestDB.ipynb).

We have prepared a dashboard to show througput data, including total events seen and events per second, at
[http://localhost:3000/d/qdb-iot-parallel-demo/parallel-data-demo?orgId=1&refresh=1s](http://localhost:3000/d/qdb-iot-parallel-demo/parallel-data-demo?orgId=1&refresh=1s).
The user for Grafana login is `admin` and password `quest`.


## Monitoring metrics

To monitor data, you usually have an agent running on your servers that collects metrics and then ingest into a time-series database.
There are many agents to choose from, but a popular option that works well with Kafka and QuestDB is the
[Telegraf Agent](https://github.com/influxdata/telegraf/tree/master).

Telegraf supports many input plugins as metrics origin, many output plugins as metrics destination, and supports
aggregators and transforms between input and output.

In this template, we have a telegraf configuration in the `./monitoring/telegraf` folder. The configuration reads
metrics from the questdb monitoring endpoint (in prometheus format) `http://questdb:9003/metrics` and from the Kafka
MX metrics server that we are exposing through a plugin on `http://broker:8778/jolokia`.

After collecting the metrics and applying some filtering and transforms, metrics are then written into several tables in QuestDB.

On a production environment you would probably want to store metrics on a different server, but for this template we are
storing the metrics in the same QuestDB instance where we store the user data.

We are not providing any monitoring dashboard on this template, but feel free to explore the metrics on the
Jupyter Notebook [http://localhost:8888/notebooks/Monitoring-Kafka-and-Questdb.ipynb](http://localhost:8888/notebooks/Monitoring-Kafka-and-Questdb.ipynb),
or even better at `http://localhost:9000`, and then try to create a Grafana dashboard at `http://localhost:3000`.


## Full list of components, ports, and volumes

We have already mentioned most of these in previous sections or notebooks, but for your reference, this is the full list
 of components, docker mounted volumes and open ports when you start with `docker-compose up`:

- broker and broker-2: The Apache Kafka broker. We start two instances, for higher availability
    - volumes: It mounts a volume using the local `./monitoring/kafka-agent` for a needed .jar dependency to enable monitoring, then three volumes under the `./broker-1` and
    `broker-2` local folders for Kafka data and metadata
    - port 29092 (reachable only from the other containers) for bootstrap server
    - port 9002 (reachable from the host machine using `localhost:9092`) for bootstrap broker
    - port 9003 (reachable from the host machine using `localhost:9093`) for bootstrap broker 2
    - port 9101 for JMX metrics
    - port 9102 for JMX metrics of broker 2
    - port 8778 for the broker monitoring metrics we collect with Telegraf
    - port 8779 for the broker-2 monitoring metrics we collect with Telegraf
    - connects_to: it doesn't initiate any connections, but it gets incoming connections from `kafka-conect`, `jupyter-notebook`, and `telegraf`
- kafka-connect: We also provide 2 workers, for higher throughput and higher availability
    - volumes: It mounts a volume using the local `./kafka-connect-plugins`, needed to enable ingestion into questdb
    - port 8083 for the REST API for the connect service in worker 1
    - port 8084 for the REST API for the connect service in worker 2
    - connects to: `broker:29092`, `broker-2:29092` and `questdb:9000`
- schema_registry:
    - port 8081 for the Kafka Schema Registry HTTP interface
    - connects to: `broker:29092` and  `broker-2:29092`
- questdb:
    - volumes: It will mount a volume using the local `./questdb_root` folder. This folder will store all the database files. It is safe to remove the contents of the folder between restarts if you want to wipe the whole database.
    - port 9000 is the REST API and web console, available at http://localhost:9000
    - port 9000 is also used for streaming data via HTTP
    - port 9009 is for sending streaming data via socket (not used in this repository)
    - port 8812 is the Postgres-wire protocol. You can connect using any postgresql driver with the user: `admin` and password `quest`
    - port 9003 is for healthcheck `http://localhost:9003` and metrics `http://localhost:9003/metrics`
    - connects to: it doesn't initiate any connections, but it gets incoming connections from `kafka-conect`, `jupyter-notebook`, and `telegraf`
- grafana:
    - volumes: It mounts two volumes, pointing at the subfolders of `./dashboard/grafana/home_dir/`. These are used for storing the pre-provisioned credentials, connections, and dashboards, and for any new dashboards you create.
    - port 3000 is the Grafana UI.  `http://localhost:3000`. User is `admin` and password `quest`
    - connects to: `questdb:8812` for getting the data to display
- jupyter-notebook:
    - volumes: it mounts a volume using the `./notebooks` folder. It contains the pre-provisioned notebooks and any new notebooks you create.
    - port 8888: web interface for the Jupyter Notebook environment `http://localhost:8888`
    - connects to: The pre-provisioned scripts will connect to `questdb:8812`, `questdb:9000`, and `broker:29092`
- telegraf:
    - volumes: it mounts a read only volume using the local folder `./monitoring/telegraf/`. This contains the configuration for metrics collection from Apache Kafka and QuestDB.
    - ports: No ports are opened for telegraf
    - connects to: It will connect to `broker:8778`, `broker-2:8779`, `questdb:9003`, and it will write metrics into questdb via `questdb:9000`


## Stopping all the components

You can stop all the components by running
`docker-compose down`

Alternatively you can also remove the associated docker volumes (the locally mounted directories will keep the data and
configurations)
`docker-compose down -v`

If you want to remove all the components and their associated docker images (they use about 1Gig on your disk), you can run
`docker-compose down -v --rmi all`

Please note this will still keep the data in the locally mounted directories, most notably in the QuestDB, Kafka brokers, and Grafana
folders. You can remove the local data like this
`rm -r questdb/questdb_root/* broker-1/kafka-data/* broker-1/tmp/* broker-1/kafka-secrets/* broker-2/kafka-data/* broker-2/tmp/* broker-2/kafka-secrets/* dashboard/grafana/home_dir/var_lib_grafana/alerting dashboard/grafana/home_dir/var_lib_grafana/grafana.db dashboard/grafana/home_dir/var_lib_grafana/csv`


## Starting and configuring components individually
TODO (refer to docker-compose documentation to start individual containers)


