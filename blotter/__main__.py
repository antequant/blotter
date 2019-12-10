import asyncio
import logging
import random
import signal
from argparse import ArgumentParser

import google.cloud.logging
import ib_insync
from blotter.ib_helpers import IBError, IBThread, IBWarning
from blotter.server import Servicer
from google.cloud import error_reporting

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

parser.add_argument(
    "--streaming-batch-size",
    help="The size of batches to create when streaming, before uploading to BigQuery.",
    type=int,
)


def error_handler(error: Exception) -> None:
    try:
        raise error
    except IBWarning:
        logging.warning(f"Warning from IB: {error}")
    except Exception:
        logging.exception(f"Reporting error from IB:")
        error_reporting.Client().report_exception()


def main() -> None:
    args = parser.parse_args()

    google.cloud.logging.Client().setup_logging(
        log_level=logging.DEBUG if args.verbose >= 2 else logging.INFO
    )

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG if args.verbose >= 2 else logging.INFO)

    ib = ib_insync.IB()

    logging.info(f"Connecting to IB on {args.tws_host}:{args.tws_port}")
    ib.connect(
        host=args.tws_host,
        port=args.tws_port,
        clientId=random.randint(1, 2 ** 31 - 1),
        readonly=True,
    )

    # Install SIGINT handler. This is apparently necessary for the process to be interruptible with Ctrl-C on Windows:
    # https://bugs.python.org/issue23057
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    thread = IBThread(ib, error_handler=error_handler)

    port = args.port or random.randint(49152, 65535)
    s = (
        Servicer.start(port, thread, streaming_batch_size=args.streaming_batch_size)
        if args.streaming_batch_size
        else Servicer.start(port, thread)
    )

    logging.info(f"Server listening on port {port}")
    thread.run_forever()


if __name__ == "__main__":
    main()
