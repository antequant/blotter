import logging
from typing import Dict, NewType

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

    _real_time_bars: Dict[StreamingID, ib_insync.RealTimeBarList]
    """Ongoing streaming data requests."""

    def __init__(self) -> None:
        self._real_time_bars = {}
        super().__init__()

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

        def _bars_updated(bars: ib_insync.RealTimeBarList, has_new_bar: bool) -> None:
            logging.debug(f"Received {len(bars)} bars (has_new_bar={has_new_bar})")

            if not bars or not has_new_bar:
                return

            try:
                df = ib_insync.util.df(bars)

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
