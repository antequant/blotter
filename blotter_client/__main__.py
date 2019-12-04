import grpc
import signal
import logging
import sys
from blotter import blotter_pb2_grpc, blotter_pb2

from datetime import datetime

from argparse import ArgumentParser, Namespace
from typing import Any

_ContractSpecifier: Any = blotter_pb2.ContractSpecifier
_Duration: Any = blotter_pb2.Duration
_LoadHistoricalDataRequest: Any = blotter_pb2.LoadHistoricalDataRequest

parser = ArgumentParser(
    prog="blotter-client",
    description="Blotter command line client",
    epilog="For more information, or to report issues, please visit: https://github.com/jspahrsummers/blotter",
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

parser.add_argument(
    "--bar-size",
    help="Size of bars to fetch",
    choices=_LoadHistoricalDataRequest.BarSize.keys(),
    default="ONE_MINUTE",
)

parser.add_argument(
    "--bar-source",
    help="Which quotes or data to fetch per bar",
    choices=_LoadHistoricalDataRequest.BarSource.keys(),
    default="MIDPOINT",
)

parser.add_argument(
    "--currency",
    help="The currency of the security being loaded (sometimes necessary to disambiguate contracts)",
    default="USD",
)

subparsers = parser.add_subparsers(dest="command", help="What to do")

backfill_parser = subparsers.add_parser("backfill", help="Backfill securities data")

duration_group = backfill_parser.add_mutually_exclusive_group()
duration_group.add_argument(
    "--days", type=int, help="Number of days to backfill data for", default=10
)


def contract_specifier_from_args(args: Namespace) -> _ContractSpecifier:
    type_mapping = {
        "stock": _ContractSpecifier.SecurityType.STOCK,
    }

    for key, sec_type in type_mapping.items():
        if hasattr(args, key):
            return _ContractSpecifier(
                symbol=getattr(args, key),
                securityType=sec_type,
                exchange="SMART",
                currency=args.currency,
            )

    raise RuntimeError(f"Security not specified")


def duration_from_args(args: Namespace) -> _Duration:
    duration_mapping = {
        "days": _Duration.TimeUnit.DAYS,
    }

    for key, unit in duration_mapping.items():
        if hasattr(args, key):
            return _Duration(count=getattr(args, key), unit=unit)

    raise RuntimeError(f"Duration not specified")


def backfill(stub: blotter_pb2_grpc.BlotterStub, args: Namespace) -> None:
    request = _LoadHistoricalDataRequest(
        contractSpecifier=contract_specifier_from_args(args),
        # TODO: Make this a command-line arg too
        endTimestampUTC=int(datetime.utcnow().timestamp()),
        duration=duration_from_args(args),
        barSize=_LoadHistoricalDataRequest.BarSize.Value(args.bar_size),
        barSource=_LoadHistoricalDataRequest.BarSource.Value(args.bar_source),
    )

    logging.info(f"LoadHistoricalData: {request}")
    stub.LoadHistoricalData(request)


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

    commands = {"backfill": backfill}
    commands[args.command](stub, args)


if __name__ == "__main__":
    main()
