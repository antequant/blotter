import asyncio
import concurrent.futures
import unittest
from typing import Awaitable, List, Tuple, Union

from ib_insync import IB

from blotter.ib_helpers import IBError, IBThread


class TestIBThread(unittest.TestCase):
    def setUp(self) -> None:
        self.loop = asyncio.get_event_loop()

        def _error_handler(error: Union[Exception, IBError]) -> None:
            self.fail(f"Exception thrown: {error}")

        self.thread = IBThread(IB(), _error_handler, self.loop)

    def _run_thread(self) -> None:
        with self.assertRaises(AssertionError):
            # Returning from this method is not normally supported, so catch the assertion that's thrown.
            self.thread.run_forever()

    def test_scheduling_coroutine(self) -> None:
        async def coro(client: IB) -> List[str]:
            self.assertEqual(asyncio.get_running_loop(), self.loop)
            return list(client.events)

        def concurrent_fn() -> int:
            events = self.thread.schedule(coro).result()
            self.assertIsNotNone(events)
            self.assertNotEqual(events, [])

            self.loop.call_soon_threadsafe(lambda: self.loop.stop())
            return len(events)

        future = concurrent.futures.ThreadPoolExecutor().submit(concurrent_fn)
        self._run_thread()
        self.assertGreater(future.result(), 0)

    def test_scheduling_awaitable(self) -> None:
        async def coro(client: IB) -> List[str]:
            self.assertEqual(asyncio.get_running_loop(), self.loop)
            return list(client.events)

        def concurrent_fn() -> int:
            # Scheduling a lambda which returns an Awaitable, instead of the coroutine itself.
            events = self.thread.schedule(lambda ib: coro(ib)).result()
            self.assertIsNotNone(events)
            self.assertNotEqual(events, [])

            self.loop.call_soon_threadsafe(lambda: self.loop.stop())
            return len(events)

        future = concurrent.futures.ThreadPoolExecutor().submit(concurrent_fn)
        self._run_thread()
        self.assertGreater(future.result(), 0)

    def test_using_client_too_early(self) -> None:
        async def coro(events: Tuple[str, ...]) -> List[str]:
            self.assertEqual(asyncio.get_running_loop(), self.loop)
            return list(events)

        # Ensures that accessing the IB client even before dispatch should be "safe."
        def too_early(client: IB) -> Awaitable[List[str]]:
            self.assertEqual(asyncio.get_running_loop(), self.loop)
            return coro(client.events)

        def concurrent_fn() -> int:
            events = self.thread.schedule(too_early).result()
            self.assertIsNotNone(events)
            self.assertNotEqual(events, [])

            self.loop.call_soon_threadsafe(lambda: self.loop.stop())
            return len(events)

        future = concurrent.futures.ThreadPoolExecutor().submit(concurrent_fn)
        self._run_thread()
        self.assertGreater(future.result(), 0)
