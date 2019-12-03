from blotter import blotter_pb2
from decimal import Decimal
import ib_insync

from typing import Any

_ContractSpecifier: Any = blotter_pb2.ContractSpecifier

def contract_from_lookup(lookup: Any) -> ib_insync.Contract:
    """Converts a ContractLookup message into an ib_insync Contract object."""

    _security_type_mapping = {
        _ContractSpecifier.SecurityType.STOCK: "STK",
        _ContractSpecifier.SecurityType.OPTION: "OPT",
        _ContractSpecifier.SecurityType.FUTURE: "FUT",
        _ContractSpecifier.SecurityType.INDEX: "IND",
        _ContractSpecifier.SecurityType.FUTURES_OPTION: "FOP",
        _ContractSpecifier.SecurityType.CASH: "CASH",
        _ContractSpecifier.SecurityType.CFD: "CFD",
        _ContractSpecifier.SecurityType.COMBO: "BAG",
        _ContractSpecifier.SecurityType.WARRANT: "WAR",
        _ContractSpecifier.SecurityType.BOND: "BOND",
        _ContractSpecifier.SecurityType.COMMODITY: "CMDTY",
        _ContractSpecifier.SecurityType.NEWS: "NEWS",
        _ContractSpecifier.SecurityType.FUND: "FUND",
    }

    _right_mapping = {
        _ContractSpecifier.Right.UNSET: "",
        _ContractSpecifier.Right.PUT: "P",
        _ContractSpecifier.Right.CALL: "C",
    }

    return ib_insync.Contract(
        symbol=lookup.symbol,
        secType=_security_type_mapping[lookup.securityType],
        lastTradeDateOrContractMonth=lookup.lastTradeDateOrContractMonth,
        strike=Decimal(lookup.strike) if lookup.strike else 0.0,
        right=_right_mapping[lookup.right],
        multiplier=lookup.multiplier,
        exchange=lookup.exchange,
        currency=lookup.currency,
        localSymbol=lookup.localSymbol,
        primaryExchange=lookup.primaryExchange,
        tradingClass=lookup.tradingClass,
        includeExpired=lookup.includeExpired,
    )
