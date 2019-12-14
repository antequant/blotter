import logging
from enum import Enum, unique

import ib_insync
import pandas as pd
from google.cloud import bigquery

from blotter.error_handling import ErrorHandlerConfiguration


@unique
class BarsTableColumn(Enum):
    """
    Specifies the known/desired columns for BigQuery tables of bar data, so they can be standardized even when the data is merged from different sources.

    Other columns are still permitted, but it is recommended they have a prefix like `unknown_` or `extra_` to indicate that they will not always be populated.
    """

    TIMESTAMP = "timestamp"
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"
    AVERAGE_PRICE = "average"
    BAR_COUNT = "bar_count"
    BAR_SOURCE = "bar_source"


@unique
class TickersTableColumn(Enum):
    """
    Specifies the known/desired columns for BigQuery tables of ticker data, so they can be standardized even when the data is merged from different sources.

    Other columns are still permitted, but it is recommended they have a prefix like `unknown_` or `extra_` to indicate that they will not always be populated.
    """

    CONTRACT_ID = "contract_id"
    SYMBOL = "symbol"
    TIMESTAMP = "timestamp"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"
    BID = "bid"
    BID_SIZE = "bid_size"
    ASK = "ask"
    ASK_SIZE = "ask_size"
    LAST = "last"
    LAST_SIZE = "last_size"


def upload_dataframe(
    table_id: str, df: pd.DataFrame, error_handler: ErrorHandlerConfiguration
) -> bigquery.job.LoadJob:
    """
    Enqueues an asynchronous job to upload the given DataFrame to the named table.

    Returns the job that was started.
    """

    client = bigquery.Client()
    dataset_id = "blotter"

    dataset_ref = client.dataset(dataset_id)
    table_ref = dataset_ref.table(table_id)

    assert BarsTableColumn.TIMESTAMP.value == TickersTableColumn.TIMESTAMP.value

    config = bigquery.job.LoadJobConfig(
        time_partitioning=bigquery.table.TimePartitioning(
            field=BarsTableColumn.TIMESTAMP.value
        ),
        schema_update_options=bigquery.job.SchemaUpdateOption.ALLOW_FIELD_ADDITION,
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=config)

    def _report_job_exception(job: bigquery.job.LoadJob) -> None:
        with error_handler(f"Exception thrown from BigQuery job {job.job_id}"):
            result = job.result()
            logging.info(f"BigQuery job {job.job_id} completed with result: {result}")

    job.add_done_callback(_report_job_exception)
    return job


def table_name_for_contract(contract: ib_insync.Contract) -> str:
    """
    Picks a BigQuery table name for the given contract.
    """

    return f"{contract.localSymbol}_{contract.conId}"
