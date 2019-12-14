import logging
import google.cloud.logging


def install_gcloud_logging_handler(logger: logging.Logger, level: int) -> None:
    handler = google.cloud.logging.handlers.CloudLoggingHandler(
        google.cloud.logging.Client()
    )

    handler.setLevel(level)
    logger.addHandler(handler)


def install_console_logging_handler(logger: logging.Logger) -> None:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s [%(name)s][%(levelname)s] %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)


def configure_root_logger(verbosity: int) -> None:
    logger = logging.getLogger()

    if verbosity >= 3:
        logger.setLevel(logging.DEBUG)
    elif verbosity >= 2:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARN)

    install_console_logging_handler(logger)
    install_gcloud_logging_handler(logger, logging.WARN)


def configure_package_logger(logger: logging.Logger, verbosity: int) -> None:
    if verbosity >= 2:
        logger.setLevel(logging.DEBUG)
    elif verbosity >= 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARN)

    install_console_logging_handler(logger)
    install_gcloud_logging_handler(logger, logging.INFO)
    logger.propagate = False
