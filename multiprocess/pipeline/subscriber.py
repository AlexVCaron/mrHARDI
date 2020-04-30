

class Subscriber:
    def __init__(self):
        self._timestamp = None
        self._id_tags = []
        self._queue = {}

    def timestamp(self, timestamp):
        if self._timestamp == timestamp:
            return True

        self._timestamp = timestamp
        return False

    def data_ready(self):
        return len(self._queue) > 0

    def transmit(self, id_tag, package):
        if id_tag not in self._queue:
            self._id_tags.append(id_tag)
            self._queue[id_tag] = {}

        self._queue[id_tag].update(package)

    def yield_data(self):
        id_tag = self._id_tags.pop(0)
        return id_tag, self._queue.pop(id_tag)
