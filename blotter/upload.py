import logging
from enum import Enum, unique

import ib_insync
import pandas as pd
from google.cloud import bigquery, error_reporting


@unique
class TableColumn(Enum):
    TIMESTAMP = "timestamp"
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"
    AVERAGE_PRICE = "average"
    BAR_COUNT = "bar_count"
    BAR_SOURCE = "bar_source"


def upload_dataframe(table_id: str, df: pd.DataFrame) -> bigquery.job.LoadJob:
    client = bigquery.Client()
    dataset_id = "blotter"

    dataset_ref = client.dataset(dataset_id)
    table_ref = dataset_ref.table(table_id)
    config = bigquery.job.LoadJobConfig(
        time_partitioning=bigquery.table.TimePartitioning(
            field=TableColumn.TIMESTAMP.value
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


def table_name_for_contract(contract: ib_insync.Contract) -> str:
    return str(contract.symbol)