import sys
import queue
from threading import Thread


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
