import asyncio
import concurrent.futures as futures
import logging
from datetime import datetime
from typing import Any, Optional, cast

import grpc

from blotter import blotter_pb2, blotter_pb2_grpc, model
import ib_insync
import pandas as pd

from google.cloud import bigquery


class Servicer(blotter_pb2_grpc.BlotterServicer):
    def __init__(self, ib_client: ib_insync.IB, eventLoop: asyncio.AbstractEventLoop):
        self._ib_client = ib_client
        self._loop = eventLoop
        super().__init__()

    def LoadHistoricalData(self, request: Any, context: Any) -> Any:
        logging.info(f"LoadHistoricalData: {request}")

        async def fetch_bars() -> pd.DataFrame:
            con = model.contract_from_specifier(request.contractSpecifier)
            await self._ib_client.qualifyContractsAsync(con)

            barList = await self._ib_client.reqHistoricalDataAsync(
                contract=con,
                endDateTime=datetime.utcfromtimestamp(request.endTimestampUTC),
                durationStr=model.duration_str(request.duration),
                barSizeSetting=model.bar_size_str(request.barSize),
                whatToShow=model.bar_source_str(request.barSource),
                useRTH=request.regularTradingHoursOnly,
            )

            if not barList:
                raise RuntimeError(f"Could not load historical data bars")

            return ib_insync.util.df(barList)

        df = asyncio.run_coroutine_threadsafe(fetch_bars(), self._loop).result()
        logging.debug(f"DataFrame sample: {df.sample()}")

        client = bigquery.Client()
        dataset_id = "blotter"
        table_id = f"test_{request.contractSpecifier.symbol}"

        dataset_ref = client.dataset(dataset_id)
        table_ref = dataset_ref.table(table_id)

        job = client.load_table_from_dataframe(df, table_ref)
        result = job.result()
        logging.info(f"BigQuery job result: {result}")

        return blotter_pb2.LoadHistoricalDataResponse()


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
