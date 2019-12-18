import logging
from datetime import datetime
from typing import Dict, Iterable, Union

import pandas as pd

import ib_insync
from blotter.ib_helpers import sanitize_price
from blotter.upload import TickersTableColumn

logger = logging.getLogger(__name__)


async def load_tickers_into_dataframe(
    ib_client: ib_insync.IB, contracts: Iterable[ib_insync.Contract]
) -> pd.DataFrame:
    """
    Requests snapshot tickers for all of the given contracts.

    Returns a DataFrame with all tickers as rows, and columns matching the `TickersTableColumn` enum.
    """

    tickers = await ib_client.reqTickersAsync(*contracts, regulatorySnapshot=False)
    logger.info(f"Fetched {len(tickers)} tickers")

    def _ticker_dict(
        t: ib_insync.Ticker,
    ) -> Dict[str, Union[str, datetime, float, None]]:  # FIXME
        assert t.contract is not None

        price_is_negative = t.close < 0

        return {
            TickersTableColumn.SYMBOL.value: t.contract.localSymbol,
            TickersTableColumn.CONTRACT_ID.value: t.contract.conId,
            TickersTableColumn.TIMESTAMP.value: t.time,
            TickersTableColumn.HIGH.value: sanitize_price(
                t.high, can_be_negative=price_is_negative
            ),
            TickersTableColumn.LOW.value: sanitize_price(
                t.low, can_be_negative=price_is_negative
            ),
            TickersTableColumn.CLOSE.value: t.close,
            TickersTableColumn.VOLUME.value: t.volume,
            TickersTableColumn.BID.value: sanitize_price(
                t.bid, can_be_negative=price_is_negative, count=t.bidSize
            ),
            TickersTableColumn.BID_SIZE.value: t.bidSize,
            TickersTableColumn.ASK.value: sanitize_price(
                t.ask, can_be_negative=price_is_negative, count=t.askSize
            ),
            TickersTableColumn.ASK_SIZE.value: t.askSize,
            TickersTableColumn.LAST.value: sanitize_price(
                t.last, can_be_negative=price_is_negative, count=t.lastSize
            ),
            TickersTableColumn.LAST_SIZE.value: t.lastSize,
        }

    df = pd.DataFrame.from_records(
        (_ticker_dict(t) for t in tickers if t.time and t.contract)
    )

    df = df.astype(
        {
            TickersTableColumn.HIGH.value: "float64",
            TickersTableColumn.LOW.value: "float64",
            TickersTableColumn.CLOSE.value: "float64",
            TickersTableColumn.VOLUME.value: "float64",
            TickersTableColumn.BID.value: "float64",
            TickersTableColumn.BID_SIZE.value: "float64",
            TickersTableColumn.ASK.value: "float64",
            TickersTableColumn.ASK_SIZE.value: "float64",
            TickersTableColumn.LAST.value: "float64",
            TickersTableColumn.LAST_SIZE.value: "float64",
        }
    )

    df[TickersTableColumn.TIMESTAMP.value] = df[
        TickersTableColumn.TIMESTAMP.value
    ].dt.round("ms")

    logger.debug(f"Tickers DataFrame: {df}")
    return df
