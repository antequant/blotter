import asyncio
import dataclasses
import logging
import math
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, Iterator, NewType, Optional

import ib_insync
import pandas as pd
from blotter.blotter_pb2 import ContractSpecifier
from blotter.ib_helpers import IBThread, qualify_contract_specifier
from blotter.upload import TableColumn, table_name_for_contract, upload_dataframe
from google.cloud import error_reporting, firestore

StreamingID = NewType("StreamingID", str)
"""A unique ID for ongoing market data streaming."""


@dataclass(frozen=True)
class _StreamingJob:
    contract_id: int
    bar_size: int
    what_to_show: str
    use_regular_trading_hours: bool

    @classmethod
    def create_from_bar_list(
        cls, bar_list: ib_insync.RealTimeBarList
    ) -> "_StreamingJob":
        return cls(
            contract_id=bar_list.contract.conId,
            bar_size=bar_list.barSize,
            what_to_show=bar_list.whatToShow,
            use_regular_trading_hours=bar_list.useRTH,
        )

    def start_request(self, ib_client: ib_insync.IB) -> ib_insync.RealTimeBarList:
        return ib_client.reqRealTimeBars(
            ib_insync.Contract(conId=self.contract_id),
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

    _BIGQUERY_SAFETY_HEADROOM = 0.5
    """What % of the BigQuery operations allowance to actually use, to leave headroom for other things."""

    _BAR_SIZE = timedelta(seconds=5)
    """The granularity of real-time data bars, and (while streaming) how quickly they arrive."""

    _MAX_BATCH_LATENCY = timedelta(minutes=10)
    """The longest length of time we should wait to upload bars. In other words, how old the data is permitted to be."""

    _FIRESTORE_COLLECTION = "streaming_jobs"
    """The name of the Firestore document collection storing streaming request metadata, so they can be resumed."""

    _real_time_bars: Dict[StreamingID, ib_insync.RealTimeBarList]
    """Active, in-memory streaming data requests."""

    def __init__(self) -> None:
        self._real_time_bars = {}
        self._firestore_db = firestore.Client()
        super().__init__()

    @property
    def _firestore_collection(self) -> firestore.CollectionReference:
        return self._firestore_db.collection(self._FIRESTORE_COLLECTION)

    def resume_streaming(self, ib_thread: IBThread) -> Iterator[StreamingID]:
        docs = self._firestore_collection.stream()
        for doc in docs:
            try:
                streaming_job = _StreamingJob(**doc.to_dict())
            except Exception:
                logging.exception(
                    f"Failed to deserialize streaming job from document {doc}"
                )
                continue

            contract = ib_insync.Contract(conId=streaming_job.contract_id)
            streaming_id = StreamingID(doc.id)

            async def _resume_job(ib_client: ib_insync.IB) -> None:
                try:
                    await self._start_job(
                        ib_client, contract, streaming_job, streaming_id
                    )
                except Exception:
                    logging.exception(f"Failed to resume streaming job {streaming_id}")

            logging.info(f"Resuming streaming for {contract} with ID {streaming_id}")
            ib_thread.schedule(_resume_job)
            yield streaming_id

    def _record_job_in_firestore(self, job: _StreamingJob) -> StreamingID:
        doc = self._firestore_collection.document()
        logging.debug(f"Recording streaming job with ID {doc.id}: {job}")

        doc.set(dataclasses.asdict(job))
        return StreamingID(doc.id)

    def _delete_job_from_firestore(self, job_id: StreamingID) -> None:
        logging.debug(f"Removing streaming job with ID {job_id}")
        self._firestore_collection.document(job_id).delete()

    def _cancel_job(
        self, ib_client: ib_insync.IB, streaming_id: StreamingID
    ) -> Optional[ib_insync.RealTimeBarList]:
        logging.debug(f"_real_time_bars before cancelling: {self._real_time_bars}")
        bar_list = self._real_time_bars.pop(streaming_id, None)
        if bar_list is not None:
            ib_client.cancelRealTimeBars(bar_list)

        self._delete_job_from_firestore(streaming_id)
        return bar_list

    @classmethod
    @property
    def _preferred_batch_size(cls) -> int:
        bars_per_day = timedelta(days=1) / cls._BAR_SIZE

        permitted_ops = (
            cls._MAX_BIGQUERY_OPERATIONS_PER_DAY * cls._BIGQUERY_SAFETY_HEADROOM
        )

        batch_size = math.ceil(bars_per_day / permitted_ops)
        assert batch_size >= 1, "Batch size should be a natural number"

        if batch_size * cls._BAR_SIZE > cls._MAX_BATCH_LATENCY:
            logging.warn(
                f"Preferred batch size {batch_size} would take {batch_size * cls._BAR_SIZE} to collect, greater than maximum {cls._MAX_BATCH_LATENCY}"
            )

        return batch_size

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
            contract_id=contract.conId,
            bar_size=5,
            what_to_show=bar_source,
            use_regular_trading_hours=regular_trading_hours_only,
        )

        streaming_id = self._record_job_in_firestore(streaming_job)
        logging.info(f"Starting streaming for {contract} with ID {streaming_id}")

        await self._start_job(ib_client, contract, streaming_job, streaming_id)
        return streaming_id

    async def _start_job(
        self,
        ib_client: ib_insync.IB,
        contract: ib_insync.Contract,
        streaming_job: _StreamingJob,
        streaming_id: StreamingID,
    ) -> None:
        batch_timer: Optional[asyncio.TimerHandle] = None

        def _bars_updated(
            bars: ib_insync.RealTimeBarList,
            has_new_bar: bool,
            timer_fired: bool = False,
        ) -> None:
            nonlocal batch_timer

            bar_count = len(bars)
            logging.debug(
                f"Received {bar_count} bars (has_new_bar={has_new_bar}, timer_fired={timer_fired})"
            )

            if not bars:
                return

            batch_size = self._preferred_batch_size
            if bar_count < batch_size:
                logging.debug(
                    f"Skipping upload because bar count {bar_count} is less than batch size {batch_size}"
                )

                if not batch_timer:
                    batch_timer = asyncio.get_running_loop().call_later(
                        self._MAX_BATCH_LATENCY.total_seconds(),
                        _bars_updated,
                        bars,
                        False,
                        True,
                    )

                    logging.debug(
                        f"Scheduled batch flush after {self._MAX_BATCH_LATENCY}"
                    )

                return

            logging.info(
                f"Flushing batch of {bar_count} real-time bars (timer_fired={timer_fired})"
            )

            if batch_timer:
                batch_timer.cancel()
                batch_timer = None

            try:
                df = ib_insync.util.df(bars)
                bars.clear()

                # See fields on RealTimeBar.
                df = pd.DataFrame(
                    data={
                        TableColumn.TIMESTAMP.value: df["time"],
                        TableColumn.OPEN.value: df["open_"],
                        TableColumn.HIGH.value: df["high"],
                        TableColumn.LOW.value: df["low"],
                        TableColumn.CLOSE.value: df["close"],
                        TableColumn.VOLUME.value: df["volume"],
                        TableColumn.AVERAGE_PRICE.value: df["wap"],
                        TableColumn.BAR_COUNT.value: df["count"],
                    }
                )

                df[TableColumn.BAR_SOURCE.value] = bars.whatToShow

                logging.debug(df)
                job = upload_dataframe(table_name_for_contract(bars.contract), df)

                logging.info(f"BigQuery data import job launched: {job.job_id}")
            except Exception:
                logging.exception(f"Cancelling real-time data due to exception")
                error_reporting.Client().report_exception()

                self._cancel_job(ib_client, streaming_id)

        bar_list = streaming_job.start_request(ib_client)

        self._real_time_bars[streaming_id] = bar_list
        logging.debug(f"_real_time_bars: {self._real_time_bars}")

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
            logging.info(f"Cancelled real time bars for contract {bar_list.contract}")
