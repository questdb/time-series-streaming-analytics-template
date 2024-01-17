# Building a Grafana dashboard

We will use Grafana, a popular open source tool for dashboards, to connect to your QuestDB instance and displaying near real time dashboards. We will use the grafana postgresql connector to connect to QuestDB.

## Starting grafana via docker

Even if you already have a working grafana installation, it is recommended to start a new one via docker, as the process
will provisioning sample connections and dashboards. If you prefer to provision a data source and a dashboard by hand,
skip this section and proceed to "Manual Provisioning"

Make sure you are at the `dashboard/grafana` directory before starting the grafana container. On starting, the contents
of the `./home_folder` will be used for provisioning sample dashboards, so it is important you start from the right
relative directory.

_Note: The following command uses the `env_variables` file to configure your grafana. It uses the default for a brand new
local installation of QuestDB. If you are not running QuestDB on the local host, you need to edit that file and change
host/port/user/password as needed. For users of QuestDB cloud you need to make sure you change the value of the
`QDB_SSL_PG_MODE` variable on that file from `disable` to `require`._

```shell
docker run -d -p 3000:3000 --name=grafana-quickstart --user "$(id -u)" --volume "$PWD/home_dir/var_lib_grafana:/var/lib/grafana" --volume "$PWD/home_dir/etc_grafana:/etc/grafana/"  --env-file ./env_variables grafana/grafana-oss
```

You can now navigate to [http://localhost:3000/d/qdb-ilp-demo/device-data-questdb-demo?orgId=1&refresh=5s](http://localhost:3000/d/qdb-ilp-demo/device-data-questdb-demo?orgId=1&refresh=5s)
using the user `demo` and password `quest` to see a live grafana dashboard. Assuming you are running the IoT example
provided for Python, Go, or JAVA, you should see the charts being updated every 5 seconds.


Feel free to explore Grafana. Both this sample dashboard and a datasource named `qdb` are automatically created.

When you want to stop your docker container you can run:

`docker stop grafana-quickstart`

And if you want to remove the docker container (and optionally the image) from your drive, execute:

```shell
docker rm grafana-quickstart
docker rmi grafana/grafana-oss
````

The rest of this README will explain how to manually provision your Grafana.

## Manual provisioning

### Creating the connection to QuestDB

In your grafana, find the data sources icon on the left menu and add a new one. Choose the PostgreSQL type.

You can enter any name you want, for example `qdb`, for host you need to enter
    * when running grafana locally (no docker) in the same machine where QuestDB is running: `localhost:8812`
    * when running grafana via docker, in the same machine where QuestDB is running: `host.docker.internal:8812`
    * when running a QuestDB Cloud instance: Please find the details for the `endpoint` at the "PostgreSQL Wire Protocol" section of your instance "Connect" tab.

For database choose `qdb`, user `admin`, password `quest`. Those are the default values for a fresh QuestDB installation.
If using QuestDB Cloud, refer to the "PostgreSQL Wire Protocol" section for the admin password.

Out of the box, QuestDB does not support TLS/SSL, so we need to select `disable` for TLS/SSL Mode, unless when using
the QuestDB cloud, in which case you need to select `require`.

Scroll down to the bottom of the screen and click on `Save & Test`. You should see the connection is working.

### Importing the dashboard

From here on, you could create your own dashboards and charts by following [this post](https://questdb.io/blog/time-series-monitoring-dashboard-grafana-questdb/).

However, if you prefer it, you can import the sample dashboard located at `/dashboard/grafana/home_dir/data/dashboards/DeviceData-QuestDBDemo.json`
in this repository. To import it, find the `dashboard>import` option on the left menu of your local grafana, and then
select the json file. The dashboard will try to use a connection named `qdb`.

