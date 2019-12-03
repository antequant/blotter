import asyncio
import concurrent.futures
import grpc

from typing import Any, TypeVar, Union, overload


def grpc_future_to_concurrent_future(gf: grpc.Future) -> concurrent.futures.Future[Any]:
    cf: concurrent.futures.Future[Any] = concurrent.futures.Future()

    def gf_terminated(gf: grpc.Future) -> None:
        if gf.cancelled():
            cf.cancel()
            return

        try:
            result = gf.result(timeout=0)
            cf.set_result(result)
        except Exception as err:
            cf.set_exception(err)

    if cf.set_running_or_notify_cancel():
        gf.add_done_callback(gf_terminated)
    else:
        gf.cancel()

    return cf


_T = TypeVar("_T")


@overload
def future_to_aio_future(
    f: concurrent.futures.Future[_T], loop: asyncio.AbstractEventLoop
) -> asyncio.Future[_T]:
    pass


@overload
def future_to_aio_future(
    f: asyncio.Future[_T], loop: asyncio.AbstractEventLoop
) -> asyncio.Future[_T]:
    pass


@overload
def future_to_aio_future(
    f: grpc.Future, loop: asyncio.AbstractEventLoop
) -> asyncio.Future[Any]:
    pass


def future_to_aio_future(
    f: Union[concurrent.futures.Future[Any], asyncio.Future[Any], grpc.Future],
    loop: asyncio.AbstractEventLoop,
) -> asyncio.Future[Any]:
    if isinstance(f, grpc.Future):
        return future_to_aio_future(grpc_future_to_concurrent_future(f), loop)
    elif isinstance(f, asyncio.Future):
        return f
    else:
        # HACK: This method definitely supports a `loop` argument, but mypy
        # doesn't think so.
        return asyncio.wrap_future(f, loop=loop)  # type: ignore
