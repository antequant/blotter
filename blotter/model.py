from blotter import blotter_pb2
from decimal import Decimal
import ib_insync

from typing import Any

_ContractSpecifier: Any = blotter_pb2.ContractSpecifier
_Duration: Any = blotter_pb2.Duration
_LoadHistoricalDataRequest: Any = blotter_pb2.LoadHistoricalDataRequest
_StartRealTimeDataRequest: Any = blotter_pb2.StartRealTimeDataRequest


def contract_from_specifier(specifier: Any) -> ib_insync.Contract:
    """Converts a ContractLookup message into an ib_insync Contract object."""

    security_type_mapping = {
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

    right_mapping = {
        _ContractSpecifier.Right.UNSPECIFIED_RIGHT: "",
        _ContractSpecifier.Right.PUT: "P",
        _ContractSpecifier.Right.CALL: "C",
    }

    return ib_insync.Contract(
        symbol=specifier.symbol,
        secType=security_type_mapping[specifier.securityType],
        lastTradeDateOrContractMonth=specifier.lastTradeDateOrContractMonth,
        strike=Decimal(specifier.strike) if specifier.strike else 0.0,
        right=right_mapping[specifier.right],
        multiplier=specifier.multiplier,
        exchange=specifier.exchange,
        currency=specifier.currency,
        localSymbol=specifier.localSymbol,
        primaryExchange=specifier.primaryExchange,
        tradingClass=specifier.tradingClass,
        includeExpired=specifier.includeExpired,
    )


def duration_str(duration: Any) -> str:
    time_unit_mapping = {
        _Duration.TimeUnit.SECONDS: "S",
        _Duration.TimeUnit.DAYS: "D",
        _Duration.TimeUnit.WEEKS: "W",
        _Duration.TimeUnit.MONTHS: "M",
        _Duration.TimeUnit.YEARS: "Y",
    }

    return f"{duration.count} {time_unit_mapping[duration.unit]}"


def bar_size_str(bar_size: Any) -> str:
    bar_size_mapping = {
        _LoadHistoricalDataRequest.BarSize.ONE_SECOND: "1 secs",
        _LoadHistoricalDataRequest.BarSize.FIVE_SECONDS: "5 secs",
        _LoadHistoricalDataRequest.BarSize.TEN_SECONDS: "10 secs",
        _LoadHistoricalDataRequest.BarSize.FIFTEEN_SECONDS: "15 secs",
        _LoadHistoricalDataRequest.BarSize.THIRTY_SECONDS: "30 secs",
        _LoadHistoricalDataRequest.BarSize.ONE_MINUTE: "1 min",
        _LoadHistoricalDataRequest.BarSize.TWO_MINUTES: "2 mins",
        _LoadHistoricalDataRequest.BarSize.THREE_MINUTES: "3 mins",
        _LoadHistoricalDataRequest.BarSize.FIVE_MINUTES: "5 mins",
        _LoadHistoricalDataRequest.BarSize.TEN_MINUTES: "10 mins",
        _LoadHistoricalDataRequest.BarSize.FIFTEEN_MINUTES: "15 mins",
        _LoadHistoricalDataRequest.BarSize.TWENTY_MINUTES: "20 mins",
        _LoadHistoricalDataRequest.BarSize.THIRTY_MINUTES: "30 mins",
        _LoadHistoricalDataRequest.BarSize.ONE_HOUR: "1 hour",
        _LoadHistoricalDataRequest.BarSize.TWO_HOURS: "2 hours",
        _LoadHistoricalDataRequest.BarSize.THREE_HOURS: "3 hours",
        _LoadHistoricalDataRequest.BarSize.FOUR_HOURS: "4 hours",
        _LoadHistoricalDataRequest.BarSize.EIGHT_HOURS: "8 hours",
        _LoadHistoricalDataRequest.BarSize.ONE_DAY: "1 day",
        _LoadHistoricalDataRequest.BarSize.ONE_WEEK: "1 week",
        _LoadHistoricalDataRequest.BarSize.ONE_MONTH: "1 month",
    }

    return bar_size_mapping[bar_size]


def historical_bar_source_str(bar_source: Any) -> str:
    return str(_LoadHistoricalDataRequest.BarSource.Name(bar_source))


def real_time_bar_source_str(bar_source: Any) -> str:
    return str(_StartRealTimeDataRequest.BarSource.Name(bar_source))

