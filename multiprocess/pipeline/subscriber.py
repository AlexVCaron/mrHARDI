
from threading import Lock

from multiprocess.exceptions import SubscriberClosedException


class Subscriber:
    def __init__(self):
        self._timestamp = None
        self._id_tags = []
        self._lock = Lock()
        self._queue = {}
        self._alive = True
        self._listeners = []

    def timestamp(self, timestamp):
        if self._timestamp == timestamp:
            return True

        self._timestamp = timestamp
        return False

    def is_alive(self):
        self._lock.acquire()
        alive = self._alive
        self._lock.release()
        return alive

    def shutdown(self):
        self._lock.acquire()
        self._alive = False
        self.transmit = self._shutdown_exception
        self._lock.release()
        self._inform_listeners()

    def data_ready(self):
        return len(self._queue) > 0

    def transmit(self, id_tag, package):
        self._lock.acquire()
        if id_tag not in self._queue:
            self._id_tags.append(id_tag)
            self._queue[id_tag] = {}

        self._queue[id_tag].update(package)
        self._lock.release()

        self._inform_listeners()

    def yield_data(self):
        self._lock.acquire()
        id_tag = self._id_tags.pop(0)
        self._lock.release()
        return id_tag, self._queue.pop(id_tag)

    def listen_for_data(self, flag):
        self._listeners.append(flag)

    def _inform_listeners(self):
        for flag in self._listeners:
            flag.set(self)

    def _shutdown_exception(self, *args, **kwargs):
        raise SubscriberClosedException(self)
