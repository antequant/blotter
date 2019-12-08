import asyncio
import concurrent.futures
from typing import Awaitable, Callable, NoReturn, Optional, TypeVar, Union

from blotter import blotter_pb2, request_helpers
from ib_insync import IB, Contract
import ib_insync.util


async def qualify_contract_specifier(
    ib_client: IB, specifier: blotter_pb2.ContractSpecifier
) -> Contract:
    """
    Determines the most likely contract that corresponds to the given description.
    """

    contract = request_helpers.contract_from_specifier(specifier)

    result = await ib_client.qualifyContractsAsync(contract)
    if not result:
        raise RuntimeError(
            f"Could not qualify contract {contract} from specifier {specifier}"
        )

    return contract


_T = TypeVar("_T")


class IBError(Exception):
    """
    Represents an error originating in TWS.
    """

    def __init__(
        self,
        request_id: int,
        error_code: int,
        error_message: str,
        contract: Optional[Contract],
    ):
        self.request_id = request_id
        """The prior request that this error is concerning."""

        self.error_code = error_code
        """The TWS error code: https://interactivebrokers.github.io/tws-api/message_codes.html"""

        self.error_message = error_message
        """The TWS error message."""

        self.contract = contract
        """The contract this error is concerning, if applicable."""

        super().__init__()

    def __str__(self) -> str:
        msg = f"Error code {self.error_code} concerning request {self.request_id}: {self.error_message}"
        if self.contract:
            msg += f" (contract: {self.contract})"

        return msg

    def __repr__(self) -> str:
        return f"IBError(request_id={self.request_id!r}, error_code={self.error_code!r}, error_message={self.error_message!r}, contract={self.contract!r})"


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
            error_handler(
                IBError(
                    request_id=reqId,
                    error_code=errorCode,
                    error_message=errorString,
                    contract=contract,
                )
            )

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
