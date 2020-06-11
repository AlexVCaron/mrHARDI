import asyncio
from threading import Event

from multiprocess.cpu.thread import ThreadedAsyncEntity
from multiprocess.pipeline.close_condition import CloseCondition


class Pipeline(ThreadedAsyncEntity):
    def __init__(self, input_channel, output_channel):
        super().__init__()
        self._input = input_channel
        self._output = output_channel
        self._exec_stack = []
        self._is_initialized = False
        self._end_cnd = CloseCondition()
        self._end_event = Event()

    def add_layer(self, layer):
        if len(self._exec_stack) == 0:
            layer.connect_input(self._input)
            self._exec_stack.append(layer)
        else:
            layer.connect_input(
                self._exec_stack[-1].get_output_channel()
            )

    def initialize(self):
        ready_evt = super().start()
        ready_evt.wait()

        self._input.start(lambda: self._end_cnd)
        self._output.start(lambda: self._end_cnd)
        for layer in self._exec_stack:
            layer.start()

        self._is_initialized = True

    def run(self):
        if not self._is_initialized:
            self.initialize()

        self._async_loop.create_task(self._run_pipeline())

    def wait_for_completion(self):
        self._end_event.wait()

    async def _run_pipeline(self):
        for t in asyncio.as_completed(
            [l.process() for l in self._exec_stack]
        ):
            await t

        self._end_cnd.set()
        self._close()
