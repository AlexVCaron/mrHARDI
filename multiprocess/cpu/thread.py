import asyncio
import sys
import queue
from asyncio import Future
from threading import Thread


class ThreadedAsyncEntity:
    def __init__(self, main_loop):
        self._future = None
        self._ready = Future(loop=main_loop)
        self._thread = None
        self._async_loop = None

    def set_completed(self, result):
        self._future.set_result(result)

    def _start_async_loop(self):
        self._thread = Thread(target=self._loop)
        self._thread.start()

    def _loop(self):
        self._async_loop = asyncio.new_event_loop()
        self._async_loop.set_debug(True)
        self._future = Future(loop=self._async_loop)
        self._ready.set_result(True)
        self._async_loop.run_forever()

    def _close(self, *args, **kwargs):
        self._future.set_result(True)
        self._async_loop.stop()


class ThreadManager(queue.Queue):
    def __init__(self, thread, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._thread = thread

    def get_thread(self):
        return self._thread

    def join_thread(self, timeout=None):
        self._thread.join(timeout)


class ManagedThread(Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ex_bucket = ThreadManager(self)

    def get_exception_bucket(self):
        return self._ex_bucket

    def run(self):
        try:
            super().run()
        except Exception:
            self._ex_bucket.put(sys.exc_info())

    def __enter__(self):
        self.start()
        return self.get_exception_bucket()

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(exc_type)
        print(exc_val)
        print(exc_tb)
