import asyncio
import logging
from abc import ABCMeta
from functools import partial

from piper.comm import Channel, CloseCondition, Subscriber
from piper.comm.channel_filter import ChannelFilter
from piper.drivers.asyncio import AsyncLoopManager
from piper.exceptions import RecoverableException, \
    UnrecoverableException
from .pipeline_item import PipelineItem, connect_pipeline_items


class Layer(PipelineItem, AsyncLoopManager, metaclass=ABCMeta):
    async def _async_run(self, *args, **kwargs):
        pass

    def __init__(
        self, input_channel, output_channel, name="layer"
    ):
        AsyncLoopManager.__init__(self, name=name)
        PipelineItem.__init__(self, input_channel, output_channel, name)
        self._layer = []
        self._hidden_connections = []
        self._end_cnd = CloseCondition()

    @property
    def serialize(self):
        return {
            **AsyncLoopManager.serialize.fget(self),
            **PipelineItem.serialize.fget(self),
            **{
                'inter_item_channels': [
                    c.serialize for c in self._connections[1:-1]
                ],
                'hidden_channels': [
                    c.serialize for c in self._hidden_connections
                ],
                'items': [i.serialize for i in self._layer]
            }
        }

    def initialize(self, exception_handler=None, depth=0):
        ex_handler = partial(
            self._async_exception_handler, basic_handler=exception_handler
        )
        ready_evt = AsyncLoopManager.start(
            self, exception_handler=ex_handler
        )
        ready_evt.wait()

        self._start_channels(ex_handler, depth)

        for item in self._layer:
            item.initialize(ex_handler, depth)

        self._initialized = True
        PipelineItem.initialize(self, depth=depth)

    def add_unit(self, unit, additional_inputs=[], additional_outputs=[]):
        self._layer.append(unit)

        for parent in additional_inputs:
            includes, excludes = None, None
            if isinstance(parent, ChannelFilter):
                parent, includes, excludes = parent.get_filter_on_item()

            if isinstance(parent, PipelineItem):
                self._hidden_connections.append(
                    connect_pipeline_items(parent, unit, includes, excludes)
                )
            else:
                unit.connect_input(parent)

        for child in additional_outputs:
            includes, excludes = None, None
            if isinstance(child, ChannelFilter):
                child, includes, excludes = child.get_filter_on_item()

            if isinstance(child, PipelineItem):
                self._hidden_connections.append(
                    connect_pipeline_items(unit, child, includes, excludes)
                )
            else:
                unit.connect_output(child)

    def set_test(self, on=True):
        PipelineItem.set_test(self, on)
        for item in self._layer:
            item.set_test(on)

    @property
    def package_keys(self):
        return self._connections[0].package_keys

    def connect_input(self, channel, includes=None, excludes=None):
        subscriber = Subscriber(
            name="sub_{}_to_{}".format(channel.name, self.input.name),
            includes=includes, excludes=excludes
        )
        channel.add_subscriber(subscriber, Channel.Sub.OUT)
        self.input.add_subscriber(subscriber, Channel.Sub.IN)
        return PipelineItem.connect_input(self, channel)

    def connect_output(self, channel, *args, **kwargs):
        subscriber = Subscriber(
            name="sub_{}_to_{}".format(self.output.name, channel.name)
        )
        channel.add_subscriber(subscriber, Channel.Sub.IN)
        self.output.add_subscriber(subscriber, Channel.Sub.OUT)
        return PipelineItem.connect_output(self, channel)

    async def process(self):
        assert self._initialized, "{} uninitialized".format(self._name)

        await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
            self._process(), self._async_loop
        ))

        logger.debug("{} is closing channels".format(self._name))

        self._end_cnd.set()
        # await self._wait_on_layer()
        # await self._wait_on_channels()
        self._close_super()

    async def wait_for_shutdown(self):
        await self.wait_for_completion()

    def _start_channels(self, exception_handler, depth):
        for channel in self._connections + self._hidden_connections:
            channel.start(
                lambda: self._end_cnd,
                exception_handler=exception_handler, depth=depth
            )

    def _close_super(self):
        AsyncLoopManager._close(self)

    async def _wait_on_layer(self):
        logger.debug("{} waiting on layer to close".format(self._name))
        for fut in asyncio.as_completed([
            item.wait_for_shutdown()
            for item in self._layer
        ]):
            await fut
        logger.debug("{} layer is closed".format(self._name))

    async def _wait_on_channels(self):
        logger.debug("{} waiting on channels".format(self._name))
        for fut in asyncio.as_completed([
            c.wait_for_completion()
            for c in self._connections + self._hidden_connections
        ]):
            await fut
        logger.debug("{} channels are closed".format(self._name))

    async def _process(self):
        for t in asyncio.as_completed(
            [unit.process() for unit in self._layer]
        ):
            try:
                await t
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self._async_loop.call_exception_handler({
                    "message": str(e),
                    'exception': e
                })
                break

        logger.info("{} is done with processing".format(self._name))

    def _async_exception_handler(self, loop, context, basic_handler=None):
        if not self._closing:
            self._closing = True
            ex = context['exception'] if 'exception' in context else None

            if isinstance(ex, RecoverableException):
                logger.error(
                    "{} got an exception, processing will continue".format(
                        self.name
                    )
                )
                logger.exception(str(ex))
                return
            elif isinstance(ex, UnrecoverableException):
                logger.error(
                    "{} got an unrecoverable exception".format(
                        self.name
                    )
                )
                logger.exception(str(ex))

                logger.warning(
                    "{} will attempt graceful shutdown".format(self.name)
                )
                task = asyncio.shield(asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
                    self._shut_channels(), loop
                )))
                task.add_done_callback(
                    lambda *args: AsyncLoopManager._async_exception_handler(
                        self, loop, context, basic_handler
                    )
                )

    async def _shut_channels(self):
        try:
            for fut in asyncio.as_completed([
                c.shutdown(True)
                for c in self._hidden_connections + self._connections
            ]):
                try:
                    await fut
                except Exception as e:
                    raise e
        except Exception as e:
            raise e
        logger.error("{} channels shut".format(self.name))
        # try:
        #     await asyncio.wait(
        #         [PipelineItem._shut_channels(self)] +
        #         list(c.shutdown(True) for c in self._hidden_connections),
        #         loop=self._async_loop
        #     )
        #     print("feni")
        # except BaseException as e:
        #     raise e


logger = logging.getLogger(Layer.__name__)


class ParallelLayer(Layer):
    def add_unit(self, unit, additional_inputs=[], additional_outputs=[]):
        unit.connect_input(self.input)
        unit.connect_output(self.output)

        super().add_unit(unit, additional_inputs, additional_outputs)


class SequenceLayer(Layer):
    def initialize(self, exception_handler=None, depth=0):
        self._layer[-1].connect_output(self.output)
        super().initialize(exception_handler, depth)

    def add_unit(self, unit, additional_inputs=[], additional_outputs=[]):
        if len(self._layer) == 0:
            unit.connect_input(self.input)
        else:
            self._connections.insert(-1, connect_pipeline_items(
                self._layer[-1], unit, self._async_loop
            ))

        super().add_unit(unit, additional_inputs, additional_outputs)
