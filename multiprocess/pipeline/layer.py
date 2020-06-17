import asyncio
import logging
from abc import ABCMeta

from multiprocess.comm.channel import Channel
from multiprocess.comm.close_condition import CloseCondition
from multiprocess.comm.subscriber import Subscriber
from multiprocess.cpu.thread import ThreadedAsyncEntity
from multiprocess.pipeline.pipeline_item import PipelineItem
from multiprocess.pipeline.unit import connect_units, Unit


class Layer(PipelineItem, ThreadedAsyncEntity, metaclass=ABCMeta):
    def __init__(
        self, input_channel, output_channel, main_loop=None, name="layer"
    ):
        ThreadedAsyncEntity.__init__(self, main_loop=main_loop, name=name)
        PipelineItem.__init__(self, input_channel, output_channel, name)
        self._layer = []
        self._hidden_connections = []
        self._end_cnd = CloseCondition()
        ready_evt = ThreadedAsyncEntity.start(self)
        ready_evt.wait()

    def add_unit(self, unit, additional_inputs=[], additional_outputs=[]):
        self._layer.append(unit)

        for parent in additional_inputs:
            if isinstance(parent, Unit):
                self._hidden_connections.append(
                    connect_units(parent, unit)
                )
            else:
                unit.connect_input(parent)
        for child in additional_outputs:
            if isinstance(child, Unit):
                self._hidden_connections.append(
                    connect_units(unit, child)
                )
            else:
                unit.connect_output(child)

    def get_package_keys(self):
        pass

    def connect_input(self, channel):
        subscriber = Subscriber(
            name="sub_{}_to_{}".format(channel.name, self.input.name)
        )
        channel.add_subscriber(subscriber, Channel.Sub.OUT)
        self.input.add_subscriber(subscriber, Channel.Sub.IN)
        return PipelineItem.connect_input(self, channel)

    def connect_output(self, channel):
        subscriber = Subscriber(
            name="sub_{}_to_{}".format(self.output.name, channel.name)
        )
        channel.add_subscriber(subscriber, Channel.Sub.IN)
        self.output.add_subscriber(subscriber, Channel.Sub.OUT)
        return PipelineItem.connect_output(self, channel)

    async def process(self):
        self._start_channels()

        await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
            self._process(), self._async_loop
        ))

        self._close()

    def _start_channels(self):
        for channel in self._connections + self._hidden_connections:
            channel.start(lambda: self._end_cnd)

    def _close(self, *args):
        logger.debug("{} is closing channels".format(self._name))
        self._end_cnd.set()
        asyncio.run_coroutine_threadsafe(
            self._wait_on_channels(), self._async_loop
        ).add_done_callback(lambda *args: self._close_super())

    def _close_super(self):
        ThreadedAsyncEntity._close(self)

    async def _wait_on_channels(self):
        logger.debug("{} waiting on channels".format(self._name))
        for fut in asyncio.as_completed([
            c.wait_for_completion()
            for c in self._connections[1:-1] + self._hidden_connections
        ]):
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
    def add_unit(self, unit, additional_inputs=[], additional_outputs=[]):
        unit.connect_input(self.input)
        unit.connect_output(self.output)

        super().add_unit(unit, additional_inputs, additional_outputs)


class SequenceLayer(Layer):
    async def process(self):
        self._layer[-1].connect_output(self.output)
        await super().process()

    def add_unit(self, unit, additional_inputs=[], additional_outputs=[]):
        if len(self._layer) == 0:
            unit.connect_input(self.input)
        else:
            self._connections.insert(-1, connect_units(
                self._layer[-1], unit, self._async_loop
            ))

        super().add_unit(unit, additional_inputs, additional_outputs)
