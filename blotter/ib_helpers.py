import asyncio
import concurrent.futures
import math
from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    List,
    NamedTuple,
    NoReturn,
    Optional,
    TypeVar,
    Union,
    cast,
)

import ib_insync.util
import pandas as pd
from ib_insync import IB, Contract, ContractDetails, Ticker

from blotter import blotter_pb2, request_helpers


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
    return cast(Dict[str, Any], contract.dict())


def deserialize_contract(d: Dict[str, Any]) -> Contract:
    return Contract(**d)


_Num = TypeVar("_Num", float, Decimal)


def sanitize_price(
    price: Optional[_Num],
    can_be_negative: bool,
    count: Union[int, float, Decimal, None] = None,
) -> Optional[_Num]:
    """
    Attempts to sanitize away different variations of "invalid" yielded by IB APIs and elsewhere.

    Returns a sanitized number, or `None` if the number was determined to be invalid.
    """

    if price is None or count == 0:
        return None

    if isinstance(price, Decimal):
        if not price.is_finite():
            return None
    elif not math.isfinite(price):
        return None

    if price == 0:
        return None
    elif price < 0 and not can_be_negative:
        return None

    return price


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
            if errorCode == 200:
                # "No security definition has been found" error.
                # This will occur a lot if we're speculatively qualifying contracts, so just filter it out.
                return
            elif errorCode == 0 and "Warning: Approaching max rate" in errorString:
                # Rate limiting warning. Don't need to record this.
                return

            is_warning = (
                (errorCode >= 1100 and errorCode < 2000)
                or (errorCode >= 2100 and errorCode < 3000)
                or "Warning:" in errorString
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
