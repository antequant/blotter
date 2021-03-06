from datetime import datetime
from logging import getLogger
from typing import Tuple

import ib_insync
import pandas as pd
from google.cloud import bigquery

from blotter import request_helpers
from blotter.blotter_pb2 import ContractSpecifier
from gcloud_service.error_handler import ErrorHandlerConfiguration
from blotter.ib_helpers import DataError, qualify_contract_specifier
from blotter.upload import BarsTableColumn, table_name_for_contract, upload_dataframe

logger = getLogger(__name__)


async def backfill_bars(
    ib_client: ib_insync.IB,
    contract_specifier: ContractSpecifier,
    end_date: datetime,
    duration: str,
    bar_size: str,
    bar_source: str,
    regular_trading_hours_only: bool,
    error_handler: ErrorHandlerConfiguration,
) -> Tuple[datetime, bigquery.LoadJob]:
    """
    Fetches historical bars (of type `bar_source` and interval `bar_size`) for the given contract over the specified time interval, then enqueues a BigQuery import job.

    Returns the date of the earliest bar loaded and a reference the job that was started.
    """

    con = await qualify_contract_specifier(ib_client, contract_specifier)

    barList = await ib_client.reqHistoricalDataAsync(
        contract=con,
        endDateTime=end_date,
        durationStr=duration,
        barSizeSetting=bar_size,
        whatToShow=bar_source,
        useRTH=regular_trading_hours_only,
        formatDate=2,  # Convert all timestamps to UTC
    )

    if not barList:
        raise DataError(f"backfill_bars: Received empty historical data bars for {con}")

    earliest_date = barList[0].date

    logger.info(f"Loaded {len(barList)} historical bars for {con}")
    df = ib_insync.util.df(barList)

    # See fields on BarData.
    df = pd.DataFrame(
        data={
            BarsTableColumn.TIMESTAMP.value: df["date"],
            BarsTableColumn.OPEN.value: df["open"],
            BarsTableColumn.HIGH.value: df["high"],
            BarsTableColumn.LOW.value: df["low"],
            BarsTableColumn.CLOSE.value: df["close"],
            BarsTableColumn.VOLUME.value: df["volume"],
            BarsTableColumn.AVERAGE_PRICE.value: df["average"],
            BarsTableColumn.BAR_COUNT.value: df["barCount"],
        }
    )

    df[BarsTableColumn.BAR_SOURCE.value] = barList.whatToShow

    logger.debug(df)
    job = upload_dataframe(table_name_for_contract(con), df, error_handler)

    return (earliest_date, job)
