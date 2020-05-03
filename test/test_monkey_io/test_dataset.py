from unittest import TestCase

from moneky_io.dataset import Dataset
from test.test_monkey_io.helpers.monkey_io_test_base import MonkeyIOTestBase
from test.test_monkey_io.helpers.data import assert_data_point


class TestDataset(TestCase, MonkeyIOTestBase):
    def setUp(self):
        self.data_shape = (10, 10, 10, 32)
        self.dataset_handle = self.generate_hdf5_dataset(
            10, 5, self.data_shape
        )
        self.dataset = Dataset(self.dataset_handle)

    def tearDown(self):
        self.dataset_handle.close()

    def test_create_dataset(self):
        loaded_ids = []

        assert self.dataset.data_ready()

        for id, data in self.dataset:
            assert id not in loaded_ids
            assert_data_point(data, self.data_shape)

            loaded_ids.append(id)

        assert len(self.dataset) == 50
        assert self.dataset.empty()
        assert not self.dataset.data_ready()

    def test_yield_single_data(self):
        id, data = self.dataset.yield_data()
        assert_data_point(data, self.data_shape)

    def test_modify_single_data(self):
        def prep_fn(data):
            data["mask"] = data.pop("img")
            return data

        self.dataset = Dataset(
            self.dataset_handle, prepare_data_fn=prep_fn
        )

        id, data = self.dataset.yield_data()
        assert_data_point(data, self.data_shape, {"img": "mask"})

    def test_yield_all_data(self):
        i = 0

        for i in range(len(self.dataset)):
            id, data = self.dataset.yield_data()
            assert_data_point(data, self.data_shape)

        assert i == 49

    def test_yield_more_data_will_fail(self):
        self.assertRaises(
            StopIteration, self._loop_dataloader,
            lambda: self.dataset.yield_data(), 51
        )

    def _loop_dataloader(self, dataloader_fn, n):
        for i in range(n):
            dataloader_fn()
