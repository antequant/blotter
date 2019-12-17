from datetime import datetime
from logging import getLogger
from typing import Any, Dict, Iterable, List, Union, cast

import ib_insync
import pandas as pd
from google.cloud import bigquery

from blotter.blotter_pb2 import ContractSpecifier
from blotter.error_handling import ErrorHandlerConfiguration
from blotter.ib_helpers import qualify_contract_specifier, sanitize_price
from blotter.upload import TickersTableColumn, table_name_for_contract, upload_dataframe

logger = getLogger(__name__)


async def look_up_options(
    ib_client: ib_insync.IB, underlying: ib_insync.Contract,
) -> List[ib_insync.Contract]:
    """
    Looks up all valid (non-expired) options contracts for the given contract specifier.
    """
    option_chains = await ib_client.reqSecDefOptParamsAsync(
        underlyingSymbol=underlying.symbol,
        futFopExchange=underlying.exchange if underlying.secType == "FUT" else "",
        underlyingSecType=underlying.secType,
        underlyingConId=underlying.conId,
    )

    logger.info(f"Loaded {len(option_chains)} option chains for {underlying}")

    option_contracts = (
        (ib_insync.FuturesOption if underlying.secType == "FUT" else ib_insync.Option)(
            symbol=underlying.symbol,
            lastTradeDateOrContractMonth=expiration,
            strike=strike,
            right=right,
            exchange=chain.exchange,
            multiplier=chain.multiplier,
            tradingClass=chain.tradingClass,
        )
        for chain in option_chains
        if chain.exchange == underlying.exchange
        for expiration in chain.expirations
        for strike in chain.strikes
        for right in ["P", "C"]
    )

    qualified_contracts = await ib_client.qualifyContractsAsync(*option_contracts)

    logger.info(
        f"Qualified {len(qualified_contracts)} options contracts for {underlying}"
    )

    return qualified_contracts


async def _load_tickers_into_dataframe(
    ib_client: ib_insync.IB, contracts: Iterable[ib_insync.Contract]
) -> pd.DataFrame:
    """
    Requests snapshot tickers for all of the given contracts.

    Returns a DataFrame with all tickers as rows.
    """

    tickers = await ib_client.reqTickersAsync(*contracts, regulatorySnapshot=False)
    logger.info(f"Fetched {len(tickers)} tickers")

    def _ticker_dict(t: Any,) -> Dict[str, Union[str, datetime, float, None]]:  # FIXME
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
        (
            _ticker_dict(t)
            for t in tickers
            if cast(Any, t).time and cast(Any, t).contract
        )
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


async def snapshot_options(
    ib_client: ib_insync.IB,
    underlying_specifier: ContractSpecifier,
    error_handler: ErrorHandlerConfiguration,
) -> bigquery.LoadJob:
    """
    Uploads a snapshot of the current options chain for the given contract specifier.

    Returns a reference to the job that was started.
    """

    underlying = await qualify_contract_specifier(ib_client, underlying_specifier)
    contracts = await look_up_options(ib_client, underlying)
    df = await _load_tickers_into_dataframe(ib_client, contracts)

    table_name = f"{table_name_for_contract(underlying)}_options"
    return upload_dataframe(table_name, df, error_handler)
