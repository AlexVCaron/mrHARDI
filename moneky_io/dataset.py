import uuid
from random import randint

import h5py

from multiprocess.pipeline.subscriber import Subscriber


class Dataset(Subscriber):
    def __init__(
        self, h5_archive, cache_len=3, prepare_data_fn=None,
        single_anat=True, single_mask=True
    ):
        super().__init__()
        self._archive = h5_archive
        self._cache = {}
        self._cache_len = cache_len
        self._infos = {}
        self._ids = None
        self._extras = {}
        self._single_anat = single_anat
        self._single_mask = single_mask

        if prepare_data_fn:
            self._prepare_data = prepare_data_fn

        self._initialize()

    def __len__(self):
        return len(self._infos)

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
                data = archive[infos["subject"]][infos["rep"]]
                self._add_to_cache(id, data)

        return self._cache[id]

    def _initialize(self):
        ids = []

        with h5py.File(self._archive, "r") as archive:
            for subject, group in archive.items():
                gp = dict(group)
                self._extras[subject] = {}
                if self._single_anat:
                    self._extras[subject]["anat"] = gp.pop("anat")
                if self._single_mask:
                    self._extras[subject]["mask"] = gp.pop("mask")

                for rep, data in gp.items():
                    id = uuid.uuid4()
                    self._infos[id] = {
                        "subject": subject,
                        "rep": rep
                    }
                    ids.append(id)

                    if len(self._cache) < self._cache_len:
                        self._add_to_cache(id, data)

        self._ids = iter(ids)

    def _add_to_cache(self, id, data):
        if len(self._cache) == self._cache_len:
            del_key = list(self._cache.keys())[randint(0, self._cache_len - 1)]
            self._cache.pop(del_key)

        self._cache[id] = self._prepare_data(data)

    def _prepare_data(self, data):
        return {
            k: v[()] for k, v in data.items()
        }
