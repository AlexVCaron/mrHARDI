import asyncio
import time
from unittest import TestCase

from monkey_io.dataloader import Dataloader
from monkey_io.dataset import Dataset
from multiprocess.comm.channel import Channel
from multiprocess.comm.collector import Collector
from multiprocess.pipeline.layer import SequenceLayer
from multiprocess.pipeline.pipeline import Pipeline
from multiprocess.pipeline.process import Process
from multiprocess.pipeline.unit import Unit
from multiprocess.scheduler import Scheduler
from test.test_monkey_io.helpers.data import DATA_KEYS, assert_data_point
from test.test_monkey_io.helpers.monkey_io_test_base import MonkeyIOTestBase


class AwaitAndPassProcess(Process):
    def __init__(self, package_keys, name, output_prefix, sleep_time=5):
        super().__init__(name, output_prefix)
        self.package = None
        self.keys = package_keys
        self.sleep = sleep_time
        self.set_process_launcher(Scheduler.Launchers.PYTHON)

    def _execute(self, *args, **kwargs):
        time.sleep(self.sleep)
        return self.package

    def get_input_keys(self):
        return self.keys

    def set_inputs(self, package):
        self.package = package


class TestPipeline(MonkeyIOTestBase, TestCase):
    def __init__(self, *args, **kwargs):
        MonkeyIOTestBase.__init__(self)
        TestCase.__init__(self, *args, **kwargs)

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.layers = []
        self.dataset_handles = []
        self.data_shape = (10, 10, 10, 32)
        self.channel_in = self._create_dataloader()
        self.channel_out = Collector(self.loop, DATA_KEYS)
        self.pipeline = Pipeline(self.channel_in, self.channel_out)

    def test_linear_pipeline_unique_units(self):
        for i in range(5):
            layer = SequenceLayer(
                Channel(self.loop, DATA_KEYS, name="l{}_chan_in".format(i)),
                Channel(self.loop, DATA_KEYS, name="l{}_chan_out".format(i)),
                name="layer_{}".format(i)
            )
            layer.add_unit(
                Unit(AwaitAndPassProcess(
                    DATA_KEYS, "proc_{}".format(i), "hello", 0
                ), "lfp", name="unit_{}".format(i))
            )
            self.pipeline.add_item(layer)

        dequeue_task = self.loop.create_task(self._dequeue_pipeline_output())

        self.pipeline.run()
        results = self.loop.run_until_complete(dequeue_task)
        self.pipeline.wait_for_completion()
        self._assert_results(results)

    def test_tree_pipeline_unique_units(self):
        pass

    def test_diamond_pipeline_unique_units(self):
        pass

    def test_big_pipeline_unique_units(self):
        pass

    async def _dequeue_pipeline_output(self):
        results = []
        output_sub = self.channel_out.get_output_subscriber()
        while output_sub.promise_data():
            try:
                results.append(await output_sub.yield_data())
            except asyncio.CancelledError:
                break

        assert not output_sub.promise_data()

        return results

    def _create_dataloader(self):
        self.dataset_handles.append(
            self.generate_hdf5_dataset(10, 5, self.data_shape)
        )
        return Dataloader(
            self.loop, [Dataset(self.dataset_handles[-1])], DATA_KEYS
        )

    def _assert_results(self, results):
        for id_tag, data in results:
            assert_data_point(data, self.data_shape)
