import asyncio
import concurrent.futures
from typing import Awaitable, Callable, NoReturn, TypeVar

from blotter import blotter_pb2, request_helpers
from ib_insync import IB, Contract


async def qualify_contract_specifier(
    ib_client: IB, specifier: blotter_pb2.ContractSpecifier
) -> Contract:
    contract = request_helpers.contract_from_specifier(specifier)
    await ib_client.qualifyContractsAsync(contract)

    return contract


_T = TypeVar("_T")


class IBThread:
    """
    Abstracts over the ib_insync client and its attachment to a specific thread/event loop.

    ib_insync uses the asyncio framework for multitasking, and is not thread-aware. As a result, code which is actually "concurrent," in the sense of the `concurrent` module, needs to be careful to always invoke `IB` on the event loop it expects to be attached to. `IBThread` helps enforce this.
    """

    def __init__(
        self, client: IB, loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
    ):
        self._client = client
        self._loop = loop
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

    @property
    def client_unsafe(self) -> IB:
        return self._client
