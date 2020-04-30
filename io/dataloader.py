import uuid
from random import randint

import h5py

from multiprocess.pipeline.subscriber import Subscriber


class Dataloader(Subscriber):
    def __init__(self, h5_archive, cache_len=3, prepare_dataset_fn=None):
        super().__init__()
        self._archive = h5_archive
        self._cache = {}
        self._cache_len = cache_len
        self._infos = {}
        self._ids = None

        if prepare_dataset_fn:
            self._prepare_dataset = prepare_dataset_fn

        self._initialize()

    def data_ready(self):
        return True

    def yield_data(self):
        id = next(self._ids)
        return id, self._get_package(id)

    def __iter__(self):
        for id in self._ids:
            yield id, self._get_package(id)

    def _get_package(self, id):
        if id not in self._cache.keys():
            with h5py.File(self._archive, "r") as archive:
                infos = self._infos[id]
                dataset = archive[infos["subject"]][infos["rep"]]
                self._add_to_cache(id, dataset)

        return self._cache[id]

    def _initialize(self):
        ids = []

        with h5py.File(self._archive, "r") as archive:
            for subject, group in archive:
                for rep, dataset in group:
                    id = uuid.uuid4()
                    self._infos[id] = {
                        "subject": subject,
                        "rep": rep
                    }
                    ids.append(id)

                    if len(self._cache) < self._cache_len:
                        self._add_to_cache(id, dataset)

        self._ids = iter(ids)

    def _add_to_cache(self, id, dataset):
        if len(self._cache) + 1 == self._cache_len:
            del_key = list(self._cache.keys())[randint(0, self._cache_len)]
            self._cache.pop(del_key)

        self._cache[id] = self._prepare_dataset(dataset)

    def _prepare_dataset(self, dataset):
        return dataset
