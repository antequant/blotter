import asyncio
import dataclasses
import math
from dataclasses import dataclass
from datetime import timedelta
from logging import getLogger
from typing import Any, Dict, Iterator, NewType, Optional

import ib_insync
import pandas as pd
from google.cloud import firestore

from blotter.blotter_pb2 import ContractSpecifier
from blotter.error_handling import ErrorHandlerConfiguration
from blotter.ib_helpers import (
    IBThread,
    deserialize_contract,
    qualify_contract_specifier,
    serialize_contract,
)
from blotter.upload import BarsTableColumn, table_name_for_contract, upload_dataframe

logger = getLogger(__name__)

StreamingID = NewType("StreamingID", str)
"""A unique ID for ongoing market data streaming."""


@dataclass(frozen=True)
class _StreamingJob:
    """
    Metadata about a streaming market data job (a.k.a. request) which can be serialized, so that the streaming can be resumed even across server restarts.
    """

    serialized_contract: Dict[str, Any]
    """An `ib_insync.Contract` serialized into dictionary form."""

    bar_size: int
    """Argument to `ib_insync.IB.reqRealTimeBars`."""

    what_to_show: str
    """Argument to `ib_insync.IB.reqRealTimeBars`."""

    use_regular_trading_hours: bool
    """Argument to `ib_insync.IB.reqRealTimeBars`."""

    def start_request(self, ib_client: ib_insync.IB) -> ib_insync.RealTimeBarList:
        """
        Submits this streaming request to the given IB client.
        """

        return ib_client.reqRealTimeBars(
            deserialize_contract(self.serialized_contract),
            barSize=self.bar_size,
            whatToShow=self.what_to_show,
            useRTH=self.use_regular_trading_hours,
        )


class StreamingManager:
    """
    Manages the lifetime of market data streaming requests.
    """

    _MAX_BIGQUERY_OPERATIONS_PER_DAY = 1000
    """The maximum number of BigQuery operations permitted per table per day."""

    _PERMITTED_OPERATIONS_PER_DAY = _MAX_BIGQUERY_OPERATIONS_PER_DAY * 0.5
    """How much of the BigQuery operations allowance to actually use, to leave headroom for other things."""

    _BAR_SIZE = timedelta(seconds=5)
    """The granularity of real-time data bars, and (while streaming) how quickly they arrive."""

    _MAXIMUM_BARS_PER_DAY = timedelta(days=1) / _BAR_SIZE
    """The maximum number of real-time data bars that could be reasonably expected in one day."""

    DEFAULT_BATCH_SIZE = math.ceil(
        _MAXIMUM_BARS_PER_DAY / _PERMITTED_OPERATIONS_PER_DAY
    )
    """A reasonable default number of bars to batch together for upload."""

    DEFAULT_BATCH_LATENCY = timedelta(minutes=10)
    """The default limit on the length of time we should wait to upload bars. In other words, how old the data is permitted to be."""

    _FIRESTORE_COLLECTION = "streaming_jobs"
    """The name of the Firestore document collection storing streaming request metadata, so they can be resumed."""

    _real_time_bars: Dict[StreamingID, ib_insync.RealTimeBarList]
    """Ongoing streaming data requests."""

    def __init__(
        self,
        error_handler: ErrorHandlerConfiguration,
        batch_size: int = DEFAULT_BATCH_SIZE,
        batch_timeout: timedelta = DEFAULT_BATCH_LATENCY,
    ) -> None:
        assert batch_size >= 1, f"Batch size {batch_size} should be a natural number"
        assert (
            batch_timeout.total_seconds() >= 1
        ), f"Batch timeout {batch_timeout} should be at least 1 second"

        if batch_size * self._BAR_SIZE > batch_timeout:
            logger.warn(
                f"Batch size {batch_size} would take {batch_size * self._BAR_SIZE} to collect, greater than timeout {batch_timeout}"
            )

        self._real_time_bars = {}
        self._firestore_db = firestore.Client()
        self._error_handler = error_handler
        self._batch_size = batch_size
        self._batch_timeout = batch_timeout
        super().__init__()

    @property
    def _firestore_collection(self) -> firestore.CollectionReference:
        return self._firestore_db.collection(self._FIRESTORE_COLLECTION)

    def resume_streaming(self, ib_thread: IBThread) -> Iterator[StreamingID]:
        """
        Attempts to load metadata about previously-running streaming jobs from Firestore, then resume them using the given IB thread.

        Yields the IDs of the jobs that were resumed (though later failures are still possible).
        """

        docs = self._firestore_collection.stream()
        for doc in docs:
            streaming_job = None
            with self._error_handler(
                f"Failed to deserialize streaming job from document {doc}"
            ):
                streaming_job = _StreamingJob(**doc.to_dict())

            if streaming_job is None:
                continue

            streaming_id = StreamingID(doc.id)

            async def _resume_job(ib_client: ib_insync.IB) -> None:
                assert streaming_job is not None

                with self._error_handler(
                    f"Failed to resume streaming job {streaming_id}"
                ):
                    await self._start_job(ib_client, streaming_job, streaming_id)

            logger.info(
                f"Resuming streaming for {streaming_job} with ID {streaming_id}"
            )
            ib_thread.schedule(_resume_job)
            yield streaming_id

    def _record_job_in_firestore(self, job: _StreamingJob) -> StreamingID:
        """
        Records the given streaming job in Firestore, so it can persist across server restarts.

        Returns a unique ID corresponding to the job.
        """

        doc = self._firestore_collection.document()
        logger.debug(f"Recording streaming job with ID {doc.id}: {job}")

        doc.set(dataclasses.asdict(job))
        return StreamingID(doc.id)

    def _delete_job_from_firestore(self, job_id: StreamingID) -> None:
        """
        Deletes a streaming job from Firestore.
        """

        logger.debug(f"Removing streaming job with ID {job_id}")
        self._firestore_collection.document(job_id).delete()

    def _cancel_job(
        self, ib_client: ib_insync.IB, streaming_id: StreamingID
    ) -> Optional[ib_insync.RealTimeBarList]:
        """
        Cancels a streaming job, removing its metadata from Firestore (so it will no longer be resumed) and cancelling streaming market data from IB.

        Returns the final `RealTimeBarList` associated with this ID, if it could be found.
        """

        logger.debug(f"_real_time_bars before cancelling: {self._real_time_bars}")
        bar_list = self._real_time_bars.pop(streaming_id, None)
        if bar_list is not None:
            ib_client.cancelRealTimeBars(bar_list)

        self._delete_job_from_firestore(streaming_id)
        return bar_list

    async def start_stream(
        self,
        ib_client: ib_insync.IB,
        contract_specifier: ContractSpecifier,
        bar_source: str,
        regular_trading_hours_only: bool,
    ) -> StreamingID:
        """
        Starts streaming data for the given contract and uploading the results into BigQuery.

        Returns an ID (unique for the lifetime of the service) which can later be used to cancel this streaming.

        WARNING: This method does no checking for duplicate requests.
        """

        contract = await qualify_contract_specifier(ib_client, contract_specifier)

        streaming_job = _StreamingJob(
            serialized_contract=serialize_contract(contract),
            bar_size=5,
            what_to_show=bar_source,
            use_regular_trading_hours=regular_trading_hours_only,
        )

        streaming_id = self._record_job_in_firestore(streaming_job)
        logger.info(f"Starting streaming for {contract} with ID {streaming_id}")

        await self._start_job(ib_client, streaming_job, streaming_id)
        return streaming_id

    async def _start_job(
        self,
        ib_client: ib_insync.IB,
        streaming_job: _StreamingJob,
        streaming_id: StreamingID,
    ) -> None:
        """
        Starts streaming market data for the described job, which should have already been recorded for later resumption.
        """

        batch_timer: Optional[asyncio.TimerHandle] = None

        def _bars_updated(
            bars: ib_insync.RealTimeBarList,
            has_new_bar: bool,
            timer_fired: bool = False,
        ) -> None:
            nonlocal batch_timer

            bar_count = len(bars)
            logger.debug(
                f"Received {bar_count} bars (has_new_bar={has_new_bar}, timer_fired={timer_fired})"
            )

            if not bars:
                return

            if not timer_fired and bar_count < self._batch_size:
                logger.debug(
                    f"Skipping upload because bar count {bar_count} is less than batch size {self._batch_size}"
                )

                if not batch_timer:
                    batch_timer = asyncio.get_running_loop().call_later(
                        self._batch_timeout.total_seconds(),
                        _bars_updated,
                        bars,
                        False,
                        True,
                    )

                    logger.debug(f"Scheduled batch flush after {self._batch_timeout}")

                return

            logger.info(
                f"Flushing batch of {bar_count} real-time bars (timer_fired={timer_fired})"
            )

            if batch_timer:
                batch_timer.cancel()
                batch_timer = None

            with self._error_handler(f"Cancelled real-time data due to exception:"):
                try:
                    df = ib_insync.util.df(bars)
                    bars.clear()

                    # See fields on RealTimeBar.
                    df = pd.DataFrame(
                        data={
                            BarsTableColumn.TIMESTAMP.value: df["time"],
                            BarsTableColumn.OPEN.value: df["open_"],
                            BarsTableColumn.HIGH.value: df["high"],
                            BarsTableColumn.LOW.value: df["low"],
                            BarsTableColumn.CLOSE.value: df["close"],
                            BarsTableColumn.VOLUME.value: df["volume"],
                            BarsTableColumn.AVERAGE_PRICE.value: df["wap"],
                            BarsTableColumn.BAR_COUNT.value: df["count"],
                        }
                    )

                    df[BarsTableColumn.BAR_SOURCE.value] = bars.whatToShow

                    logger.debug(df)
                    job = upload_dataframe(
                        table_name_for_contract(bars.contract), df, self._error_handler
                    )

                    logger.info(f"BigQuery data import job launched: {job.job_id}")
                except Exception:
                    self._cancel_job(ib_client, streaming_id)
                    raise

        bar_list = streaming_job.start_request(ib_client)

        self._real_time_bars[streaming_id] = bar_list
        logger.debug(f"_real_time_bars: {self._real_time_bars}")

        bar_list.updateEvent += _bars_updated

    async def cancel_stream(
        self, ib_client: ib_insync.IB, streaming_id: StreamingID
    ) -> None:
        """
        Cancels a previous streaming request, identified by `streaming_id`.

        If the data is no longer streaming, nothing happens.
        """

        bar_list = self._cancel_job(ib_client, streaming_id)
        if bar_list is not None:
            logger.info(f"Cancelled real time bars for contract {bar_list.contract}")
