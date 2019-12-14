import logging
from types import TracebackType
from typing import Any, Callable, ContextManager, Optional, Type

import google.cloud.error_reporting


class ErrorHandler(ContextManager["ErrorHandler"]):
    """
    Context manager that implements error handling behavior for the blotter service.
    """

    def __init__(self, report_to_gcloud: bool, fmt: str, *args: Any, **kwargs: Any):
        """
        Initializes an error handler which will optionally report to Google Cloud, and will log any exception using the given format string and arguments.
        """

        self._report_to_gcloud = report_to_gcloud
        self._fmt = fmt
        self._args = args
        self._kwargs = kwargs
        super().__init__()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> bool:
        logging.exception(self._fmt, *self._args, **self._kwargs)

        if self._report_to_gcloud:
            google.cloud.error_reporting.Client().report_exception()

        return True


class ErrorHandlerConfiguration:
    """
    Provides a convenient interface to build `ErrorHandler`s with partially-preset configuration.
    """

    def __init__(self, report_to_gcloud: bool):
        self._report_to_gcloud = report_to_gcloud
        super().__init__()

    def __call__(self, fmt: str, *args: Any, **kwargs: Any) -> ErrorHandler:
        return ErrorHandler(self._report_to_gcloud, fmt, *args, **kwargs)
