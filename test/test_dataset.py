from functools import partial
from unittest import TestCase

from moneky_io.dataset import Dataset
from test.helpers.data import create_hdf5_dataset, create_pipeline_input_subject, create_pipeline_input_rep, \
    assert_data_point


class TestDataset(TestCase):
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

        for id, data in self.dataset:
            assert id not in loaded_ids
            assert_data_point(data, self.data_shape)

            loaded_ids.append(id)

        assert len(self.dataset) == 50

    def test_yield_single_data(self):
        id, data = self.dataset.yield_data()
        assert_data_point(data, self.data_shape)

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

    def generate_hdf5_dataset(
        self, n_subs, n_reps, shape, prefix=None,
        init_val=None, single_anat=True, single_mask=True
    ):
        sub_fn = partial(
            create_pipeline_input_subject,
            shape=shape, init_val=init_val,
            single_anat=single_anat,
            single_mask=single_mask
        )

        rep_fn = partial(
            create_pipeline_input_rep,
            shape=shape, init_val=init_val,
            mask=not single_mask, anat=not single_anat
        )

        return create_hdf5_dataset(
            n_subs, n_reps, prefix, rep_fn, sub_fn
        )
