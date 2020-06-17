import asyncio
import logging

from multiprocess.comm.channel import Channel
from multiprocess.comm.subscriber import Subscriber
from multiprocess.pipeline.pipeline_item import PipelineItem


class Unit(PipelineItem):
    def __init__(self, process, log_file_path, name="unit", timeout=5):
        super().__init__(
            Subscriber("{}_sub_in".format(name)),
            Subscriber("{}_sub_out".format(name)),
            name
        )

        self._proc = process
        self._log = log_file_path
        self._timeout = timeout

    def connect_input(self, channel):
        channel.add_subscriber(self.input, Channel.Sub.OUT)
        return super().connect_input(channel)

    def connect_output(self, channel):
        channel.add_subscriber(self.output, Channel.Sub.IN)
        return super().connect_input(channel)

    def get_package_keys(self):
        return self._proc.get_input_keys()

    async def process(self):
        while self.input.promise_data():
            try:
                logger.debug("{} awaiting data".format(self._name))
                id_tag, in_package = await self.input.yield_data()
                logger.debug("{} received data".format(self._name))
                self._proc.set_inputs(in_package)
                logger.info("{} executing process".format(self._name))
                self._proc.execute(self._log)
                outputs = self._proc.get_outputs()
                logger.debug("{} transmitting data".format(self._name))
                await self.output.transmit(id_tag, outputs)
                logger.debug("{} transmitted data".format(self._name))
            except asyncio.CancelledError:
                logger.debug("{} data flow was shutdown".format(self._name))
                pass

        logger.debug("{} shutting down outputs".format(self._name))
        await self.output.shutdown()
        logger.info("{} processing complete".format(self._name))


logger = logging.getLogger(Unit.__name__)


def create_unit(process, log_file_path, channel_in, channel_out):
    return Unit(process, log_file_path).connect_input(channel_in) \
                                       .connect_output(channel_out)


def connect_units(unit_up, unit_down, loop=None):
    inter_channel = Channel(
        loop, unit_down.get_package_keys(),
        name="chan_{}_to_{}".format(unit_up.name, unit_down.name)
    )
    unit_up.connect_output(inter_channel)
    unit_down.connect_input(inter_channel)
    return inter_channel
