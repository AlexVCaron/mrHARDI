import asyncio
import uuid

from abc import ABCMeta, abstractmethod
from random import randint

from piper import metadata_manager
from piper.comm import Subscriber
from piper.exceptions import NotImplementedException


class Dataset(Subscriber, metaclass=ABCMeta):
    def __init__(
        self, cache_len=3, prepare_data_fn=None, add_subject_info_fn=None,
        single_anat=True, single_mask=True, name="dataset"
    ):
        super().__init__(name)

        self._cache = {}
        self._cache_len = cache_len
        self._infos = {}
        self._subject_infos = {}
        self._single_anat = single_anat
        self._single_mask = single_mask
        self._empty = False

        if prepare_data_fn:
            self._prepare_data = prepare_data_fn

        if add_subject_info_fn:
            self._additional_subject_infos = add_subject_info_fn

        self._initialize()
        self._ids = iter(self._infos.keys())

    @abstractmethod
    def _initialize(self):
        pass

    @abstractmethod
    def _load_into_cache(self, id, subject, rep, **kwargs):
        pass

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
            self._load_into_cache(id, **self._infos[id])

        extras, subject_id = {}, self._infos[id]["subject"]
        if subject_id in self._subject_infos.keys():
            extras.update(self._subject_infos[subject_id])

        return {**self._cache[id], **extras}

    def _add_subject_info(
        self, subject_id, rep_list, load_rep_fn,
        single_anat=None, single_mask=None
    ):
        self._subject_infos[subject_id] = {}

        if single_anat is not None:
            self._subject_infos[subject_id]["anat"] = single_anat
        if single_mask is not None:
            self._subject_infos[subject_id]["mask"] = single_mask

        self._subject_infos[subject_id]["n_rep"] = len(rep_list)

        self._subject_infos[subject_id] = self._additional_subject_infos(
            subject_id, self._subject_infos[subject_id]
        )

        metadata_manager.register_category(
            subject_id, self._subject_infos[subject_id]
        )

        for rep_id in rep_list:
            id = str(uuid.uuid4())

            self._infos[id] = {
                "subject": subject_id,
                "rep": rep_id
            }

            metadata_manager.register_category(
                id, self._infos[id], lambda meta, manager: {
                    **meta, **manager.get_category(meta["subject"])
                }
            )

            if len(self._cache) < self._cache_len:
                self._add_to_cache(id, load_rep_fn(rep_id))

    def _add_to_cache(self, id, data):
        if len(self._cache) == self._cache_len:
            del_key = list(self._cache.keys())[randint(0, self._cache_len - 1)]
            self._cache.pop(del_key)

        self._cache[id] = self._prepare_data(self._data_to_dict(data))

    def _additional_subject_infos(self, subject_id, subject_infos):
        return subject_infos

    def _prepare_data(self, data):
        return data

    def _data_to_dict(self, data):
        return dict(data)
