import asyncio
import concurrent.futures
from datetime import datetime, timedelta, timezone
from logging import getLogger
from typing import Awaitable, Callable, Iterator, Optional, Tuple, TypeVar

import grpc
from google.cloud import bigquery

import ib_insync
from blotter import blotter_pb2, blotter_pb2_grpc, request_helpers
from blotter.backfill import backfill_bars
from gcloud_service.error_handler import ErrorHandlerConfiguration
from blotter.ib_helpers import IBThread, qualify_contract_specifier
from blotter.options import snapshot_options, start_polling_options
from blotter.polling import PollingID, PollingManager
from blotter.streaming import StreamingID, StreamingManager

logger = getLogger(__name__)

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
        streaming_manager: StreamingManager,
        error_handler: ErrorHandlerConfiguration,
        executor: concurrent.futures.ThreadPoolExecutor = concurrent.futures.ThreadPoolExecutor(),
    ) -> Tuple["Servicer", grpc.Server]:
        """
        Instantiates a server, binds it to the given port and begins accepting requests on `executor`.
        """

        s = grpc.server(executor)
        servicer = cls(ib_thread, streaming_manager, error_handler)
        blotter_pb2_grpc.add_BlotterServicer_to_server(servicer, s)
        s.add_insecure_port(f"[::]:{port}")
        s.start()

        return (servicer, s)

    def __init__(
        self,
        ib_thread: IBThread,
        streaming_manager: StreamingManager,
        error_handler: ErrorHandlerConfiguration,
    ):
        """
        Initializes this handler to invoke ib_insync via the given `ib_thread`.
        """

        self._ib_thread = ib_thread
        self._streaming_manager = streaming_manager
        self._polling_manager = PollingManager(error_handler)
        self._error_handler = error_handler
        super().__init__()

    def resume_streaming(self) -> None:
        """
        Resumes any streaming market data queries that were interrupted on previous runs.
        """

        streaming_ids = list(self._streaming_manager.resume_streaming(self._ib_thread))
        logger.info(f"Resumed streaming IDs {streaming_ids}")

        # TODO: Resume things on PollingManager too

    def _run_in_ib_thread(
        self, fn: Callable[[ib_insync.IB], Awaitable[_T]]
    ) -> "concurrent.futures.Future[_T]":
        """
        Schedules work on the `IBThread` for this service, reporting any exceptions that occur.
        """

        fut = self._ib_thread.schedule_async(fn)

        def _report_future_exception(future: "concurrent.futures.Future[_T]") -> None:
            with self._error_handler(f"Exception thrown in IB thread:"):
                future.result()

        fut.add_done_callback(_report_future_exception)
        return fut

    def LoadHistoricalData(
        self,
        request: blotter_pb2.LoadHistoricalDataRequest,
        context: grpc.ServicerContext,
    ) -> Iterator[blotter_pb2.LoadHistoricalDataResponse]:
        logger.info(f"LoadHistoricalData: {request}")

        td = request_helpers.duration_timedelta_atleast(request.duration)
        end_date = datetime.fromtimestamp(request.endTimestampUTC, tz=timezone.utc)

        if td.days <= 10:
            duration = request_helpers.duration_str(request.duration)
            start_date = end_date - timedelta(seconds=1)
        else:
            logger.debug(f"Splitting requested duration {td}")
            duration = request_helpers.duration_str(
                blotter_pb2.Duration(count=10, unit=blotter_pb2.Duration.TimeUnit.DAYS)
            )

            start_date = end_date - td

        async def _backfill(
            ib_client: ib_insync.IB,
        ) -> Tuple[datetime, bigquery.LoadJob]:
            nonlocal end_date

            logger.info(
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
                error_handler=self._error_handler,
            )

        while end_date > start_date:
            (end_date, job) = self._run_in_ib_thread(_backfill).result()

            logger.info(f"BigQuery backfill job launched: {job.job_id}")
            yield blotter_pb2.LoadHistoricalDataResponse(backfillJobID=job.job_id)

    def StartRealTimeData(
        self,
        request: blotter_pb2.StartRealTimeDataRequest,
        context: grpc.ServicerContext,
    ) -> blotter_pb2.StartRealTimeDataResponse:
        logger.info(f"StartRealTimeData: {request}")

        async def _start_stream(ib_client: ib_insync.IB) -> StreamingID:
            return await self._streaming_manager.start_stream(
                ib_client,
                contract=request.contractSpecifier,
                bar_source=request_helpers.real_time_bar_source_str(request.barSource),
                regular_trading_hours_only=request.regularTradingHoursOnly,
            )

        streaming_id = self._run_in_ib_thread(_start_stream).result()
        logger.debug(f"Real-time bars streaming ID: {streaming_id}")

        return blotter_pb2.StartRealTimeDataResponse(requestID=streaming_id)

    def CancelRealTimeData(
        self,
        request: blotter_pb2.CancelRealTimeDataRequest,
        context: grpc.ServicerContext,
    ) -> blotter_pb2.CancelRealTimeDataResponse:
        logger.info(f"CancelRealTimeData: {request}")

        async def _cancel_stream(ib_client: ib_insync.IB) -> None:
            await self._streaming_manager.cancel_stream(
                ib_client, streaming_id=StreamingID(request.requestID)
            )

        self._run_in_ib_thread(_cancel_stream)
        return blotter_pb2.CancelRealTimeDataResponse()

    def HealthCheck(
        self, request: blotter_pb2.HealthCheckRequest, context: grpc.ServicerContext,
    ) -> blotter_pb2.HealthCheckResponse:
        logger.info(f"HealthCheck: {request}")
        return blotter_pb2.HealthCheckResponse()

    def SnapshotOptionChain(
        self,
        request: blotter_pb2.SnapshotOptionChainRequest,
        context: grpc.ServicerContext,
    ) -> blotter_pb2.SnapshotOptionChainResponse:
        logger.info(f"SnapshotOptionChain: {request}")

        async def _snapshot(ib_client: ib_insync.IB) -> bigquery.LoadJob:
            return await snapshot_options(
                ib_client, request.contractSpecifier, self._error_handler
            )

        job = self._run_in_ib_thread(_snapshot).result()
        logger.info(f"BigQuery import job launched: {job.job_id}")

        return blotter_pb2.SnapshotOptionChainResponse(importJobID=job.job_id)

    def StartStreamingOptionChain(
        self,
        request: blotter_pb2.StartStreamingOptionChainRequest,
        context: grpc.ServicerContext,
    ) -> blotter_pb2.StartStreamingOptionChainResponse:
        logger.info(f"StartStreamingOptionChain: {request}")

        async def _start_polling(ib_client: ib_insync.IB) -> PollingID:
            polling_interval = PollingManager.DEFAULT_POLLING_INTERVAL
            if request.pollingInterval:
                polling_interval = timedelta(seconds=request.pollingInterval)

            return await start_polling_options(
                self._polling_manager,
                polling_interval,
                ib_client,
                request.contractSpecifier,
            )

        polling_id = self._run_in_ib_thread(_start_polling).result()
        logger.debug(f"Real-time bars streaming ID: {polling_id}")

        return blotter_pb2.StartStreamingOptionChainResponse(requestID=polling_id)

    def CancelStreamingOptionChain(
        self,
        request: blotter_pb2.CancelStreamingOptionChainRequest,
        context: grpc.ServicerContext,
    ) -> blotter_pb2.CancelStreamingOptionChainResponse:
        logger.info(f"CancelStreamingOptionChain: {request}")

        async def _cancel_polling(ib_client: ib_insync.IB) -> None:
            await self._polling_manager.cancel_polling(
                ib_client, polling_id=PollingID(request.requestID)
            )

        self._run_in_ib_thread(_cancel_polling)
        return blotter_pb2.CancelStreamingOptionChainResponse()
