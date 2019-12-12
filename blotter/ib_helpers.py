import asyncio
import concurrent.futures
import logging
from dataclasses import dataclass
from typing import (
    Any, Awaitable, Callable, Dict, Iterable, List, NamedTuple, NoReturn,
    Optional, TypeVar, Union)

import ib_insync.util
import pandas as pd
from ib_insync import IB, Contract, ContractDetails, Ticker

from blotter import blotter_pb2, request_helpers
from blotter.upload import TableColumn


@dataclass(frozen=True)
class AmbiguousContractError(Exception):
    """
    Thrown when a contract specifier cannot be disambiguated to a single contract.
    """

    specifier: blotter_pb2.ContractSpecifier
    """The provided contract specifier that was ambiguous."""

    possible_contracts: List[ContractDetails]
    """Details for possible contracts the specifier could be referring to."""

    def __str__(self) -> str:
        return f"{type(self)}: Contract specifier {self.specifier} is ambiguous: {self.possible_contracts}"


async def qualify_contract_specifier(
    ib_client: IB, specifier: blotter_pb2.ContractSpecifier
) -> Contract:
    """
    Determines the most likely contract that corresponds to the given description.
    """

    contract = request_helpers.contract_from_specifier(specifier)

    result = await ib_client.qualifyContractsAsync(contract)
    if not result:
        # Would prefer to use this directly in the first place, but unfortunately qualifyContracts*() has some special fixup logic that isn't generalized here.
        details = await ib_client.reqContractDetailsAsync(contract)
        raise AmbiguousContractError(specifier=specifier, possible_contracts=details)

    return contract


def serialize_contract(contract: Contract) -> Dict[str, Any]:
    return {key: getattr(contract, key) for key in Contract.__slots__}


def deserialize_contract(d: Dict[str, Any]) -> Contract:
    return Contract(**d)


def tickers_to_dataframe(tickers: Iterable[Ticker]) -> pd.DataFrame:
    """
    Transforms `ib_insync.Ticker` fields into a pandas DataFrame. The `Ticker.contract` object is unpacked into multiple columns that help uniquely (and human-readably) identify the contract.
    """

    original_df = ib_insync.util.df(tickers)
    df = original_df.apply(
        lambda row: pd.Series(
            (row["contract"].conId, row["contract"].localSymbol),
            index=["contractId", "symbol"],
        ),
        axis=1,
        result_type="expand",
    )

    return df.join(original_df.drop(columns=["contract"]))

async def load_tickers_into_dataframe(
    ib_client: ib_insync.IB, contracts: Iterable[ib_insync.Contract]
) -> pd.DataFrame:
    """
    Requests snapshot tickers for all of the given contracts.

    Returns a DataFrame with all tickers as rows.
    """

    tickers = await ib_client.reqTickersAsync(*contracts, regulatorySnapshot=False)
    logging.debug(f"Fetched {len(tickers)} tickers")

    df = tickers_to_dataframe(tickers).rename(
        columns={
            "time": TableColumn.TIMESTAMP,
            "open": TableColumn.OPEN,
            "high": TableColumn.HIGH,
            "low": TableColumn.LOW,
            "close": TableColumn.CLOSE,
            "volume": TableColumn.VOLUME,
            "vwap": TableColumn.AVERAGE_PRICE,
        }
    )

    logging.debug(f"Tickers DataFrame: {df}")
    return df


_T = TypeVar("_T")


@dataclass(frozen=True)
class IBWarning(UserWarning):
    """
    Represents a warning or informative message originating in TWS.
    """

    request_id: int
    """The prior request that this warning is concerning."""

    error_code: int
    """The TWS error code: https://interactivebrokers.github.io/tws-api/message_codes.html"""

    error_message: str
    """The TWS error message."""

    contract: Optional[Contract]
    """The contract this warning is concerning, if applicable."""

    def __str__(self) -> str:
        msg = f"{type(self)}: {self.error_code} concerning request {self.request_id}: {self.error_message}"
        if self.contract:
            msg += f" (contract: {self.contract})"

        return msg


@dataclass(frozen=True)
class IBError(Exception):
    """
    Represents a hard error originating in TWS.
    """

    request_id: int
    """The prior request that this error is concerning."""

    error_code: int
    """The TWS error code: https://interactivebrokers.github.io/tws-api/message_codes.html"""

    error_message: str
    """The TWS error message."""

    contract: Optional[Contract]
    """The contract this error is concerning, if applicable."""

    def __str__(self) -> str:
        msg = f"{type(self)}: {self.error_code} concerning request {self.request_id}: {self.error_message}"
        if self.contract:
            msg += f" (contract: {self.contract})"

        return msg


@dataclass(frozen=True)
class DataError(Exception):
    """
    Thrown to indicate unexpected data that the application does not know how to handle.
    """

    message: str

    def __str__(self) -> str:
        return f"{type(self)}: {self.message}"


class IBThread:
    """
    Abstracts over the ib_insync client and its attachment to a specific thread/event loop.

    ib_insync uses the asyncio framework for multitasking, and is not thread-aware. As a result, code which is actually "concurrent," in the sense of the `concurrent` module, needs to be careful to always invoke `IB` on the event loop it expects to be attached to. `IBThread` helps enforce this.
    """

    def __init__(
        self,
        client: IB,
        error_handler: Callable[[Union[Exception, IBError]], None],
        loop: asyncio.AbstractEventLoop = asyncio.get_event_loop(),
    ):
        self._client = client
        self._loop = loop

        def _ib_error_event_handler(
            reqId: int, errorCode: int, errorString: str, contract: Optional[Contract]
        ) -> None:
            is_warning = (errorCode >= 1100 and errorCode < 2000) or (
                errorCode >= 2100 and errorCode < 3000
            )

            err = (IBWarning if is_warning else IBError)(
                request_id=reqId,
                error_code=errorCode,
                error_message=errorString,
                contract=contract,
            )

            error_handler(err)

        def _install_error_handlers() -> None:
            ib_insync.util.globalErrorEvent += error_handler
            self._client.errorEvent += _ib_error_event_handler

        self._loop.call_soon_threadsafe(_install_error_handlers)

        super().__init__()

    def run_forever(self) -> NoReturn:
        """
        Takes over the current thread to run the event loop, and all ib_insync operations upon it.
        """
        assert (
            asyncio.get_event_loop() == self._loop
        ), "IBThread.run_forever() should be invoked on the event loop it is attached to"

        self._client.run()
        assert False, "IB.run() should never return"

    def schedule(
        self, fn: Callable[[IB], Awaitable[_T]]
    ) -> "concurrent.futures.Future[_T]":
        """
        Schedules an async operation on the IB event loop, providing the client.
        """

        # This is formally a coroutine to asyncio, so should help ensure that we run `fn` only on the event loop, as opposed to the calling thread of `schedule()` (but ihavenoideawhatimdoing.gif)
        async def invoke() -> _T:
            return await fn(self._client)

        return asyncio.run_coroutine_threadsafe(invoke(), self._loop)
