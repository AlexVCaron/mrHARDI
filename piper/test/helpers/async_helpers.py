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
