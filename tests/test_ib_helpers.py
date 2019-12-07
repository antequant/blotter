import asyncio
import concurrent.futures
import unittest
from typing import List

from ib_insync import IB

from blotter.ib_helpers import IBThread


class TestIBThread(unittest.TestCase):
    def setUp(self) -> None:
        self.loop = asyncio.get_event_loop()
        self.thread = IBThread(IB(), self.loop)

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

        with self.assertRaises(AssertionError):
            # Returning from this method is not normally supported, so catch the assertion that's thrown.
            self.thread.run_forever()

        self.assertGreater(future.result(), 0)
