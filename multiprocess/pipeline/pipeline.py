import asyncio
import logging
from threading import Event

from multiprocess.comm.close_condition import CloseCondition
from multiprocess.cpu.thread import ThreadedAsyncEntity


class Pipeline(ThreadedAsyncEntity):
    def __init__(self, input_channel, output_channel, name="pipe"):
        super().__init__(name=name)
        self._input = input_channel
        self._output = output_channel
        self._exec_stack = []
        self._is_initialized = False
        self._end_cnd = CloseCondition()
        self._end_event = Event()

    def add_item(self, layer, additional_parents=None):
        if len(self._exec_stack) == 0:
            layer.connect_input(self._input)
        else:
            layer.connect_input(
                self._exec_stack[-1].output
            )

        self._exec_stack.append(layer)

        if additional_parents:
            for parent in additional_parents:
                layer.connect_input(parent.output)

    def initialize(self):
        logger.info("{} initializing".format(self._name))

        logger.debug("{} is starting its thread and loop".format(self._name))
        ready_evt = super().start()
        ready_evt.wait()
        logger.debug("{} loop ready for processing".format(self._name))

        logger.debug(
            "{} connecting and starting channels and layers".format(self._name)
        )
        self._exec_stack[-1].connect_output(self._output)
        self._input.start(lambda: self._end_cnd)
        self._output.start(lambda: self._end_cnd)
        for layer in self._exec_stack:
            layer.start()

        self._is_initialized = True
        logger.info("{} initialized".format(self._name))

    def run(self):
        if not self._is_initialized:
            self.initialize()

        asyncio.run_coroutine_threadsafe(
            self._run_pipeline(), self._async_loop
        )

    def wait_for_completion(self):
        self._end_event.wait()

    async def _run_pipeline(self):
        logger.info("{} running".format(self._name))

        for t in asyncio.as_completed(
            [l.process() for l in self._exec_stack]
        ):
            await t
            logger.debug(
                "{} has finished processing a layer".format(self._name)
            )

        logger.info("{} has finished processing".format(self._name))

        self._end_cnd.set()
        self._end_event.set()
        self._close()
        logger.info("{} has ended gracefully".format(self._name))


logger = logging.getLogger(Pipeline.__name__)
