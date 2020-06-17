import asyncio
from functools import partial


def async_close_channels_callback(sub_shutdown_fn, async_loop, close_cnd=None):
    def close_callback(*args, fn, cnd, loop):
        print("Closing")
        shutdown = loop.create_task(fn())
        if cnd:
            shutdown.add_done_callback(lambda *a: cnd.set())
        print("Close done")

    return partial(
        close_callback, fn=sub_shutdown_fn, cnd=close_cnd, loop=async_loop
    )


def set_future_in_loop(future, result):
    asyncio.run_coroutine_threadsafe(
        _set_future(result, future),
        future.get_loop()
    )


def cancel_future_in_loop(future):
    asyncio.run_coroutine_threadsafe(
        _cancel_future(future),
        future.get_loop()
    ).result()


async def _set_future(result, future):
    future.set_result(result)


async def _cancel_future(future):
    future.cancel()
