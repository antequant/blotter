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
    local_symbol: str

    contract_id: int

    primary_exchange: str
    """Needed to disambiguate SMART contract IDs."""

    bar_size: int
    what_to_show: str
    use_regular_trading_hours: bool

    @classmethod
    def create_from_bar_list(
        cls, bar_list: ib_insync.RealTimeBarList
    ) -> "_StreamingJob":
        return cls(
            local_symbol=bar_list.contract.localSymbol,
            contract_id=bar_list.contract.conId,
            primary_exchange=bar_list.contract.primaryExchange,
            bar_size=bar_list.barSize,
            what_to_show=bar_list.whatToShow,
            use_regular_trading_hours=bar_list.useRTH,
        )

    def start_request(self, ib_client: ib_insync.IB) -> ib_insync.RealTimeBarList:
        return ib_client.reqRealTimeBars(
            ib_insync.Contract(
                conId=self.contract_id,
                primaryExchange=self.primary_exchange,
                localSymbol=self.local_symbol,
            ),
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
        batch_size: int = DEFAULT_BATCH_SIZE,
        batch_timeout: timedelta = DEFAULT_BATCH_LATENCY,
    ) -> None:
        assert batch_size >= 1, f"Batch size {batch_size} should be a natural number"
        assert (
            batch_timeout.total_seconds() >= 1
        ), f"Batch timeout {batch_timeout} should be at least 1 second"

        if batch_size * self._BAR_SIZE > batch_timeout:
            logging.warn(
                f"Batch size {batch_size} would take {batch_size * self._BAR_SIZE} to collect, greater than timeout {batch_timeout}"
            )

        self._real_time_bars = {}
        self._firestore_db = firestore.Client()
        self._batch_size = batch_size
        self._batch_timeout = batch_timeout
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

            streaming_id = StreamingID(doc.id)

            async def _resume_job(ib_client: ib_insync.IB) -> None:
                try:
                    await self._start_job(ib_client, streaming_job, streaming_id)
                except Exception:
                    logging.exception(f"Failed to resume streaming job {streaming_id}")

            logging.info(
                f"Resuming streaming for {streaming_job} with ID {streaming_id}"
            )
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
            primary_exchange=contract.primaryExchange,
            local_symbol=contract.localSymbol,
            bar_size=5,
            what_to_show=bar_source,
            use_regular_trading_hours=regular_trading_hours_only,
        )

        streaming_id = self._record_job_in_firestore(streaming_job)
        logging.info(f"Starting streaming for {contract} with ID {streaming_id}")

        await self._start_job(ib_client, streaming_job, streaming_id)
        return streaming_id

    async def _start_job(
        self,
        ib_client: ib_insync.IB,
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

            if not timer_fired and bar_count < self._batch_size:
                logging.debug(
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

                    logging.debug(f"Scheduled batch flush after {self._batch_timeout}")

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
