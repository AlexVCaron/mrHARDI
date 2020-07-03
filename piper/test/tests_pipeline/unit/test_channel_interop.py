import asyncio
from unittest import TestCase
from uuid import uuid4

from piper.comm import Channel
from piper.comm import Subscriber
from piper.comm.close_condition import CloseCondition
from piper.test.helpers.async_helpers import \
    async_close_channels_callback


class TestChannelInterop(TestCase):
    def setUp(self):
        self._loop = asyncio.get_event_loop()
        self._loop.set_debug(True)
        self.channel1 = Channel(["data"], name="Channel1")
        self.channel2 = Channel(["data"], name="Channel2")

    def test_single_link(self):
        sub_in = Subscriber("sub_in")
        sub_between = Subscriber("sub_between")
        sub_out = Subscriber("sub_out")

        async def close_subs():
            await sub_in.shutdown()

        end_cnd = CloseCondition()

        self.channel1.add_subscriber(sub_in, Channel.Sub.IN)
        self.channel1.add_subscriber(sub_between, Channel.Sub.OUT)
        self.channel2.add_subscriber(sub_between, Channel.Sub.IN)
        self.channel2.add_subscriber(sub_out, Channel.Sub.OUT)

        self.channel1.start(lambda: end_cnd)
        self.channel2.start(lambda: end_cnd)

        id_tag, data = uuid4(), {"data": "data"}
        transmit = self._loop.create_task(sub_in.transmit(id_tag, data))
        transmit.add_done_callback(
            async_close_channels_callback(close_subs, self._loop, end_cnd))

        results = self._loop.create_task(self._get_sub(sub_out))

        res_id_tag, res_data = self._loop.run_until_complete(results)

        assert res_id_tag == id_tag
        assert res_data == data

    async def _get_sub(self, sub):
        while sub.is_alive():
            return await sub.yield_data()

    async def _collect_results(self, task, end_cnd):
        await end_cnd
        result = await task
        return result
