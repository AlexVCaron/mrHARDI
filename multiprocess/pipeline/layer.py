import asyncio
import logging
from abc import ABCMeta

from multiprocess.cpu.thread import ThreadedAsyncEntity
from multiprocess.pipeline.channel import Channel
from multiprocess.pipeline.close_condition import CloseCondition
from multiprocess.pipeline.subscriber import Subscriber
from multiprocess.pipeline.unit import connect_units


class Layer(ThreadedAsyncEntity, metaclass=ABCMeta):
    def __init__(
        self, input_channel, output_channel, main_loop=None, name="layer"
    ):
        super().__init__(main_loop=main_loop, name=name)
        self._layer = []
        self._channels = [input_channel, output_channel]
        self._end_cnd = CloseCondition()
        ready_evt = super().start()
        ready_evt.wait()

    def add_unit(self, unit):
        self._layer.append(unit)

    def get_input_channel(self):
        return self._channels[0]

    def get_output_channel(self):
        return self._channels[-1]

    def connect_input(self, channel):
        subscriber = Subscriber()
        channel.add_subscriber(subscriber, Channel.Sub.OUT)
        self._channels[0].add_subscriber(subscriber, Channel.Sub.IN)

    def connect_output(self, channel):
        subscriber = Subscriber()
        channel.add_subscriber(subscriber, Channel.Sub.IN)
        self._channels[-1].add_subscriber(subscriber, Channel.Sub.OUT)

    def process(self):
        self._start_channels()

        task = asyncio.run_coroutine_threadsafe(
            self._process(), self._async_loop
        )
        task.add_done_callback(lambda *args: self._close())

        return task

    def _start_channels(self):
        for channel in self._channels:
            channel.start(lambda: self._end_cnd)

    def _close(self, *args):
        logger.debug("{} is closing channels".format(self._name))
        self._end_cnd.set()
        asyncio.run_coroutine_threadsafe(
            self._wait_on_channels(), self._async_loop
        ).add_done_callback(lambda *args: self._close_super())

    def _close_super(self):
        super()._close()

    async def _wait_on_channels(self):
        logger.debug("{} waiting on channels".format(self._name))
        for fut in asyncio.as_completed(
            [c.wait_for_completion() for c in self._channels[1:-1]]
        ):
            await fut
        logger.debug("{} channels are closed".format(self._name))

    async def _process(self):
        for t in asyncio.as_completed(
            [unit.process() for unit in self._layer]
        ):
            await t

        logger.info("{} is done with processing".format(self._name))


logger = logging.getLogger(Layer.__name__)


class ParallelLayer(Layer):
    def add_unit(self, unit):
        unit.connect_input(self._channels[0])
        unit.connect_output(self._channels[-1])

        super().add_unit(unit)


class SequenceLayer(Layer):
    def process(self):
        self._layer[-1].connect_output(self._channels[-1])
        super().process()

    def add_unit(self, unit):
        if len(self._layer) == 0:
            unit.connect_input(self._channels[0])
        else:
            self._channels.insert(-1, connect_units(
                self._layer[-1], unit, self._async_loop
            ))

        super().add_unit(unit)
