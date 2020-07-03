import logging

from .channel import Channel


class Collector(Channel):
    def __init__(
        self, package_keys, integrate_data_fn=None,
        broadcast_out=False, name="collector"
    ):
        super().__init__(package_keys, broadcast_out, name)
        self._idle_packages = []

        if integrate_data_fn:
            self._integrate_data = integrate_data_fn

    async def _yield(self, sub):
        id_tag, data = self._integrate_data(
            *(await sub.yield_data()), self._idle_packages
        )

        if id_tag and data is not None:
            self._idle_packages.append((id_tag, data))

        return id_tag

    def _get_package(self, id_tag, *args, remove_from_queue=True):
        result = next(filter(
            lambda val: val[0] == id_tag and self._data_complete(val[1]),
            self._idle_packages
        ))

        if remove_from_queue:
            index = self._idle_packages.index(result)
            self._idle_packages.pop(index)

        return result[1]

    def _data_complete(self, data):
        return all(k in data for k in self._package_keys)

    def _integrate_data(self, id_tag, data, idle_packages):
        return id_tag, data

    def _is_complete(self, id_tag):
        try:
            self._get_package(id_tag, remove_from_queue=False)
        except StopIteration:
            return False

        return True


logger = logging.getLogger(Collector.__name__)
