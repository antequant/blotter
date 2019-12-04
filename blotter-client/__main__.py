import grpc
import signal
import logging
from blotter import blotter_pb2_grpc
from blotter.blotter_pb2 import *

from datetime import datetime

from argparse import ArgumentParser

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

parser.add_argument("address", help="The hostname and port to connect to blotter on.")


def main():
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG if args.verbose >= 2 else logging.INFO)

    # Install SIGINT handler. This is apparently necessary for the process to be interruptible with Ctrl-C on Windows:
    # https://bugs.python.org/issue23057
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    address = args.address
    logging.info(f"Connecting to {address}")

    channel = grpc.insecure_channel(address)
    stub = blotter_pb2_grpc.BlotterStub(channel)

    request = LoadHistoricalDataRequest(
        contractSpecifier=ContractSpecifier(
            symbol="MSFT",
            securityType=ContractSpecifier.STOCK,
            currency="USD",
            exchange="SMART",
        ),
        endTimestampUTC=int(datetime.utcnow().timestamp()),
        duration=Duration(count=10, unit=Duration.DAYS),
        barSize=LoadHistoricalDataRequest.ONE_MINUTE,
        barSource=LoadHistoricalDataRequest.MIDPOINT,
    )

    logging.debug(f"LoadHistoricalData: {request}")
    stub.LoadHistoricalData(request)


if __name__ == "__main__":
    main()
