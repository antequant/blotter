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
securities_group.add_argument(
    "--future", help="Load data for the given futures contract."
)

parser.add_argument(
    "--exchange",
    help="The exchange of the security being loaded (sometimes necessary to disambiguate contracts)",
    default="SMART",
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

backfill_parser = subparsers.add_parser("backfill", help="Backfill securities data")

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

duration_group = backfill_parser.add_mutually_exclusive_group()
duration_group.add_argument(
    "--days", type=int, help="Number of days to backfill data for", default=10
)

start_parser = subparsers.add_parser("start", help="Start streaming securities data")
start_parser.add_argument(
    "--bar-source",
    help="Which quotes or data to fetch per bar",
    choices=blotter_pb2.StartRealTimeDataRequest.BarSource.keys(),
    default="TRADES",
)

stop_parser = subparsers.add_parser("stop", help="Stop streaming securities data")
stop_parser.add_argument("request_id", help="The streaming request to cancel")


def contract_specifier_from_args(args: Namespace) -> blotter_pb2.ContractSpecifier:
    type_mapping = {
        "stock": blotter_pb2.ContractSpecifier.SecurityType.STOCK,
        "future": blotter_pb2.ContractSpecifier.SecurityType.FUTURE,
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

    raise RuntimeError(f"Security not specified")


def duration_from_args(args: Namespace) -> blotter_pb2.Duration:
    duration_mapping = {
        "days": blotter_pb2.Duration.TimeUnit.DAYS,
    }

    for key, unit in duration_mapping.items():
        if hasattr(args, key):
            return blotter_pb2.Duration(count=getattr(args, key), unit=unit)

    raise RuntimeError(f"Duration not specified")


def backfill(stub: blotter_pb2_grpc.BlotterStub, args: Namespace) -> None:
    request = blotter_pb2.LoadHistoricalDataRequest(
        contractSpecifier=contract_specifier_from_args(args),
        # TODO: Make this a command-line arg too
        endTimestampUTC=int(datetime.utcnow().timestamp()),
        duration=duration_from_args(args),
        barSize=blotter_pb2.LoadHistoricalDataRequest.BarSize.Value(args.bar_size),
        barSource=blotter_pb2.LoadHistoricalDataRequest.BarSource.Value(
            args.bar_source
        ),
    )

    logging.info(f"LoadHistoricalData: {request}")

    response = stub.LoadHistoricalData(request)
    print(f"Backfill started with job ID: {response.backfillJobID}")


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


def main() -> None:
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG if args.verbose >= 2 else logging.INFO)

    if not args.command:
        logging.error("No command provided")
        parser.print_usage()
        sys.exit(1)

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
    }

    commands[args.command](stub, args)


if __name__ == "__main__":
    main()
