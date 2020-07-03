import asyncio
import time
from unittest import TestCase

from helpers.data import DATA_KEYS, assert_data_point
from helpers.monkey_io_test_base import MonkeyIOTestBase
from monkey_io.dataloader import Dataloader
from monkey_io.h5dataset import H5Dataset
from piper.comm import Channel
from piper.comm import Collector
from piper.comm import Subscriber
from piper.pipeline import SequenceLayer
from piper.pipeline.pipeline import Pipeline
from piper.pipeline.process import PythonProcess
from piper.pipeline.unit import Unit


# TODO : remove dependencies on MonkeyIO and move to piper


class AwaitAndPassProcess(PythonProcess):
    def __init__(self, package_keys, name, output_prefix, sleep_time=5):
        super().__init__(name, output_prefix)
        self.package = None
        self.keys = package_keys
        self.sleep = sleep_time

    def _execute(self, *args, **kwargs):
        time.sleep(self.sleep)
        return self.package

    def get_required_output_keys(self):
        return self.get_input_keys()

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
        self.sub_out = Subscriber()
        self.channel_out.add_subscriber(self.sub_out, Channel.Sub.OUT)
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
        while self.sub_out.promise_data():
            try:
                results.append(await self.sub_out.yield_data())
            except asyncio.CancelledError:
                break

        assert not self.sub_out.promise_data()

        return results

    def _create_dataloader(self):
        self.dataset_handles.append(
            self.generate_hdf5_dataset(10, 5, self.data_shape)
        )
        return Dataloader(
            self.loop, [H5Dataset(self.dataset_handles[-1])], DATA_KEYS
        )

    def _assert_results(self, results):
        for id_tag, data in results:
            assert_data_point(data, self.data_shape)
