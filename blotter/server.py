import asyncio
import concurrent.futures as futures
import logging
from datetime import datetime
from typing import Dict, Optional, cast

import grpc

from blotter import blotter_pb2, blotter_pb2_grpc, model
import ib_insync
import pandas as pd

from google.cloud import bigquery


def _upload_dataframe(table_id: str, df: pd.DataFrame) -> bigquery.job.LoadJob:
    client = bigquery.Client()
    dataset_id = "blotter"

    dataset_ref = client.dataset(dataset_id)
    table_ref = dataset_ref.table(table_id)
    config = bigquery.job.LoadJobConfig(
        time_partitioning=bigquery.table.TimePartitioning(field="date"),
        schema_update_options=bigquery.job.SchemaUpdateOption.ALLOW_FIELD_ADDITION,
    )

    return client.load_table_from_dataframe(df, table_ref, job_config=config)


class Servicer(blotter_pb2_grpc.BlotterServicer):
    _real_time_bars: Dict[str, ib_insync.RealTimeBarList]

    def __init__(self, ib_client: ib_insync.IB, eventLoop: asyncio.AbstractEventLoop):
        self._ib_client = ib_client
        self._loop = eventLoop
        self._real_time_bars = {}
        super().__init__()

    async def _qualify_contract_specifier(
        self, specifier: blotter_pb2.ContractSpecifier
    ) -> ib_insync.Contract:
        contract = model.contract_from_specifier(specifier)
        await self._ib_client.qualifyContractsAsync(contract)

        return contract

    def LoadHistoricalData(
        self,
        request: blotter_pb2.LoadHistoricalDataRequest,
        context: grpc.ServicerContext,
    ) -> blotter_pb2.LoadHistoricalDataResponse:
        logging.info(f"LoadHistoricalData: {request}")

        async def fetch_bars() -> pd.DataFrame:
            con = await self._qualify_contract_specifier(request.contractSpecifier)

            barList = await self._ib_client.reqHistoricalDataAsync(
                contract=con,
                endDateTime=datetime.utcfromtimestamp(request.endTimestampUTC),
                durationStr=model.duration_str(request.duration),
                barSizeSetting=model.bar_size_str(request.barSize),
                whatToShow=model.historical_bar_source_str(request.barSource),
                useRTH=request.regularTradingHoursOnly,
                formatDate=2,  # Convert all timestamps to UTC
            )

            if not barList:
                raise RuntimeError(f"Could not load historical data bars")

            return ib_insync.util.df(barList)

        df = asyncio.run_coroutine_threadsafe(fetch_bars(), self._loop).result()
        logging.debug(df)

        job = _upload_dataframe(f"test_{request.contractSpecifier.symbol}", df)
        result = job.result()
        logging.info(f"BigQuery historical data import: {result}")

        return blotter_pb2.LoadHistoricalDataResponse()

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
                df = df.rename(columns={"time": "date"})
                logging.debug(df)

                job = _upload_dataframe(f"test_{bars.contract.symbol}", df)
                result = job.result()
                logging.info(f"BigQuery real-time data import: {result}")
            except Exception as err:
                logging.error(
                    f"Cancelling real-time data due to exception thrown: {err}"
                )

                self._ib_client.cancelRealTimeBars(bars)

        async def start_stream() -> str:
            con = await self._qualify_contract_specifier(request.contractSpecifier)

            bar_list = self._ib_client.reqRealTimeBars(
                contract=con,
                barSize=5,
                whatToShow=model.real_time_bar_source_str(request.barSource),
                useRTH=request.regularTradingHoursOnly,
            )

            req_id = str(bar_list.reqId)
            if req_id in self._real_time_bars:
                logging.error(
                    f'Unexpectedly found "{req_id}" already in tracked bars: {self._real_time_bars}'
                )

            self._real_time_bars[req_id] = bar_list
            bar_list.updateEvent += bars_updated

            return req_id

        req_id = asyncio.run_coroutine_threadsafe(start_stream(), self._loop).result()
        logging.debug(f"Real-time bars request ID: {req_id}")

        return blotter_pb2.StartRealTimeDataResponse(requestID=req_id)

    def CancelRealTimeData(
        self,
        request: blotter_pb2.CancelRealTimeDataRequest,
        context: grpc.ServicerContext,
    ) -> blotter_pb2.CancelRealTimeDataResponse:
        logging.info(f"CancelRealTimeData: {request}")

        async def cancel_stream() -> None:
            bar_list = self._real_time_bars.pop(request.requestID, None)
            if bar_list:
                self._ib_client.cancelRealTimeBars(bar_list)

        asyncio.run_coroutine_threadsafe(cancel_stream(), self._loop)
        return blotter_pb2.CancelRealTimeDataResponse()


def start(
    port: int,
    ib_client: ib_insync.IB,
    eventLoop: Optional[asyncio.AbstractEventLoop] = None,
    executor: Optional[futures.ThreadPoolExecutor] = None,
) -> grpc.Server:
    if eventLoop is None:
        eventLoop = asyncio.get_running_loop()

    if executor is None:
        executor = futures.ThreadPoolExecutor()

    s = grpc.server(executor)
    blotter_pb2_grpc.add_BlotterServicer_to_server(Servicer(ib_client, eventLoop), s)
    s.add_insecure_port(f"[::]:{port}")
    s.start()

    return s
