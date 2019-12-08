import asyncio
import concurrent.futures
import logging
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Iterator, Optional, Tuple, TypeVar

import grpc
import ib_insync
from blotter import blotter_pb2, blotter_pb2_grpc, request_helpers
from blotter.backfill import backfill_bars
from blotter.ib_helpers import IBThread
from blotter.streaming import StreamingID, StreamingManager
from google.cloud import bigquery, error_reporting

_T = TypeVar("_T")


class Servicer(blotter_pb2_grpc.BlotterServicer):
    """
    The implementation of the Blotter RPC service, responsible for handling client requests to start/stop blotting different instruments.
    """

    @classmethod
    def start(
        cls,
        port: int,
        ib_thread: IBThread,
        executor: concurrent.futures.ThreadPoolExecutor = concurrent.futures.ThreadPoolExecutor(),
    ) -> grpc.Server:
        """
        Instantiates a server, binds it to the given port and begins accepting requests on `executor`.
        """

        s = grpc.server(executor)
        blotter_pb2_grpc.add_BlotterServicer_to_server(cls(ib_thread), s)
        s.add_insecure_port(f"[::]:{port}")
        s.start()

        return s

    def __init__(self, ib_thread: IBThread):
        """
        Initializes this handler to invoke ib_insync via the given `ib_thread`.
        """

        self._ib_thread = ib_thread
        self._streaming_manager = StreamingManager()
        super().__init__()

    def resume_streaming(self) -> None:
        streaming_ids = list(self._streaming_manager.resume_streaming(self._ib_thread))
        logging.info(f"Resumed streaming IDs {streaming_ids}")

    def _run_in_ib_thread(
        self, fn: Callable[[ib_insync.IB], Awaitable[_T]]
    ) -> "concurrent.futures.Future[_T]":
        """
        Schedules work on the `IBThread` for this service, reporting any exceptions that occur.
        """

        fut = self._ib_thread.schedule(fn)

        def _report_future_exception(future: "concurrent.futures.Future[_T]") -> None:
            try:
                future.result()
            except Exception:
                logging.exception(f"Exception thrown in IB thread:")
                error_reporting.Client().report_exception()

        fut.add_done_callback(_report_future_exception)
        return fut

    def LoadHistoricalData(
        self,
        request: blotter_pb2.LoadHistoricalDataRequest,
        context: grpc.ServicerContext,
    ) -> Iterator[blotter_pb2.LoadHistoricalDataResponse]:
        logging.info(f"LoadHistoricalData: {request}")

        td = request_helpers.duration_timedelta_atleast(request.duration)
        end_date = datetime.fromtimestamp(request.endTimestampUTC, tz=timezone.utc)

        if td.days <= 10:
            duration = request_helpers.duration_str(request.duration)
            start_date = end_date - timedelta(seconds=1)
        else:
            logging.debug(f"Splitting requested duration {td}")
            duration = request_helpers.duration_str(
                blotter_pb2.Duration(count=10, unit=blotter_pb2.Duration.TimeUnit.DAYS)
            )

            start_date = end_date - td

        async def _backfill(
            ib_client: ib_insync.IB,
        ) -> Tuple[datetime, bigquery.LoadJob]:
            nonlocal end_date

            logging.info(
                f"Backfilling {duration} from {end_date} of {request.contractSpecifier}"
            )

            return await backfill_bars(
                ib_client,
                contract_specifier=request.contractSpecifier,
                end_date=end_date,
                duration=duration,
                bar_size=request_helpers.bar_size_str(request.barSize),
                bar_source=request_helpers.historical_bar_source_str(request.barSource),
                regular_trading_hours_only=request.regularTradingHoursOnly,
            )

        while end_date > start_date:
            (end_date, job) = self._run_in_ib_thread(_backfill).result()

            logging.info(f"BigQuery backfill job launched: {job.job_id}")
            yield blotter_pb2.LoadHistoricalDataResponse(backfillJobID=job.job_id)

    def StartRealTimeData(
        self,
        request: blotter_pb2.StartRealTimeDataRequest,
        context: grpc.ServicerContext,
    ) -> blotter_pb2.StartRealTimeDataResponse:
        logging.info(f"StartRealTimeData: {request}")

        async def _start_stream(ib_client: ib_insync.IB) -> StreamingID:
            return await self._streaming_manager.start_stream(
                ib_client,
                contract_specifier=request.contractSpecifier,
                bar_source=request_helpers.real_time_bar_source_str(request.barSource),
                regular_trading_hours_only=request.regularTradingHoursOnly,
            )

        streaming_id = self._run_in_ib_thread(_start_stream).result()
        logging.debug(f"Real-time bars streaming ID: {streaming_id}")

        return blotter_pb2.StartRealTimeDataResponse(requestID=streaming_id)

    def CancelRealTimeData(
        self,
        request: blotter_pb2.CancelRealTimeDataRequest,
        context: grpc.ServicerContext,
    ) -> blotter_pb2.CancelRealTimeDataResponse:
        logging.info(f"CancelRealTimeData: {request}")

        async def _cancel_stream(ib_client: ib_insync.IB) -> None:
            await self._streaming_manager.cancel_stream(
                ib_client, streaming_id=StreamingID(request.requestID)
            )

        self._run_in_ib_thread(_cancel_stream)
        return blotter_pb2.CancelRealTimeDataResponse()

    def HealthCheck(
        self, request: blotter_pb2.HealthCheckRequest, context: grpc.ServicerContext,
    ) -> blotter_pb2.HealthCheckResponse:
        logging.info(f"HealthCheck: {request}")
        return blotter_pb2.HealthCheckResponse()

