import asyncio
import logging
from enum import Enum
from itertools import cycle
from uuid import uuid4

from multiprocess.comm.subscriber import Subscriber
from multiprocess.cpu.thread import ThreadedAsyncEntity


class Channel(ThreadedAsyncEntity):
    class Sub(Enum):
        IN = "in"
        OUT = "out"

    def __init__(
        self, main_loop, package_keys, broadcast_out=False, name="chan"
    ):
        super().__init__(main_loop, name)

        self._package_keys = package_keys
        self._broadcast_out = broadcast_out
        self._transmit_futures = []

        self._subscribers = {
            k: [] for k in Channel.Sub
        }
        self._out_iter = None
        self._idle_packages = {}

        if self._broadcast_out:
            self._transmit = self._bcast_out

    def start(self, end_cnd=lambda: False, daemon=True, **kwargs):
        ready_evt = super().start(daemon=daemon, **kwargs)
        ready_evt.wait()
        self._threaded_run(end_cnd, self._async_loop)
        return self._done

    def _threaded_run(self, end_cnd, loop):
        self.prepare_iterators()
        asyncio.run_coroutine_threadsafe(self._async_run(end_cnd), loop)

    def has_inputs(self):
        will_be_data = any(list(
            s.promise_data() for s in self._subscribers[Channel.Sub.IN]
        ))

        return (
            len(self._subscribers[Channel.Sub.IN]) > 0 and will_be_data
        )

    def package_keys(self):
        return self._package_keys

    def prepare_iterators(self):
        self._out_iter = self._subscribers[Channel.Sub.OUT]
        if not self._broadcast_out:
            self._out_iter = cycle(
                self._subscribers[Channel.Sub.OUT]
            )

    def prepare_subscribers(self):
        for sub_type in self._subscribers.values():
            for sub in sub_type:
                sub.set_loop(self._async_loop)

    def add_subscriber(self, sub, type=Sub.IN):
        self._subscribers[type].append(sub)

    def _get_package(self, id_tag, *args, **kwargs):
        return self._idle_packages.pop(id_tag)

    def _is_complete(self, id_tag):
        package_keys = self._idle_packages[id_tag]
        return all(k in package_keys for k in self._package_keys)

    def _looping_required(self, end_cnd):
        return not end_cnd() or self.has_inputs()

    async def _async_run(self, end_cnd):
        logger.info("{} async loop starting".format(self._name))
        try:
            while self._looping_required(end_cnd):
                logger.debug("{} pooling data".format(self._name))
                await self.pool_data_package()
        except asyncio.CancelledError:
            logger.debug("{} received cancellation call".format(self._name))
            pass

        for fut in asyncio.as_completed(self._transmit_futures):
            await fut

        logger.debug("{} shutting output subscribers".format(self._name))
        for fut in asyncio.as_completed([
            s.shutdown() for s in self._subscribers[Channel.Sub.OUT]
        ]):
            await fut

        logger.debug("{} attempting graceful shutdown".format(self._name))
        self._close()
        logger.info("Goodbye {}".format(self._name))

    def _subscribers_empty(self):
        return all(
            not s.promise_data() for s in self._subscribers[Channel.Sub.IN]
        )

    async def pool_data_package(self):
        timestamp = uuid4()
        while True:
            logger.debug("{} has started looping".format(self._name))
            inputs = list(filter(
                lambda s: s.timestamp(timestamp),
                self._subscribers[Channel.Sub.IN]
            ))
            has_transmitted = False
            inner_cancel = None

            logger.debug(
                "{} has {} up-to-date inputs".format(self._name, len(inputs))
            )

            for result in asyncio.as_completed([
                self._yield(i) for i in inputs
            ]):
                try:
                    logger.debug("{} awaits on subscriber".format(self._name))
                    id_tag = await result
                    logger.debug(
                        "{} received an id {}".format(self._name, id_tag)
                    )

                    try:
                        if id_tag and self._is_complete(id_tag):
                            logger.debug(
                                "{} is transmitting data".format(self._name)
                            )
                            package = self._get_package(id_tag)
                            await self._transmit(id_tag, package)
                            has_transmitted = True
                            logger.debug(
                                "{} has transmitted".format(self._name)
                            )
                        else:
                            logger.debug("{} package was not complete".format(
                                self._name)
                            )
                    except KeyError:
                        pass
                except asyncio.CancelledError as e:
                    inner_cancel = e

            if inner_cancel and self._subscribers_empty():
                raise inner_cancel

            await asyncio.sleep(0)

            if has_transmitted and all([not s.promise_data() for s in inputs]):
                logger.debug("{} is breaking the loop".format(self._name))
                break
            else:
                timestamp = uuid4()

    async def _yield(self, sub):
        id_tag, data = await sub.yield_data()

        if id_tag:
            if id_tag not in self._idle_packages:
                self._idle_packages[id_tag] = {}

            logging.debug(
                "{} putting at {} : {}".format(
                    self._name, id_tag, data.keys() if data else None
                )
            )
            self._idle_packages[id_tag].update(data)

        return id_tag

    async def _transmit(self, id_tag, package):
        sub = next(self._out_iter)
        task = asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
            sub.transmit(id_tag, package), self._async_loop
        ))
        self._transmit_futures.append(task)

        await task
        self._transmit_futures.remove(task)

    async def _bcast_out(self, id_tag, package):
        for fut in asyncio.as_completed([
            s.transmit(id_tag, package) for s in self._out_iter
        ]):
            await fut


logger = logging.getLogger(Channel.__name__)


def create_connection(input_list, package_keys, main_loop, name, bcast=False):
    channel = Channel(main_loop, package_keys, bcast, name)

    for in_c in input_list:
        subscriber = Subscriber()

        channel.add_subscriber(subscriber, Channel.Sub.IN)
        in_c.add_subscriber(subscriber, Channel.Sub.OUT)

    return channel
