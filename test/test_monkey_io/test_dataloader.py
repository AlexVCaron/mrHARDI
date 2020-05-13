from unittest import TestCase

from moneky_io.dataloader import Dataloader
from moneky_io.dataset import Dataset
from multiprocess.pipeline.channel import Channel
from multiprocess.pipeline.subscriber import Subscriber
from test.test_monkey_io.helpers.data import DATA_KEYS, assert_data_point
from test.test_monkey_io.helpers.monkey_io_test_base import MonkeyIOTestBase


class TestDataloader(TestCase, MonkeyIOTestBase):
    def setUp(self):
        self.dataset_handles = []
        self.data_shape = (10, 10, 10, 32)
        self.dataloader = self._create_dataloader()

    def tearDown(self):
        for handle in self.dataset_handles:
            handle.close()

    def test_pool_data_package(self):
        output_sub = Subscriber()
        self.dataloader.add_subscriber(output_sub, Channel.Sub.OUT)
        self.dataloader.prepare_iterators()

        self.dataloader.pool_data_package()

        assert output_sub.data_ready()
        id, data = output_sub.yield_data()
        assert_data_point(data, self.data_shape)

    def test_threaded_data_package(self):
        output_sub = Subscriber()
        self.dataloader.add_subscriber(output_sub, Channel.Sub.OUT)

        stop_cond = [False, True]
        self._run_threaded_test([output_sub], lambda: stop_cond.pop(0), 1)

    def test_threaded_all(self):
        output_sub = Subscriber()
        self.dataloader.add_subscriber(output_sub, Channel.Sub.OUT)
        self._run_threaded_test([output_sub], lambda: False, 50)

    def test_threaded_multi_source_all(self):
        output_sub = Subscriber()
        self.dataloader.add_subscriber(output_sub, Channel.Sub.OUT)

        for i in range(2):
            self.dataset_handles.append(
                self.generate_hdf5_dataset(10, 5, self.data_shape)
            )
            self.dataloader.add_subscriber(
                Dataset(self.dataset_handles[-1]),
                Channel.Sub.IN
            )

        self._run_threaded_test([output_sub], lambda: False, 150)

    def test_threaded_multi_output_all(self):
        output_subs = [Subscriber() for i in range(3)]
        for sub in output_subs:
            self.dataloader.add_subscriber(sub, Channel.Sub.OUT)

        self._run_threaded_test(output_subs, lambda: False, 150)

    def test_threaded_multi_source_multi_output_all(self):
        output_subs = [Subscriber() for i in range(3)]
        for sub in output_subs:
            self.dataloader.add_subscriber(sub, Channel.Sub.OUT)

        for i in range(2):
            self.dataset_handles.append(
                self.generate_hdf5_dataset(10, 5, self.data_shape)
            )
            self.dataloader.add_subscriber(
                Dataset(self.dataset_handles[-1]),
                Channel.Sub.IN
            )

        self._run_threaded_test(output_subs, lambda: False, 450)

    def test_threaded_multi_source_multi_output(self):
        output_subs = [Subscriber() for i in range(3)]
        for sub in output_subs:
            self.dataloader.add_subscriber(sub, Channel.Sub.OUT)

        for i in range(3):
            self.dataset_handles.append(
                self.generate_hdf5_dataset(10, 5, self.data_shape)
            )
            self.dataloader.add_subscriber(
                Dataset(self.dataset_handles[-1]),
                Channel.Sub.IN
            )

        stop_cond = [False, False, False, True]
        self._run_threaded_test(output_subs, lambda: stop_cond.pop(0), 9)

    def test_threaded_multi_output(self):
        output_subs = [Subscriber() for i in range(3)]
        for sub in output_subs:
            self.dataloader.add_subscriber(sub, Channel.Sub.OUT)

        stop_cond = [False, True]
        self._run_threaded_test(output_subs, lambda: stop_cond.pop(0), 3)

    def test_threaded_multi_source_full_same_len(self):
        output_sub = Subscriber()
        self.dataloader.add_subscriber(output_sub, Channel.Sub.OUT)

        for i in range(3):
            self.dataset_handles.append(
                self.generate_hdf5_dataset(10, 5, self.data_shape)
            )
            self.dataloader.add_subscriber(
                Dataset(self.dataset_handles[-1]),
                Channel.Sub.IN
            )

        stop_cond = [False, False, False, True]
        self._run_threaded_test([output_sub], lambda: stop_cond.pop(0), 3)

    def test_threaded_multi_source_full(self):
        output_sub = Subscriber()
        self.dataloader.add_subscriber(output_sub, Channel.Sub.OUT)

        for i in range(3):
            self.dataset_handles.append(
                self.generate_hdf5_dataset(
                    (i + 1) * 3, (i + 1) * 2, self.data_shape
                )
            )
            self.dataloader.add_subscriber(
                Dataset(self.dataset_handles[-1]),
                Channel.Sub.IN
            )

        stop_cond = [False, False, False, True]
        self._run_threaded_test([output_sub], lambda: stop_cond.pop(0), 3)

    def _assert_output_subs(self, output_subs, i):
        for output_sub in output_subs:
            while output_sub.data_ready():
                id, data = output_sub.yield_data()
                assert_data_point(data, self.data_shape)
                i += 1

        return i

    def _run_threaded_test(self, output_subs, stop_cond, awaited_outputs):
        self.dataloader.start(stop_cond)

        i = 0
        while self.dataloader.running():
            i = self._assert_output_subs(output_subs, i)

        i = self._assert_output_subs(output_subs, i)
        for output_sub in output_subs:
            assert not output_sub.data_ready()

        assert not self.dataloader.running()

        self._assert_subs_closed(output_subs)

        assert i == awaited_outputs, "Awaited {} outputs, got {}".format(
            awaited_outputs, i
        )

    def _assert_subs_closed(self, subs):
        for sub in subs:
            assert not sub.is_alive()


    def _create_dataloader(self):
        self.dataset_handles.append(
            self.generate_hdf5_dataset(10, 5, self.data_shape)
        )
        return Dataloader([Dataset(self.dataset_handles[-1])], DATA_KEYS)
