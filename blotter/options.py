import logging
from typing import Iterable, List

import ib_insync
import pandas as pd
from google.cloud import bigquery

from blotter.blotter_pb2 import ContractSpecifier
from blotter.ib_helpers import qualify_contract_specifier
from blotter.upload import (
    TickersTableColumn,
    table_name_for_contract,
    upload_dataframe,
)


async def _look_up_options(
    ib_client: ib_insync.IB, underlying: ib_insync.Contract,
) -> List[ib_insync.Contract]:
    """
    Looks up all valid (non-expired) options contracts for the given contract specifier.
    """
    option_chains = await ib_client.reqSecDefOptParamsAsync(
        underlyingSymbol=underlying.symbol,
        futFopExchange=underlying.exchange if underlying.secType == "FOP" else "",
        underlyingSecType=underlying.secType,
        underlyingConId=underlying.conId,
    )

    logging.info(f"Loaded {len(option_chains)} option chains for {underlying}")

    option_contracts = (
        ib_insync.Option(
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

    logging.info(
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
    logging.info(f"Fetched {len(tickers)} tickers")

    df = pd.DataFrame.from_records(
        (
            {
                TickersTableColumn.SYMBOL: t.contract.localSymbol,
                TickersTableColumn.CONTRACT_ID: t.contract.conId,
                TickersTableColumn.TIMESTAMP: t.time,
                TickersTableColumn.OPEN: t.open,
                TickersTableColumn.HIGH: t.high,
                TickersTableColumn.LOW: t.low,
                TickersTableColumn.CLOSE: t.close,
                TickersTableColumn.VOLUME: t.volume,
                TickersTableColumn.AVERAGE_PRICE: t.vwap,
                TickersTableColumn.BID: t.bid,
                TickersTableColumn.BID_SIZE: t.bidSize,
                TickersTableColumn.ASK: t.ask,
                TickersTableColumn.ASK_SIZE: t.askSize,
                TickersTableColumn.LAST: t.last,
                TickersTableColumn.LAST_SIZE: t.lastSize,
            }
            for t in tickers
        )
    )

    logging.debug(f"Tickers DataFrame: {df}")
    return df


async def snapshot_options(
    ib_client: ib_insync.IB, underlying_specifier: ContractSpecifier,
) -> bigquery.LoadJob:
    """
    Uploads a snapshot of the current options chain for the given contract specifier.

    Returns a reference to the job that was started.
    """

    underlying = await qualify_contract_specifier(ib_client, underlying_specifier)
    contracts = await _look_up_options(ib_client, underlying)
    df = await _load_tickers_into_dataframe(ib_client, contracts)

    table_name = f"{table_name_for_contract(underlying)}_options"
    return upload_dataframe(table_name, df)
