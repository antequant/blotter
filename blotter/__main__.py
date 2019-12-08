import asyncio
import logging
import random
import signal
from argparse import ArgumentParser

import google.cloud.logging
import ib_insync
from blotter.ib_helpers import IBThread
from blotter.server import Servicer

parser = ArgumentParser(
    prog="blotter",
    description="Microservice to connect to Interactive Brokers and stream market data into Google BigQuery",
    epilog="For more information, or to report issues, please visit: https://github.com/jspahrsummers/blotter",
)

parser.add_argument(
    "-v",
    "--verbose",
    help="Turns on more logging. Stack multiple times to increase logging even further.",
    action="count",
)

parser.add_argument(
    "-p",
    "--port",
    help="The port to listen for incoming connections on.",
    default=50051,
)

parser.add_argument(
    "--tws-host",
    help="The hostname upon which Trader Workstation or IB Gateway is listening for connections.",
    default="127.0.0.1",
)

parser.add_argument(
    "--tws-port",
    help="The port upon which Trader Workstation or IB Gateway is listening for connections.",
    default=7497,
)


def main() -> None:
    args = parser.parse_args()

    google.cloud.logging.Client().setup_logging(
        log_level=logging.DEBUG if args.verbose >= 2 else logging.INFO
    )

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG if args.verbose >= 2 else logging.INFO)

    ib = ib_insync.IB()

    print(f"Connecting to IB on {args.tws_host}:{args.tws_port}")
    ib.connect(
        host=args.tws_host,
        port=args.tws_port,
        clientId=random.randint(1, 2 ** 31 - 1),
        readonly=True,
    )

    # Install SIGINT handler. This is apparently necessary for the process to be interruptible with Ctrl-C on Windows:
    # https://bugs.python.org/issue23057
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    thread = IBThread(ib)

    port = args.port or random.randint(49152, 65535)
    s = Servicer.start(port, thread)
    print(f"Server listening on port {port}")

    thread.run_forever()


if __name__ == "__main__":
    main()
