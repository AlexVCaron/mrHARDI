import asyncio
import uuid
from random import randint

import h5py

from multiprocess.exceptions import NotImplementedException
from multiprocess.pipeline.subscriber import Subscriber


class Dataset(Subscriber):
    def __init__(
        self, h5_archive, cache_len=3, prepare_data_fn=None,
        single_anat=True, single_mask=True
    ):
        super().__init__(name="dataset")
        self._archive = h5_archive
        self._cache = {}
        self._cache_len = cache_len
        self._infos = {}
        self._ids = None
        self._subject_infos = {}
        self._single_anat = single_anat
        self._single_mask = single_mask
        self._empty = False

        if prepare_data_fn:
            self._prepare_data = prepare_data_fn

        self._initialize()

    def __len__(self):
        return len(self._infos)

    def data_ready(self):
        return not self.empty()

    def empty(self):
        return self._empty

    async def yield_data(self):
        try:
            id = next(self._ids)
            return id, self._get_package(id)
        except StopIteration:
            self._empty = True
            await self.shutdown()
            raise asyncio.CancelledError()

    async def transmit(self, id_tag, package):
        raise NotImplementedException(
            "Dataset does not provide an insert method"
        )

    def __iter__(self):
        for id in self._ids:
            yield id, self._get_package(id)

        self._empty = True

    def _get_package(self, id):
        if id not in self._cache.keys():
            with h5py.File(self._archive, "r") as archive:
                infos = self._infos[id]
                data = archive[infos["subject"]][infos["rep"]]
                self._add_to_cache(id, data)

        extras, subject_id = {}, self._infos[id]["subject"]
        if subject_id in self._subject_infos.keys():
            extras.update(self._subject_infos[subject_id])

        return {**self._cache[id], **extras}

    def _initialize(self):
        ids = []

        with h5py.File(self._archive, "r") as archive:
            for subject, group in archive.items():
                gp = dict(group)
                self._subject_infos[subject] = {}
                if self._single_anat:
                    self._subject_infos[subject]["anat"] = gp.pop("anat")[()]
                if self._single_mask:
                    self._subject_infos[subject]["mask"] = gp.pop("mask")[()]

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

        self._cache[id] = self._prepare_data(self._unpack(data))

    def _unpack(self, data):
        return {
            k: v[()] for k, v in data.items()
        }

    def _prepare_data(self, data):
        return data
