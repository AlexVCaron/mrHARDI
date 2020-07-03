import asyncio
import logging

from piper.comm import Subscriber
from piper.drivers.asyncio import AsyncLoopManager
from piper.stats.manager import StatsManager

logging.basicConfig(level="WARNING")


class Executor(AsyncLoopManager):
    async def _async_run(self, *args, **kwargs):
        pass

    def __init__(self, pipeline, profiling=False, name="executor"):
        super().__init__(name=name)
        self._results = Subscriber("{}_sub_results_collector".format(name))
        self._pipeline = pipeline
        ready_evt = self.start(None, self._async_exception_handler)
        ready_evt.wait()
        self._profiler = {
            "is_profiling": profiling,
            "profiler": None
        }
        self._exception_stack = []

        self._pipeline.connect_output(self._results)

        if profiling:
            self._pipeline.initialize(
                self._async_loop, self._async_exception_handler
            )
            self._start_profiling()

    def profile(self):
        self._pipeline.initialize(
            self._async_loop, self._async_exception_handler
        )
        self._start_profiling(True)

    @property
    def serialize(self):
        return {**super().serialize, **{
            "pipeline": self._pipeline.serialize,
            "results": self._results.serialize
        }}

    @property
    def pipeline(self):
        return self._pipeline

    def execute_pipeline(self):
        if not self._pipeline.initialized:
            self._pipeline.initialize(
                self._async_loop, self._async_exception_handler
            )

        self._pipeline.run()

        return asyncio.run_coroutine_threadsafe(
            self._dequeue_pipeline(), self._async_loop
        ).result()

    async def _dequeue_pipeline(self):
        results = []
        logger.debug("{} has started collecting results".format(self._name))
        while self._results.promise_data():
            try:
                results.append(await self._results.yield_data())
                logger.debug("{} collected a result".format(self._name))
            except asyncio.CancelledError:
                logger.warning("{} collection shutdown".format(self._name))
                break

        logger.info("{} wait end of pipeline".format(self._name))

        self._pipeline.wait_for_completion()

        return results

    def _async_exception_handler(self, loop, context, basic_handler=None):
        msg = context.get("exception", context["message"])
        logger.error("Caught an error in async loop {}".format(msg))
        self._exception_stack.append(msg)
        self._pipeline.kill()

    def _start_profiling(self, close_on_exit=False):
        self._profiler["profiler"] = StatsManager(
            self, close_on_exit
        )

        with self._profiler["profiler"] as profiler:
            print("Profiler {} running ...".format(profiler.name))
            _ = input(
                "Close and purge db ? <Press enter>"
            )


logger = logging.getLogger(Executor.__name__)
