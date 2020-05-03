import time
from enum import Enum
from itertools import cycle
from threading import Thread
from uuid import uuid4

from multiprocess.pipeline.subscriber import Subscriber


class Channel:
    class Sub(Enum):
        IN = "in"
        OUT = "out"

    def __init__(self, package_keys, broadcast_out=False):
        self._package_keys = package_keys
        self._broadcast_out = broadcast_out
        self._thread = None
        self._subscribers = {
            k: [] for k in Channel.Sub
        }
        self._idle_packages = {}

        if self._broadcast_out:
            self._transmit = self._bcast_out

    def start(self, end_fn):
        self._thread = Thread(target=self._threaded_run, args=(end_fn,))
        self._thread.daemon = True
        self._thread.start()

    def running(self):
        return self._thread and self._thread.is_alive()

    def has_inputs(self):
        return len(self._subscribers[Channel.Sub.IN]) > 0

    def _threaded_run(self, end_fn):
        if not self._broadcast_out:
            self._subscribers[Channel.Sub.OUT] = cycle(
                self._subscribers[Channel.Sub.OUT]
            )

        while not end_fn() and self.has_inputs():
            self.pool_data_package()

    def add_subscriber(self, sub, type=Sub.IN):
        self._subscribers[type].append(sub)

    def pool_data_package(self):
        timestamp = uuid4()
        inputs = self._subscribers[Channel.Sub.IN]
        has_transmitted = False

        while True:
            for i, sub in enumerate(inputs):
                if not sub.timestamp(timestamp) and sub.data_ready():
                    id_tag = self._yield(i, sub)

                    if id_tag and self._is_complete(id_tag):
                        self._transmit(id_tag)
                        has_transmitted = True
                        break

            if has_transmitted or all(s.timestamp(timestamp) for s in inputs):
                break

            time.sleep(1)

    def _is_complete(self, id_tag):
        package_keys = self._idle_packages[id_tag]
        return all(k in self._package_keys for k in package_keys)

    def _yield(self, sub_idx, sub):
        id_tag, data = sub.yield_data()

        if id_tag not in self._idle_packages:
            self._idle_packages[id_tag] = {}

        self._idle_packages[id_tag].update(data)

        return id_tag

    def _transmit(self, id_tag):
        sub = next(self._subscribers[Channel.Sub.OUT])
        package = self._idle_packages[id_tag]
        sub.transmit(id_tag, package)

    def _bcast_out(self, id_tag):
        package = self._idle_packages[id_tag]
        for sub in self._subscribers[Channel.Sub.OUT]:
            sub.transmit(id_tag, package)


def create_connection(input_list, package_keys):
    channel = Channel(package_keys)

    for in_c in input_list:
        subscriber = Subscriber()

        channel.add_subscriber(subscriber, Channel.Sub.IN)
        in_c.add_subscriber(subscriber, Channel.Sub.OUT)

    return channel
