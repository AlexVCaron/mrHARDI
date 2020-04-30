import time


class Unit:
    def __init__(self, in_sub, process, out_sub):
        self._in = in_sub
        self._proc = process
        self._out = out_sub

    def process(self):
        while not self._in.data_ready():
            time.sleep(1)

        in_package = self._in.yield_data()
        self._proc.set_inputs(in_package)
        self._proc.execute()
        outputs = self._proc.get_outputs()

        self._out.transmit(outputs)
