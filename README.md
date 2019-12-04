# blotter
Microservice to connect to Interactive Brokers and stream market data into Google BigQuery

## Building

```sh
docker build . -t blotter
```

## Running

```sh
docker run -p 50051:50051 --detach --rm blotter:latest -v --tws-port 4002
```

## Client

```sh
python -m blotter_client --help
python -m blotter_client -b localhost:50051 -v --stock MSFT backfill
```