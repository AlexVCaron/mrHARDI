import logging

from .collector import Collector


class Gatherer(Collector):
    def __init__(
        self, data_complete_fn,
        prepare_output=lambda data: data, name="gatherer"
    ):
        super().__init__([], name=name)

        self._prep_out = prepare_output
        self._data_complete = data_complete_fn
        self._idle_packages = {}

    def _get_package(self, id_tag, *args, **kwargs):
        return self._idle_packages[id_tag]

    def _is_complete(self, id_tag):
        return self._data_complete(self._idle_packages[id_tag])

    async def _yield(self, sub):
        id_tag, data = await sub.yield_data()

        if id_tag:
            if id_tag not in self._idle_packages:
                self._idle_packages[id_tag] = []

            self._idle_packages[id_tag].append(data)

        return id_tag


logger = logging.getLogger(Gatherer.__name__)