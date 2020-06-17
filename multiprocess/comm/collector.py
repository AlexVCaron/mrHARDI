import logging

from multiprocess.comm.channel import Channel
from multiprocess.comm.subscriber import Subscriber


class Collector(Channel):
    def __init__(self, main_loop, package_keys, name="collector"):
        super().__init__(main_loop, package_keys, name=name)
        self._subscribers[Channel.Sub.OUT] = [Subscriber(
            name="{}_out_sub".format(name)
        )]
        self._idle_packages = []

    def get_output_subscriber(self):
        return self._subscribers[Channel.Sub.OUT][0]

    def add_subscriber(self, sub, type=Channel.Sub.IN):
        assert type is Channel.Sub.IN
        super().add_subscriber(sub)

    async def _yield(self, sub):
        id_tag, data = await sub.yield_data()

        if id_tag:
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

    def _is_complete(self, id_tag):
        try:
            self._get_package(id_tag, remove_from_queue=False)
        except StopIteration:
            return False

        return True


logger = logging.getLogger(Collector.__name__)
