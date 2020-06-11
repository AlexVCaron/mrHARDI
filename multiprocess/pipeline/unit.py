import asyncio
import logging

from multiprocess.pipeline.channel import Channel
from multiprocess.pipeline.subscriber import Subscriber


class Unit:
    def __init__(self, process, log_file_path, name="unit", timeout=5):
        self._in = Subscriber("{}_sub_in".format(name))
        self._out = Subscriber("{}_sub_out".format(name))

        self._name = name
        self._proc = process
        self._log = log_file_path
        self._timeout = timeout

    def get_package_keys(self):
        return self._proc.get_input_keys()

    async def process(self):
        while self._in.is_alive() or self._in.data_ready():
            try:
                logger.debug("{} awaiting data".format(self._name))
                id_tag, in_package = await self._in.yield_data()
                logger.debug("{} received data".format(self._name))
                self._proc.set_inputs(in_package)
                logger.info("{} executing process".format(self._name))
                self._proc.execute(self._log)
                outputs = self._proc.get_outputs()
                logger.debug("{} transmitting data".format(self._name))
                await self._out.transmit(id_tag, outputs)
                logger.debug("{} transmitted data".format(self._name))
            except asyncio.CancelledError as e:
                logger.debug("{} data flow was shutdown".format(self._name))
                pass

        logger.debug("{} shutting down outputs".format(self._name))
        await self._out.shutdown()
        logger.info("{} processing complete".format(self._name))

    def connect_input(self, channel):
        channel.add_subscriber(self._in, Channel.Sub.OUT)
        return self

    def connect_output(self, channel):
        channel.add_subscriber(self._out, Channel.Sub.IN)
        return self


logger = logging.getLogger(Unit.__name__)


def create_unit(process, log_file_path, channel_in, channel_out):
    return Unit(process, log_file_path).connect_input(channel_in) \
                                       .connect_output(channel_out)


def connect_units(unit_up, unit_down, loop=None):
    inter_channel = Channel(loop, unit_down.get_package_keys())
    unit_up.connect_output(inter_channel)
    unit_down.connect_input(inter_channel)
    return inter_channel
