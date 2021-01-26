# blotter
Microservice to connect to Interactive Brokers and stream market data into Google BigQuery

See the [antequant Python project conventions](https://github.com/antequant/conventions/wiki/Python) for how to clone and set up this repository for development.

## Building

```sh
docker build . -t blotter
```

## Running

```sh
docker run -p 50051:50051 blotter -v --tws-port 4002
```

## Client

```sh
python -m blotter_client --help
python -m blotter_client -b localhost:50051 -v --stock MSFT --exchange SMART backfill
```
