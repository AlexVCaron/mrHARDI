import asyncio
import logging
from threading import Event

from piper.comm import Channel
from piper.comm.close_condition import CloseCondition
from piper.drivers.asyncio import AsyncLoopManager


class Pipeline(AsyncLoopManager):
    async def _async_run(self, *args, **kwargs):
        pass

    def __init__(self, input_channel, output_channel, name="pipe"):
        super().__init__(name=name)
        self._input = input_channel
        self._output = output_channel
        self._exec_stack = []
        self._main_async_job = None
        self._is_initialized = False
        self._is_killing = False
        self._started = False
        self._end_cnd = CloseCondition()
        self._end_event = Event()

    def connect_output(self, subscriber):
        self._output.add_subscriber(subscriber, Channel.Sub.OUT)

    @property
    def serialize(self):
        return {**super().serialize, **{
            "initialized": self._is_initialized,
            "channel_in": self._input.serialize,
            "channel_out": self._output.serialize,
            "started": self._started,
            "stopped": self._end_event.is_set(),
            "items": [i.serialize for i in self._exec_stack]
        }}

    @property
    def initialized(self):
        return self._is_initialized

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

    def initialize(self, main_loop, exception_handler=None):
        logger.info("{} initializing".format(self._name))

        ready_evt = super().start(main_loop, exception_handler)
        ready_evt.wait()

        # logger.debug("{} is starting its thread and loop".format(self._name))
        #
        # logger.debug("{} loop ready for processing".format(self._name))

        logger.debug(
            "{} connecting and starting channels and layers".format(self._name)
        )
        self._exec_stack[-1].connect_output(self._output)
        self._input.start(
            lambda: self._end_cnd,
            exception_handler=exception_handler, depth=0
        )
        self._output.start(
            lambda: self._end_cnd,
            exception_handler=exception_handler, depth=0
        )

        for i, layer in enumerate(self._exec_stack):
            layer.initialize(exception_handler, i)

        self._is_initialized = True
        logger.info("{} initialized".format(self._name))

    def kill(self):
        if not self._is_killing:
            self._is_killing = True
            asyncio.run_coroutine_threadsafe(
                self._input.shutdown(True), self._async_loop
            )# .add_done_callback(
            #     lambda *args: asyncio.run_coroutine_threadsafe(
            #         self._cancel_tasks_job(excludes=[self._main_async_job]),
            #         self._async_loop
            #     )
            # )

    def run(self):
        assert self._is_initialized, "Pipeline is not initialized, not running"

        self._main_async_job = asyncio.run_coroutine_threadsafe(
            self._run_pipeline(), self._async_loop
        )

    def test_run(self, quiet=False):
        logging.basicConfig(level="INFO" if quiet else "DEBUG")

        for item in self._exec_stack:
            item.set_test()

    def wait_for_completion(self):
        self._end_event.wait()

    async def _run_pipeline(self):
        logger.info("{} running".format(self._name))

        self._started = True

        for t in asyncio.as_completed(
            [l.process() for l in self._exec_stack]
        ):
            try:
                await t
                logger.debug(
                    "{} has finished processing a layer".format(self._name)
                )
            except asyncio.CancelledError as e:
                # If this task is cancelled, then all exceptions should have
                # been caught and processed, we only need to pass until all
                # layers have caught the cancel, to ensure graceful shutdown
                print(1)
                logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!Exception while running pipeline\n{}".format(e))
                pass
            except Exception as e:
                raise e

        logger.info("{} has finished processing".format(self._name))

        self._end_cnd.set()

        self._end_event.set()
        self._close()
        logger.info("{} has ended gracefully".format(self._name))


logger = logging.getLogger(Pipeline.__name__)
