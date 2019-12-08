import asyncio
import logging
import math
from datetime import timedelta
from typing import Dict, NewType, Optional

import ib_insync
import pandas as pd
from blotter.blotter_pb2 import ContractSpecifier
from blotter.ib_helpers import qualify_contract_specifier
from blotter.upload import TableColumn, table_name_for_contract, upload_dataframe
from google.cloud import error_reporting

StreamingID = NewType("StreamingID", str)
"""A unique ID for ongoing market data streaming."""


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

    _real_time_bars: Dict[StreamingID, ib_insync.RealTimeBarList]
    """Ongoing streaming data requests."""

    def __init__(self, batch_size: int = StreamingManager.preferred_batch_size()) -> None:
        self._real_time_bars = {}
        self._batch_size = batch_size
        super().__init__()

    @classmethod
    def preferred_batch_size(cls) -> int:
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

            if bar_count < self._batch_size:
                logging.debug(
                    f"Skipping upload because bar count {bar_count} is less than batch size {self._batch_size}"
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

                ib_client.cancelRealTimeBars(bars)

                streaming_id = StreamingID(str(bars.reqId))
                if streaming_id in self._real_time_bars:
                    del self._real_time_bars[streaming_id]

        con = await qualify_contract_specifier(ib_client, contract_specifier)

        bar_list = ib_client.reqRealTimeBars(
            contract=con,
            barSize=5,
            whatToShow=bar_source,
            useRTH=regular_trading_hours_only,
        )

        streaming_id = StreamingID(str(bar_list.reqId))
        if streaming_id in self._real_time_bars:
            logging.error(
                f'Unexpectedly found "{streaming_id}" already in tracked bars: {self._real_time_bars}'
            )

        self._real_time_bars[streaming_id] = bar_list
        logging.debug(f"_real_time_bars: {self._real_time_bars}")

        bar_list.updateEvent += _bars_updated
        return streaming_id

    async def cancel_stream(
        self, ib_client: ib_insync.IB, streaming_id: StreamingID
    ) -> None:
        """
        Cancels a previous streaming request, identified by `streaming_id`.

        If the data is no longer streaming, nothing happens.
        """

        logging.debug(f"_real_time_bars: {self._real_time_bars}")

        bar_list = self._real_time_bars.pop(streaming_id, None)
        if bar_list is None:
            return

        ib_client.cancelRealTimeBars(bar_list)
        logging.info(f"Cancelled real time bars for contract {bar_list.contract}")
