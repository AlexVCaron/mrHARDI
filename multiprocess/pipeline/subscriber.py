import asyncio

from multiprocess.exceptions import SubscriberClosedException


class Subscriber:
    def __init__(self):
        self._timestamp = None
        self._id_tags = []
        self._queue = {}
        self._alive = True

    async def timestamp(self, timestamp):
        if self._timestamp == timestamp:
            return True

        self._timestamp = timestamp
        return False

    async def is_alive(self):
        return self._alive

    async def shutdown(self):
        self._alive = False
        self.transmit = self._shutdown_exception

    async def data_ready(self):
        return len(self._queue) > 0

    async def transmit(self, id_tag, package):
        if id_tag not in self._queue:
            self._id_tags.append(id_tag)
            self._queue[id_tag] = {}

        self._queue[id_tag].update(package)

    async def yield_data(self):
        id_tag = self._id_tags.pop(0)
        return id_tag, self._queue.pop(id_tag)

    async def _shutdown_exception(self, *args, **kwargs):
        raise SubscriberClosedException(self)
