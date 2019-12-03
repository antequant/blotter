import asyncio
import concurrent.futures as futures
import logging
from typing import Any, Optional

import grpc

from blotter import blotter_pb2, blotter_pb2_grpc, model
import ib_insync


class Servicer(blotter_pb2_grpc.BlotterServicer):
    def __init__(self, ib_client: ib_insync.IB, eventLoop: asyncio.AbstractEventLoop):
        self._ib_client = ib_client
        self._loop = eventLoop
        super().__init__()

    # def LookUp(self, request: Any, context: Any) -> Any:
    #     async def _coroutine() -> int:
    #         contract = model.contract_from_lookup(request)

    #         logging.debug(f"Qualifying contract {contract}")
    #         await self._ib_client.qualify_contract_inplace(contract)
    #         logging.debug(f"Qualified contract: {contract}")

    #         return int(contract.conId)

    #     logging.debug(f"LookUp({request})")
    #     conId = asyncio.run_coroutine_threadsafe(_coroutine(), self._loop).result()
    #     if not conId:
    #         raise RuntimeError(
    #             f"Could not qualify contract <{request}> (it may be ambiguous)"
    #         )

    #     return blotter_pb2.Contract(contractID=conId)

    # def Subscribe(self, request: Any, context: Any) -> Any:
    #     pass


def start(
    port: int,
    ib_client: ib_insync.IB,
    eventLoop: Optional[asyncio.AbstractEventLoop] = None,
    executor: Optional[futures.ThreadPoolExecutor] = None,
) -> grpc.Server:
    if eventLoop is None:
        eventLoop = asyncio.get_running_loop()

    if executor is None:
        executor = futures.ThreadPoolExecutor()

    s = grpc.server(executor)
    blotter_pb2_grpc.add_BlotterServicer_to_server(Servicer(ib_client, eventLoop), s)
    s.add_insecure_port(f"[::]:{port}")
    s.start()

    return s
