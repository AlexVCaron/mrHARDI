import asyncio
import logging
import queue
import sys
from threading import Thread, Event


class ThreadedAsyncEntity:
    def __init__(self, main_loop=None, name="ThreadedAsyncEntity"):
        self._name = name
        self._done = asyncio.Future(loop=main_loop)
        self._ready = Event()
        self._thread = None

    def set_completed(self):
        asyncio.run_coroutine_threadsafe(
            self._completed(),
            loop=self._done.get_loop()
        )

    async def wait_for_completion(self):
        await self._done

    def start(self, *args, daemon=True, **kwargs):
        logger.debug("{} starting thread".format(self._name))
        self._thread = Thread(target=self._loop, daemon=daemon)
        self._thread.start()
        return self._ready

    def running(self):
        return self._async_loop.is_running()

    def has_started(self):
        return self._thread is not None

    def is_alive(self):
        return self._thread.is_alive()

    def _loop(self):
        logger.debug("{} starting async loop".format(self._name))
        self._async_loop = asyncio.new_event_loop()
        self._async_loop.set_debug(True)
        self._ready.set()
        logger.debug("{} async loop is running".format(self._name))
        self._async_loop.run_forever()
        self._async_loop.close()
        logger.debug("{} async loop closed".format(self._name))
        self.set_completed()

    def _close(self):
        self._async_loop.stop()

    async def _completed(self):
        self._done.set_result(True)


logger = logging.getLogger(ThreadedAsyncEntity.__name__)


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
