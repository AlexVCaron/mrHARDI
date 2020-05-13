from threading import Event, Lock


class Sentinel:
    def __init__(self, subs=[]):
        self._event = Event()
        self._lock = Lock()
        self._ring_lock = Lock()
        self._subs = []

        for sub in subs:
            sub.listen_for_data(self)

    def wait(self, timeout=None):
        self._event.wait(timeout)
        self._lock.acquire()
        data = self._subs.copy()
        self._subs.clear()
        self._lock.release()
        return data

    def clear(self):
        self._event.clear()
        self._ring_lock.release()

    def set(self, sub):
        self._ring_lock.acquire()
        self._lock.acquire()
        self._subs.append(sub)
        self._lock.release()
        self._event.set()
