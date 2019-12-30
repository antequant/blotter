import asyncio
import random
import signal
import sys
from argparse import ArgumentParser
from datetime import timedelta
from logging import getLogger
from types import TracebackType
from typing import Type

import ib_insync
from blotter.error_handling import ErrorHandlerConfiguration
from blotter.ib_helpers import IBError, IBThread, IBWarning
from blotter.server import Servicer
from blotter.streaming import StreamingManager
from gcloud_service.logging import configure_package_logger, configure_root_logger

logger = getLogger(__package__)

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
    "--report-errors", help="Report errors to Google Cloud.", action="store_true",
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
    "--resume",
    help="Automatically resume streaming operations from previous runs, if they were not explicitly cancelled.",
    action="store_true",
)

parser.add_argument(
    "--streaming-batch-size",
    help="The size of batches to create when streaming, before uploading to BigQuery.",
    default=StreamingManager.DEFAULT_BATCH_SIZE,
)

parser.add_argument(
    "--streaming-batch-timeout",
    help="The maximum duration (in seconds) to wait when batching data from streaming, before uploading to BigQuery.",
    type=lambda s: timedelta(seconds=float(s)),
    default=StreamingManager.DEFAULT_BATCH_LATENCY,
)


def install_except_hook(error_handler: ErrorHandlerConfiguration) -> None:
    mgr = error_handler(f"Uncaught exception:")
    mgr.__enter__()

    def _hook(
        type_: Type[BaseException], value: BaseException, traceback: TracebackType,
    ) -> None:
        mgr.__exit__(type_, value, traceback)

    sys.excepthook = _hook


def main() -> None:
    args = parser.parse_args()

    error_handler = ErrorHandlerConfiguration(report_to_gcloud=args.report_errors)
    configure_root_logger(args.verbose)
    configure_package_logger(logger, args.verbose)

    ib = ib_insync.IB()

    logger.info(f"Connecting to IB on {args.tws_host}:{args.tws_port}")
    ib.connect(
        host=args.tws_host,
        port=args.tws_port,
        clientId=random.randint(1, 2 ** 31 - 1),
        readonly=True,
    )

    # Install SIGINT handler. This is apparently necessary for the process to be interruptible with Ctrl-C on Windows:
    # https://bugs.python.org/issue23057
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    def handle_ib_thread_error(error: Exception) -> None:
        with error_handler(f"Reporting error from IB:"):
            try:
                raise error
            except IBWarning:
                logger.warning(f"Warning from IB: {error}")
            except ConnectionError:
                logger.exception(f"Connection error from IB:")

    thread = IBThread(ib, error_handler=handle_ib_thread_error)
    port = args.port or random.randint(49152, 65535)
    streaming_manager = StreamingManager(
        error_handler=error_handler,
        batch_size=args.streaming_batch_size,
        batch_timeout=args.streaming_batch_timeout,
    )

    (servicer, server) = Servicer.start(port, thread, streaming_manager, error_handler)
    if args.resume:
        servicer.resume_streaming()

    logger.info(f"Server listening on port {port}")
    thread.run_forever()


if __name__ == "__main__":
    main()
