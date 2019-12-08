from decimal import Decimal

import ib_insync
from blotter.blotter_pb2 import (
    ContractSpecifier,
    Duration,
    LoadHistoricalDataRequest,
    StartRealTimeDataRequest,
)


def contract_from_specifier(specifier: ContractSpecifier) -> ib_insync.Contract:
    """
    Converts a ContractSpecifier into an ib_insync Contract object.
    
    This does not guarantee that the resulting Contract actually refers to a real security.
    """

    security_type_mapping = {
        ContractSpecifier.SecurityType.STOCK: "STK",
        ContractSpecifier.SecurityType.OPTION: "OPT",
        ContractSpecifier.SecurityType.FUTURE: "FUT",
        ContractSpecifier.SecurityType.INDEX: "IND",
        ContractSpecifier.SecurityType.FUTURES_OPTION: "FOP",
        ContractSpecifier.SecurityType.CASH: "CASH",
        ContractSpecifier.SecurityType.CFD: "CFD",
        ContractSpecifier.SecurityType.COMBO: "BAG",
        ContractSpecifier.SecurityType.WARRANT: "WAR",
        ContractSpecifier.SecurityType.BOND: "BOND",
        ContractSpecifier.SecurityType.COMMODITY: "CMDTY",
        ContractSpecifier.SecurityType.NEWS: "NEWS",
        ContractSpecifier.SecurityType.FUND: "FUND",
    }

    right_mapping = {
        ContractSpecifier.Right.UNSPECIFIED_RIGHT: "",
        ContractSpecifier.Right.PUT: "P",
        ContractSpecifier.Right.CALL: "C",
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


def duration_str(duration: Duration) -> str:
    """
    Converts a `Duration` into the string format expected by ib_insync.
    """

    time_unit_mapping = {
        Duration.TimeUnit.SECONDS: "S",
        Duration.TimeUnit.DAYS: "D",
        Duration.TimeUnit.WEEKS: "W",
        Duration.TimeUnit.MONTHS: "M",
        Duration.TimeUnit.YEARS: "Y",
    }

    return f"{duration.count} {time_unit_mapping[duration.unit]}"


def bar_size_str(bar_size: LoadHistoricalDataRequest.BarSize) -> str:
    """
    Converts a `BarSize` into the string format expected by ib_insync.
    """

    bar_size_mapping = {
        LoadHistoricalDataRequest.BarSize.ONE_SECOND: "1 secs",
        LoadHistoricalDataRequest.BarSize.FIVE_SECONDS: "5 secs",
        LoadHistoricalDataRequest.BarSize.TEN_SECONDS: "10 secs",
        LoadHistoricalDataRequest.BarSize.FIFTEEN_SECONDS: "15 secs",
        LoadHistoricalDataRequest.BarSize.THIRTY_SECONDS: "30 secs",
        LoadHistoricalDataRequest.BarSize.ONE_MINUTE: "1 min",
        LoadHistoricalDataRequest.BarSize.TWO_MINUTES: "2 mins",
        LoadHistoricalDataRequest.BarSize.THREE_MINUTES: "3 mins",
        LoadHistoricalDataRequest.BarSize.FIVE_MINUTES: "5 mins",
        LoadHistoricalDataRequest.BarSize.TEN_MINUTES: "10 mins",
        LoadHistoricalDataRequest.BarSize.FIFTEEN_MINUTES: "15 mins",
        LoadHistoricalDataRequest.BarSize.TWENTY_MINUTES: "20 mins",
        LoadHistoricalDataRequest.BarSize.THIRTY_MINUTES: "30 mins",
        LoadHistoricalDataRequest.BarSize.ONE_HOUR: "1 hour",
        LoadHistoricalDataRequest.BarSize.TWO_HOURS: "2 hours",
        LoadHistoricalDataRequest.BarSize.THREE_HOURS: "3 hours",
        LoadHistoricalDataRequest.BarSize.FOUR_HOURS: "4 hours",
        LoadHistoricalDataRequest.BarSize.EIGHT_HOURS: "8 hours",
        LoadHistoricalDataRequest.BarSize.ONE_DAY: "1 day",
        LoadHistoricalDataRequest.BarSize.ONE_WEEK: "1 week",
        LoadHistoricalDataRequest.BarSize.ONE_MONTH: "1 month",
    }

    return bar_size_mapping[bar_size]


def historical_bar_source_str(bar_source: LoadHistoricalDataRequest.BarSource) -> str:
    """
    Converts a `BarSource` into the string format expected by ib_insync for `whatToShow`.
    """

    return str(LoadHistoricalDataRequest.BarSource.Name(bar_source))


def real_time_bar_source_str(bar_source: StartRealTimeDataRequest.BarSource) -> str:
    """
    Converts a `BarSource` into the string format expected by ib_insync for `whatToShow`.
    """

    return str(StartRealTimeDataRequest.BarSource.Name(bar_source))
