from typing import List
import logging

import ib_insync

from blotter.blotter_pb2 import ContractSpecifier
from blotter.ib_helpers import qualify_contract_specifier


async def fetch_option_chains(
    ib_client: ib_insync.IB, contract_specifier: ContractSpecifier
) -> List[ib_insync.Ticker]:
    underlying = await qualify_contract_specifier(ib_client, contract_specifier)
    option_chains = await ib_client.reqSecDefOptParamsAsync(
        underlyingSymbol=underlying.symbol,
        futFopExchange=underlying.exchange if underlying.secType == "FOP" else "",
        underlyingSecType=underlying.secType,
        underlyingConId=underlying.conId,
    )

    logging.debug(f"Loaded {len(option_chains)} option chains for {contract_specifier}")

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

    logging.debug(
        f"Qualified {len(qualified_contracts)} options contracts for {contract_specifier}"
    )

    tickers = await ib_client.reqTickersAsync(
        *qualified_contracts, regulatorySnapshot=False
    )

    logging.debug(
        f"Fetched {len(tickers)} tickers for options contraints for {contract_specifier}"
    )

    return tickers