import asyncio
from asyncio import Future
from enum import Enum
from itertools import cycle
from threading import Thread
from uuid import uuid4

from multiprocess.cpu.thread import ThreadedAsyncEntity
from multiprocess.pipeline.subscriber import Subscriber


class Channel(ThreadedAsyncEntity):
    class Sub(Enum):
        IN = "in"
        OUT = "out"

    def __init__(self, main_loop, package_keys, broadcast_out=False):
        super().__init__(main_loop)

        self._package_keys = package_keys
        self._broadcast_out = broadcast_out

        self._subscribers = {
            k: [] for k in Channel.Sub
        }
        self._out_iter = None
        self._idle_packages = {}

        if self._broadcast_out:
            self._transmit = self._bcast_out

    def running(self):
        return self._thread.is_alive()

    def start(self, main_loop, end_fn=lambda: False):
        self._start_async_loop()
        if main_loop.run_until_complete(self._ready):
            self._threaded_run(end_fn, self._async_loop)
        return self._future

    def _threaded_run(self, end_fn, loop):
        self.prepare_iterators()
        f = asyncio.run_coroutine_threadsafe(self._async_run(end_fn), loop)

        f.add_done_callback(lambda *args, **kwargs: self._close(*args, **kwargs))

    async def has_inputs(self):
        a = len(self._subscribers[Channel.Sub.IN])
        alive, ready = True, True
        for s in self._subscribers[Channel.Sub.IN]:
            alive = alive and await s.is_alive()
            ready = ready and await s.data_ready()
        # b = list(await s.is_alive() or await s.data_ready() for s in self._subscribers[Channel.Sub.IN])
        b = False
        return (
            a > 0 and (alive or ready)
        )

    async def _async_run(self, end_fn):
        while not end_fn() and await self.has_inputs():
            await self.pool_data_package()

        for sub in self._subscribers[Channel.Sub.OUT]:
            await sub.shutdown()

    def prepare_iterators(self):
        self._out_iter = self._subscribers[Channel.Sub.OUT]
        if not self._broadcast_out:
            self._out_iter = cycle(
                self._subscribers[Channel.Sub.OUT]
            )

    def add_subscriber(self, sub, type=Sub.IN):
        self._subscribers[type].append(sub)

    async def pool_data_package(self):
        timestamp = uuid4()
        has_transmitted = False

        while await self.has_inputs():
            inputs = self._subscribers[Channel.Sub.IN]

            for i, sub in enumerate(inputs):
                if not await sub.timestamp(timestamp):
                    while await sub.data_ready():
                        id_tag = await self._yield(i, sub)

                        if id_tag and self._is_complete(id_tag):
                            await self._transmit(id_tag)
                            has_transmitted = True

            timestamped = True
            for s in inputs:
                timestamped = timestamp and await s.timestamp(timestamp)

            if has_transmitted or timestamped:
                break

    def _is_complete(self, id_tag):
        package_keys = self._idle_packages[id_tag]
        return all(k in package_keys for k in self._package_keys)

    async def _yield(self, sub_idx, sub):
        id_tag, data = await sub.yield_data()

        if id_tag not in self._idle_packages:
            self._idle_packages[id_tag] = {}

        self._idle_packages[id_tag].update(data)

        return id_tag

    async def _transmit(self, id_tag):
        sub = next(self._out_iter)
        package = self._idle_packages[id_tag]
        await sub.transmit(id_tag, package)

    async def _bcast_out(self, id_tag):
        package = self._idle_packages[id_tag]
        for sub in self._out_iter:
            await sub.transmit(id_tag, package)


def create_connection(input_list, package_keys):
    channel = Channel(package_keys)

    for in_c in input_list:
        subscriber = Subscriber()

        channel.add_subscriber(subscriber, Channel.Sub.IN)
        in_c.add_subscriber(subscriber, Channel.Sub.OUT)

    return channel
