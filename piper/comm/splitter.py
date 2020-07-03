import asyncio
import logging

from .channel import Channel


class Splitter(Channel):
    def __init__(self, input_subscriber, name="splitter"):
        super().__init__(None, name=name)

        self._partitions = []
        super().add_subscriber(input_subscriber)
        self._is_complete = lambda *args: True

    def add_subscriber(self, sub, key_partition=None, type=Channel.Sub.OUT):
        assert type == Channel.Sub.OUT
        assert key_partition is not None

        self._partitions.append((sub, key_partition))

    async def _transmit(self, id_tag, package):
        for fut in asyncio.as_completed([
            sub.transmit(id_tag, {k: package[k] for k in part})
            for sub, part in self._partitions
        ]):
            await fut

    def _attempt_shutdown(self):
        self._subscribers[Channel.Sub.OUT] = [p[0] for p in self._partitions]
        super()._attempt_shutdown()


logger = logging.getLogger(Splitter.__name__)
