from datetime import timedelta
from logging import getLogger
from typing import List

from google.cloud import bigquery

import ib_insync
from blotter.blotter_pb2 import ContractSpecifier
from gcloud_service.error_handler import ErrorHandlerConfiguration
from blotter.ib_helpers import qualify_contract_specifier
from blotter.polling import PollingID, PollingManager
from blotter.tickers import load_tickers_into_dataframe
from blotter.upload import table_name_for_contract, upload_dataframe

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


def _table_name_for_options(underlying: ib_insync.Contract) -> str:
    """
    Determines the appropriate BigQuery table name to use for options data associated with the given underlying.
    """

    return f"{table_name_for_contract(underlying)}_options"


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
    df = await load_tickers_into_dataframe(ib_client, contracts)
    return upload_dataframe(_table_name_for_options(underlying), df, error_handler)


async def start_polling_options(
    polling_manager: PollingManager,
    polling_interval: timedelta,
    ib_client: ib_insync.IB,
    underlying_specifier: ContractSpecifier,
) -> PollingID:
    """
    Loads the options chain for the given contract specifier, then starts polling for market data on each options contract on the provided interval.

    Returns the ID of the polling job.
    """

    underlying = await qualify_contract_specifier(ib_client, underlying_specifier)
    contracts = await look_up_options(ib_client, underlying)
    return await polling_manager.start_polling(
        ib_client,
        contracts,
        polling_interval=polling_interval,
        upload_table_name=_table_name_for_options(underlying),
    )
