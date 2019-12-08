import asyncio
import concurrent.futures
import logging
from datetime import datetime
from enum import Enum, unique
from typing import Awaitable, Callable, Dict, Optional, TypeVar

import grpc
import ib_insync
import pandas as pd
from blotter import blotter_pb2, blotter_pb2_grpc, request_helpers
from blotter.ib_helpers import IBThread
from google.cloud import bigquery, error_reporting


@unique
class _TableColumn(Enum):
    TIMESTAMP = "timestamp"
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"
    AVERAGE_PRICE = "average"
    BAR_COUNT = "bar_count"
    BAR_SOURCE = "bar_source"


def _upload_dataframe(table_id: str, df: pd.DataFrame) -> bigquery.job.LoadJob:
    client = bigquery.Client()
    dataset_id = "blotter"

    dataset_ref = client.dataset(dataset_id)
    table_ref = dataset_ref.table(table_id)
    config = bigquery.job.LoadJobConfig(
        time_partitioning=bigquery.table.TimePartitioning(
            field=_TableColumn.TIMESTAMP.value
        ),
        schema_update_options=bigquery.job.SchemaUpdateOption.ALLOW_FIELD_ADDITION,
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=config)

    def _report_job_exception(job: bigquery.job.LoadJob) -> None:
        try:
            result = job.result()
            logging.info(f"BigQuery job {job.job_id} completed with result: {result}")
        except Exception:
            logging.exception(f"Exception thrown from BigQuery job {job.job_id}")
            error_reporting.Client().report_exception()

    job.add_done_callback(_report_job_exception)
    return job


def _table_name_for_contract(contract: ib_insync.Contract) -> str:
    return str(contract.symbol)


async def _qualify_contract_specifier(
    ib_client: ib_insync.IB, specifier: blotter_pb2.ContractSpecifier
) -> ib_insync.Contract:
    contract = request_helpers.contract_from_specifier(specifier)
    await ib_client.qualifyContractsAsync(contract)

    return contract


_T = TypeVar("_T")


class Servicer(blotter_pb2_grpc.BlotterServicer):
    _real_time_bars: Dict[str, ib_insync.RealTimeBarList]

    def __init__(self, ib_thread: IBThread):
        self._ib_thread = ib_thread
        self._real_time_bars = {}
        super().__init__()

    def _run_in_ib_thread(
        self, fn: Callable[[ib_insync.IB], Awaitable[_T]]
    ) -> "concurrent.futures.Future[_T]":
        fut = self._ib_thread.schedule(fn)

        def _report_future_exception(future: "concurrent.futures.Future[_T]") -> None:
            try:
                future.result()
            except Exception:
                logging.exception(f"Exception thrown in IB thread")
                error_reporting.Client().report_exception()

        fut.add_done_callback(_report_future_exception)
        return fut

    def LoadHistoricalData(
        self,
        request: blotter_pb2.LoadHistoricalDataRequest,
        context: grpc.ServicerContext,
    ) -> blotter_pb2.LoadHistoricalDataResponse:
        logging.info(f"LoadHistoricalData: {request}")

        async def fetch_bars(ib_client: ib_insync.IB) -> bigquery.LoadJob:
            con = await _qualify_contract_specifier(
                ib_client, request.contractSpecifier
            )

            barList = await ib_client.reqHistoricalDataAsync(
                contract=con,
                endDateTime=datetime.utcfromtimestamp(request.endTimestampUTC),
                durationStr=request_helpers.duration_str(request.duration),
                barSizeSetting=request_helpers.bar_size_str(request.barSize),
                whatToShow=request_helpers.historical_bar_source_str(request.barSource),
                useRTH=request.regularTradingHoursOnly,
                formatDate=2,  # Convert all timestamps to UTC
            )

            if not barList:
                raise RuntimeError(f"Could not load historical data bars")

            df = ib_insync.util.df(barList)

            # See fields on BarData.
            df = pd.DataFrame(
                data={
                    _TableColumn.TIMESTAMP.value: df["date"],
                    _TableColumn.OPEN.value: df["open"],
                    _TableColumn.HIGH.value: df["high"],
                    _TableColumn.LOW.value: df["low"],
                    _TableColumn.CLOSE.value: df["close"],
                    _TableColumn.VOLUME.value: df["volume"],
                    _TableColumn.AVERAGE_PRICE.value: df["average"],
                    _TableColumn.BAR_COUNT.value: df["barCount"],
                }
            )

            df[_TableColumn.BAR_SOURCE.value] = barList.whatToShow

            logging.debug(df)
            return _upload_dataframe(_table_name_for_contract(con), df)

        job = self._run_in_ib_thread(fetch_bars).result()
        logging.info(f"BigQuery backfill job launched: {job.job_id}")

        return blotter_pb2.LoadHistoricalDataResponse(backfillJobID=job.job_id)

    def StartRealTimeData(
        self,
        request: blotter_pb2.StartRealTimeDataRequest,
        context: grpc.ServicerContext,
    ) -> blotter_pb2.StartRealTimeDataResponse:
        logging.info(f"StartRealTimeData: {request}")

        def bars_updated(bars: ib_insync.RealTimeBarList, has_new_bar: bool) -> None:
            logging.debug(f"Received {len(bars)} bars (has_new_bar={has_new_bar})")

            if not bars or not has_new_bar:
                return

            try:
                df = ib_insync.util.df(bars)

                # See fields on RealTimeBar.
                df = pd.DataFrame(
                    data={
                        _TableColumn.TIMESTAMP.value: df["time"],
                        _TableColumn.OPEN.value: df["open_"],
                        _TableColumn.HIGH.value: df["high"],
                        _TableColumn.LOW.value: df["low"],
                        _TableColumn.CLOSE.value: df["close"],
                        _TableColumn.VOLUME.value: df["volume"],
                        _TableColumn.AVERAGE_PRICE.value: df["wap"],
                        _TableColumn.BAR_COUNT.value: df["count"],
                    }
                )

                df[_TableColumn.BAR_SOURCE.value] = bars.whatToShow

                logging.debug(df)
                job = _upload_dataframe(_table_name_for_contract(bars.contract), df)

                logging.info(f"BigQuery data import job launched: {job.job_id}")
            except Exception:
                logging.exception(f"Cancelling real-time data due to exception")
                error_reporting.Client().report_exception()

                self._ib_thread.client_unsafe.cancelRealTimeBars(bars)

        async def start_stream(ib_client: ib_insync.IB) -> str:
            con = await _qualify_contract_specifier(
                ib_client, request.contractSpecifier
            )

            bar_list = ib_client.reqRealTimeBars(
                contract=con,
                barSize=5,
                whatToShow=request_helpers.real_time_bar_source_str(request.barSource),
                useRTH=request.regularTradingHoursOnly,
            )

            req_id = str(bar_list.reqId)
            if req_id in self._real_time_bars:
                logging.error(
                    f'Unexpectedly found "{req_id}" already in tracked bars: {self._real_time_bars}'
                )

            self._real_time_bars[req_id] = bar_list
            logging.debug(f"_real_time_bars: {self._real_time_bars}")

            bar_list.updateEvent += bars_updated

            return req_id

        req_id = self._run_in_ib_thread(start_stream).result()
        logging.debug(f"Real-time bars request ID: {req_id}")

        return blotter_pb2.StartRealTimeDataResponse(requestID=req_id)

    def CancelRealTimeData(
        self,
        request: blotter_pb2.CancelRealTimeDataRequest,
        context: grpc.ServicerContext,
    ) -> blotter_pb2.CancelRealTimeDataResponse:
        logging.info(f"CancelRealTimeData: {request}")

        async def cancel_stream(ib_client: ib_insync.IB) -> None:
            logging.debug(f"_real_time_bars: {self._real_time_bars}")

            bar_list = self._real_time_bars.pop(request.requestID, None)
            if bar_list is not None:
                ib_client.cancelRealTimeBars(bar_list)
                logging.info(
                    f"Cancelled real time bars for contract {bar_list.contract}"
                )

        self._run_in_ib_thread(cancel_stream)
        return blotter_pb2.CancelRealTimeDataResponse()


def start(
    port: int,
    ib_thread: IBThread,
    executor: Optional[concurrent.futures.ThreadPoolExecutor] = None,
) -> grpc.Server:
    if executor is None:
        executor = concurrent.futures.ThreadPoolExecutor()

    s = grpc.server(executor)
    blotter_pb2_grpc.add_BlotterServicer_to_server(Servicer(ib_thread), s)
    s.add_insecure_port(f"[::]:{port}")
    s.start()

    return s
