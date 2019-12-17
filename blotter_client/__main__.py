import logging
import signal
import sys
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
from datetime import datetime

import grpc

from blotter import blotter_pb2, blotter_pb2_grpc

parser = ArgumentParser(
    prog="blotter-client",
    description="Blotter command line client",
    epilog="For more information, or to report issues, please visit: https://github.com/jspahrsummers/blotter",
    formatter_class=ArgumentDefaultsHelpFormatter,
)

parser.add_argument(
    "-v",
    "--verbose",
    help="Turns on more logging. Stack multiple times to increase logging even further.",
    action="count",
)

parser.add_argument(
    "-b",
    "--blotter-address",
    help="The hostname and port to connect to Blotter on.",
    default="localhost:50051",
)

securities_group = parser.add_mutually_exclusive_group()
securities_group.add_argument("--stock", help="Load data for the given stock ticker.")

securities_group.add_argument("--index", help="Load data for the given index.")

securities_group.add_argument(
    "--future", help="Load data for the given futures contract."
)

securities_group.add_argument(
    "--forex",
    help="Load data for the given currency, quoted in the base currency specified by --currency",
)

parser.add_argument(
    "--exchange",
    help="The exchange of the security being loaded (sometimes necessary to disambiguate contracts). Examples: SMART, IDEALPRO, GLOBEX, CBOE",
)

parser.add_argument(
    "--currency",
    help="The currency of the security being loaded (sometimes necessary to disambiguate contracts)",
    default="USD",
)

parser.add_argument(
    "--contract-month",
    "--last-trade-date",
    help="Date in YYYYMM or YYYYMMDD format, specifying the contract month or last trade date of the instrument",
)

subparsers = parser.add_subparsers(dest="command", help="What to do")

ping_parser = subparsers.add_parser(
    "ping",
    help="Check that the server is online",
    formatter_class=ArgumentDefaultsHelpFormatter,
)

backfill_parser = subparsers.add_parser(
    "backfill",
    help="Backfill securities data",
    formatter_class=ArgumentDefaultsHelpFormatter,
)

backfill_parser.add_argument(
    "--bar-size",
    help="Size of bars to fetch",
    choices=blotter_pb2.LoadHistoricalDataRequest.BarSize.keys(),
    default="ONE_MINUTE",
)

backfill_parser.add_argument(
    "--bar-source",
    help="Which quotes or data to fetch per bar",
    choices=blotter_pb2.LoadHistoricalDataRequest.BarSource.keys(),
    default="TRADES",
)

backfill_parser.add_argument(
    "--until",
    type=int,
    help="Backfill up until this POSIX UTC timestamp",
    default=int(datetime.utcnow().timestamp()),
)

duration_group = backfill_parser.add_mutually_exclusive_group(required=True)

duration_group.add_argument(
    "--seconds", type=int, help="Number of seconds to backfill data for"
)

duration_group.add_argument(
    "--days", type=int, help="Number of days to backfill data for"
)

duration_group.add_argument(
    "--weeks", type=int, help="Number of weeks to backfill data for",
)

duration_group.add_argument(
    "--months", type=int, help="Number of months to backfill data for",
)

duration_group.add_argument(
    "--years", type=int, help="Number of years to backfill data for",
)

start_parser = subparsers.add_parser(
    "start",
    help="Start streaming securities data",
    formatter_class=ArgumentDefaultsHelpFormatter,
)

start_parser.add_argument(
    "--bar-source",
    help="Which quotes or data to fetch per bar",
    choices=blotter_pb2.StartRealTimeDataRequest.BarSource.keys(),
    default="TRADES",
)

stop_parser = subparsers.add_parser(
    "stop",
    help="Stop streaming securities data",
    formatter_class=ArgumentDefaultsHelpFormatter,
)

stop_parser.add_argument("request_id", help="The streaming request to cancel")

options_parser = subparsers.add_parser(
    'options',
    help="Options-specific blotting commands",
    formatter_class=ArgumentDefaultsHelpFormatter,
)

options_subparsers = options_parser.add_subparsers(dest="options_command", help="What to do")

snapshot_options_parser = options_subparsers.add_parser(
    "snapshot",
    help="Snapshot the options chain for the given stock or future",
    formatter_class=ArgumentDefaultsHelpFormatter,
)

start_streaming_options_parser = options_subparsers.add_parser(
    'start',
    help="Start streaming options data",
    formatter_class=ArgumentDefaultsHelpFormatter,
)

stop_streaming_options_parser = options_subparsers.add_parser(
    'stop',
    help="Stop streaming options data",
    formatter_class=ArgumentDefaultsHelpFormatter,
)

stop_streaming_options_parser.add_argument("request_id", help="The streaming request to cancel")

def contract_specifier_from_args(args: Namespace) -> blotter_pb2.ContractSpecifier:
    type_mapping = {
        "stock": blotter_pb2.ContractSpecifier.SecurityType.STOCK,
        "future": blotter_pb2.ContractSpecifier.SecurityType.FUTURE,
        "forex": blotter_pb2.ContractSpecifier.SecurityType.CASH,
        "index": blotter_pb2.ContractSpecifier.SecurityType.INDEX,
    }

    specifier = blotter_pb2.ContractSpecifier(
        exchange=args.exchange, currency=args.currency
    )

    if args.contract_month:
        specifier.lastTradeDateOrContractMonth = args.contract_month

    for key, sec_type in type_mapping.items():
        if getattr(args, key):
            specifier.symbol = getattr(args, key)
            specifier.securityType = sec_type
            return specifier

    parser.error(f"No security type specified")


def duration_from_args(args: Namespace) -> blotter_pb2.Duration:
    duration_mapping = {
        "seconds": blotter_pb2.Duration.TimeUnit.SECONDS,
        "days": blotter_pb2.Duration.TimeUnit.DAYS,
        "weeks": blotter_pb2.Duration.TimeUnit.WEEKS,
        "months": blotter_pb2.Duration.TimeUnit.MONTHS,
        "years": blotter_pb2.Duration.TimeUnit.YEARS,
    }

    for key, unit in duration_mapping.items():
        if getattr(args, key):
            return blotter_pb2.Duration(count=getattr(args, key), unit=unit)

    parser.error(f"No backfill duration specified")


def backfill(stub: blotter_pb2_grpc.BlotterStub, args: Namespace) -> None:
    request = blotter_pb2.LoadHistoricalDataRequest(
        contractSpecifier=contract_specifier_from_args(args),
        endTimestampUTC=args.until,
        duration=duration_from_args(args),
        barSize=blotter_pb2.LoadHistoricalDataRequest.BarSize.Value(args.bar_size),
        barSource=blotter_pb2.LoadHistoricalDataRequest.BarSource.Value(
            args.bar_source
        ),
    )

    logging.info(f"LoadHistoricalData: {request}")

    for response in stub.LoadHistoricalData(request):
        logging.info(f"Backfill started with job ID: {response.backfillJobID}")


def start_streaming(stub: blotter_pb2_grpc.BlotterStub, args: Namespace) -> None:
    request = blotter_pb2.StartRealTimeDataRequest(
        contractSpecifier=contract_specifier_from_args(args),
        barSource=blotter_pb2.StartRealTimeDataRequest.BarSource.Value(args.bar_source),
    )

    logging.info(f"StartRealTimeData: {request}")

    response = stub.StartRealTimeData(request)
    print(f"Streaming started with request ID: {response.requestID}")


def stop_streaming(stub: blotter_pb2_grpc.BlotterStub, args: Namespace) -> None:
    request = blotter_pb2.CancelRealTimeDataRequest(requestID=args.request_id)

    logging.info(f"CancelRealTimeData: {request}")
    stub.CancelRealTimeData(request)


def ping(stub: blotter_pb2_grpc.BlotterStub, args: Namespace) -> None:
    request = blotter_pb2.HealthCheckRequest()
    logging.info(f"HealthCheck: {request}")

    stub.HealthCheck(request)
    print("Ping!")


def snapshot_options(stub: blotter_pb2_grpc.BlotterStub, args: Namespace) -> None:
    request = blotter_pb2.SnapshotOptionChainRequest(
        contractSpecifier=contract_specifier_from_args(args)
    )
    logging.info(f"SnapshotOptionChain: {request}")

    response = stub.SnapshotOptionChain(request)
    logging.info(f"Importing option chain with job ID: {response.importJobID}")

def start_options_streaming(stub: blotter_pb2_grpc.BlotterStub, args: Namespace) -> None:
    request = blotter_pb2.StartStreamingOptionChainRequest(
        contractSpecifier=contract_specifier_from_args(args),
    )

    logging.info(f"StartStreamingOptionChain: {request}")

    response = stub.StartStreamingOptionChain(request)
    print(f"Streaming started with request ID: {response.requestID}")


def stop_options_streaming(stub: blotter_pb2_grpc.BlotterStub, args: Namespace) -> None:
    request = blotter_pb2.CancelStreamingOptionChainRequest(requestID=args.request_id)

    logging.info(f"CancelStreamingOptionChain: {request}")
    stub.CancelStreamingOptionChain(request)


def handle_options_command(stub: blotter_pb2_grpc.BlotterStub, args: Namespace) -> None:
    commands = {
        "snapshot": snapshot_options,
        "start": start_options_streaming,
        "stop": stop_options_streaming,
    }

    commands[args.options_command](stub, args)

def main() -> None:
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG if args.verbose >= 2 else logging.INFO)

    if not args.command:
        parser.error("No command provided")

    # Install SIGINT handler. This is apparently necessary for the process to be interruptible with Ctrl-C on Windows:
    # https://bugs.python.org/issue23057
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    address = args.blotter_address
    logging.info(f"Connecting to {address}")

    channel = grpc.insecure_channel(address)
    stub = blotter_pb2_grpc.BlotterStub(channel)

    commands = {
        "backfill": backfill,
        "start": start_streaming,
        "stop": stop_streaming,
        "ping": ping,
        "options": handle_options_command,
    }

    commands[args.command](stub, args)


if __name__ == "__main__":
    main()
