from threading import Thread

from multiprocess.pipeline.channel import Channel
from multiprocess.pipeline.sentinel import Sentinel
from multiprocess.pipeline.subscriber import Subscriber


class Unit:
    def __init__(self, process, log_file_path, timeout=5):
        self._in, self._out = Subscriber(), Subscriber()
        self._sentinel = Sentinel([self._in])
        self._proc = process
        self._log = log_file_path
        self._timeout = timeout

    def process(self):
        thread = Thread(target=self._process, daemon=True)
        thread.start()

    def _process(self):
        while self._in.is_alive() or self._in.data_ready():
            inputs = self._sentinel.wait()
            self._sentinel.clear()

            for input in inputs:
                while input.data_ready():
                    id_tag, in_package = self._in.yield_data()
                    self._proc.set_inputs(id_tag, in_package)
                    self._proc.execute(self._log)
                    outputs = self._proc.get_outputs()

                    self._out.transmit(id_tag, outputs)

        self._out.shutdown()

    def connect_input(self, channel):
        channel.add_subscriber(self._in, Channel.Sub.OUT)
        return self

    def connect_output(self, channel):
        channel.add_subscriber(self._out, Channel.Sub.IN)
        return self


def create_unit(process, log_file_path, channel_in, channel_out):
    return Unit(process, log_file_path).connect_input(channel_in).connect_output(channel_out)
