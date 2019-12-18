import asyncio
import dataclasses
from dataclasses import dataclass
from datetime import datetime, timedelta
from logging import getLogger
from typing import Any, Dict, Iterable, List, NewType

from google.cloud import firestore

import blotter.bigquery_helpers as bigquery_helpers
import ib_insync
from blotter.error_handling import ErrorHandlerConfiguration
from blotter.ib_helpers import IBThread, deserialize_contract, serialize_contract
from blotter.tickers import load_tickers_into_dataframe
from blotter.upload import upload_dataframe

logger = getLogger(__name__)

PollingID = NewType("PollingID", str)
"""A unique ID for market data polling."""


@dataclass(frozen=True)
class _PollingJob:
    """
    Metadata about a market data polling job which can be serialized, so that it can be resumed even across server restarts.
    """

    serialized_contracts: List[Dict[str, Any]]
    """One or more `ib_insync.Contract`s serialized into dictionary form."""

    polling_interval: timedelta
    """How often the polling should be performed."""

    upload_table_name: str
    """The name of the BigQuery table to upload into."""

    @classmethod
    def from_contracts(
        cls,
        contracts: Iterable[ib_insync.Contract],
        polling_interval: timedelta,
        upload_table_name: str,
    ) -> "_PollingJob":
        return cls(
            serialized_contracts=[
                serialize_contract(contract) for contract in contracts
            ],
            polling_interval=polling_interval,
            upload_table_name=upload_table_name,
        )

    @property
    def contracts(self) -> Iterable[ib_insync.Contract]:
        return (deserialize_contract(d) for d in self.serialized_contracts)


class PollingManager:
    """
    Manages periodic polling of market data.
    """

    DEFAULT_POLLING_INTERVAL = timedelta(minutes=5)
    """The default length of time we should wait between market data polling. In other words, how old the data is permitted to be."""

    _FIRESTORE_COLLECTION = "polling_jobs"
    """The name of the Firestore document collection storing polling jobs' metadata, so they can be resumed."""

    _polling_tasks: Dict[PollingID, "asyncio.Task[None]"]
    """Ongoing polling tasks."""

    def __init__(self, error_handler: ErrorHandlerConfiguration,) -> None:
        default_poll_count_per_day = timedelta(days=1) / self.DEFAULT_POLLING_INTERVAL
        assert (
            default_poll_count_per_day <= bigquery_helpers.PERMITTED_OPERATIONS_PER_DAY
        ), f"Expected number of polling uploads {default_poll_count_per_day} would exceed permitted {bigquery_helpers.PERMITTED_OPERATIONS_PER_DAY}"

        self._firestore_db = firestore.Client()
        self._error_handler = error_handler
        super().__init__()

    @property
    def _firestore_collection(self) -> firestore.CollectionReference:
        return self._firestore_db.collection(self._FIRESTORE_COLLECTION)

    def _record_job_in_firestore(self, job: _PollingJob) -> PollingID:
        """
        Records the given polling job in Firestore, so it can persist across server restarts.

        Returns a unique ID corresponding to the job.
        """

        doc = self._firestore_collection.document()
        logger.debug(f"Recording polling job with ID {doc.id}: {job}")

        doc.set(dataclasses.asdict(job))
        return PollingID(doc.id)

    def _delete_job_from_firestore(self, job_id: PollingID) -> None:
        """
        Deletes a polling job from Firestore.
        """

        logger.debug(f"Removing polling job with ID {job_id}")
        self._firestore_collection.document(job_id).delete()

    async def cancel_polling(
        self, ib_client: ib_insync.IB, polling_id: PollingID
    ) -> None:
        """
        Cancels a polling job, removing its metadata from Firestore (so it will no longer be resumed) and stopping the periodic timer.
        """

        logger.debug(
            f"{len(self._polling_tasks)} _polling_tasks before cancelling: {self._polling_tasks.keys()}"
        )
        task = self._polling_tasks.pop(polling_id, None)
        if task is not None:
            task.cancel()

        self._delete_job_from_firestore(polling_id)
        logger.info(f"Cancelled polling for job ID {polling_id}")

    # TODO: Support some concept of trading hours, because this will be super wasteful for equity options otherwise
    async def start_polling(
        self,
        ib_client: ib_insync.IB,
        contracts: List[ib_insync.Contract],
        upload_table_name: str,
        polling_interval: timedelta = DEFAULT_POLLING_INTERVAL,
    ) -> PollingID:
        """
        Starts polling data for the given contracts and uploading the results into BigQuery.

        Returns an ID (unique for the lifetime of the service) which can later be used to cancel the polling.

        WARNING: This method does no checking for duplicate requests.
        """

        poll_count_per_day = timedelta(days=1) / polling_interval
        if poll_count_per_day > bigquery_helpers.PERMITTED_OPERATIONS_PER_DAY:
            logger.warn(
                f"Expected number of polling uploads {poll_count_per_day} would exceed permitted {bigquery_helpers.PERMITTED_OPERATIONS_PER_DAY}"
            )

        polling_job = _PollingJob.from_contracts(
            contracts,
            polling_interval=polling_interval,
            upload_table_name=upload_table_name,
        )

        polling_id = self._record_job_in_firestore(polling_job)
        logger.info(
            f"Starting polling for {len(contracts)} contracts with ID {polling_id}"
        )

        await self._start_job(ib_client, polling_job, polling_id, contracts=contracts)
        return polling_id

    async def _start_job(
        self,
        ib_client: ib_insync.IB,
        polling_job: _PollingJob,
        polling_id: PollingID,
        contracts: List[ib_insync.Contract],  # FIXME: Get rid of this?
    ) -> None:
        """
        Starts polling market data for the described job, which should have already been recorded for later resumption.
        """

        async def _polling_loop() -> None:
            with self._error_handler(f"Cancelled polling due to exception:"):
                try:
                    while True:
                        logger.info(f"Fetching tickers for {len(contracts)} contracts")
                        df = load_tickers_into_dataframe(ib_client, contracts)
                        logger.debug(df)

                        job = upload_dataframe(
                            polling_job.upload_table_name, df, self._error_handler
                        )

                        logger.info(f"BigQuery data import job launched: {job.job_id}")

                        next_wake_up = datetime.now() + polling_job.polling_interval
                        logger.info(f"{polling_id} polling again at {next_wake_up}")

                        await ib_insync.util.waitUntilAsync(next_wake_up)
                except Exception:
                    await self.cancel_polling(ib_client, polling_id)
                    raise

        task = asyncio.create_task(_polling_loop())

        self._polling_tasks[polling_id] = task
        logger.debug(
            f"{len(self._polling_tasks)} _polling_tasks: {self._polling_tasks.keys()}"
        )
