import logging
from datetime import datetime

import ib_insync
import pandas as pd
from blotter import request_helpers
from blotter.blotter_pb2 import ContractSpecifier
from blotter.ib_helpers import qualify_contract_specifier
from blotter.upload import TableColumn, table_name_for_contract, upload_dataframe
from google.cloud import bigquery


async def backfill_bars(
    ib_client: ib_insync.IB,
    contract_specifier: ContractSpecifier,
    end_date: datetime,
    duration: str,
    bar_size: str,
    bar_source: str,
    regular_trading_hours_only: bool,
) -> bigquery.LoadJob:
    """
    Fetches historical bars (of type `bar_source` and interval `bar_size`) for the given contract over the specified time interval, then enqueues a BigQuery import job.
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
        raise RuntimeError(f"Could not load historical data bars for {con}")

    df = ib_insync.util.df(barList)

    # See fields on BarData.
    df = pd.DataFrame(
        data={
            TableColumn.TIMESTAMP.value: df["date"],
            TableColumn.OPEN.value: df["open"],
            TableColumn.HIGH.value: df["high"],
            TableColumn.LOW.value: df["low"],
            TableColumn.CLOSE.value: df["close"],
            TableColumn.VOLUME.value: df["volume"],
            TableColumn.AVERAGE_PRICE.value: df["average"],
            TableColumn.BAR_COUNT.value: df["barCount"],
        }
    )

    df[TableColumn.BAR_SOURCE.value] = barList.whatToShow

    logging.debug(df)
    return upload_dataframe(table_name_for_contract(con), df)
