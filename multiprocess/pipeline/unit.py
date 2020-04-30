import time

from multiprocess.pipeline.channel import Channel
from multiprocess.pipeline.subscriber import Subscriber


class Unit:
    def __init__(self, process):
        self._in, self._out = Subscriber(), Subscriber()
        self._proc = process

    def process(self):
        while not self._in.data_ready():
            time.sleep(1)

        id_tag, in_package = self._in.yield_data()
        self._proc.set_inputs(id_tag, in_package)
        self._proc.execute()
        outputs = self._proc.get_outputs()

        self._out.transmit(id_tag, outputs)

    def connect_input(self, channel):
        channel.add_subscriber(self._in, Channel.Sub.OUT)
        return self

    def connect_output(self, channel):
        channel.add_subscriber(self._in, Channel.Sub.IN)
        return self


def create_unit(process, channel_in, channel_out):
    return Unit(process).connect_input(channel_in).connect_output(channel_out)
