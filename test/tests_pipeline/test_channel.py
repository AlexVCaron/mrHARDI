import asyncio
import time
from itertools import cycle
from unittest import TestCase
from uuid import uuid4

from multiprocess.pipeline.channel import Channel
from multiprocess.pipeline.close_condition import CloseCondition
from multiprocess.pipeline.subscriber import Subscriber
from test.tests_pipeline.helpers.async_helpers import \
    async_close_channels_callback


class TestChannel(TestCase):
    def setUp(self):
        self._loop = asyncio.new_event_loop()
        self._loop.set_debug(True)

        self.sub_in = list()
        self.sub_out = list()

        self.channel = Channel(self._loop, ["data"])

    def tearDown(self):
        time.sleep(2)
        if self.channel.has_started():
            assert not self.channel.running()
        self._loop.stop()
        self._loop.close()

    def test_start(self):
        end_cnd = CloseCondition()
        self._setup_subscribers(1, 1)
        self.channel.start(lambda: end_cnd)

        shutdown = self._loop.create_task(self.sub_in[0].shutdown())
        shutdown.add_done_callback(lambda *args: end_cnd.set())

        self._loop.run_until_complete(self.channel.wait_for_completion())

        assert not self.channel.running()

    def test_has_inputs(self):
        assert not self.channel.has_inputs()
        self._setup_subscribers(1, 2)
        assert self.channel.has_inputs()

    def test_one_to_one_flow(self):
        id_tag, data = uuid4(), self._basic_data_package()

        self._setup_subscribers(1, 1)
        results = self._run_test([(id_tag, data)])

        self._assert_data_points(results, {id_tag: data}, 1)
        self._assert_output_subscribers()

    def test_one_to_many_flow(self):
        id_tag1, data1 = uuid4(), self._basic_data_package("data2")
        id_tag2, data2 = uuid4(), self._basic_data_package("data1")

        self._one_to_many(((id_tag1, data1), (id_tag2, data2)), 2)

    def test_one_to_many_flow_bcast(self):
        self.channel = Channel(self._loop, ["data"], True)

        id_tag, data = uuid4(), self._basic_data_package()

        self._one_to_many(((id_tag, data),), 2)

    def test_many_to_one_flow(self):
        id_tag1, data1 = uuid4(), self._basic_data_package("data2")
        id_tag2, data2 = uuid4(), self._basic_data_package("data1")

        self._many_to_one(((id_tag1, data1), (id_tag2, data2)), n=2)

    def test_many_to_one_flow_partial(self):
        self.channel = Channel(self._loop, ["data1", "data2"])

        id_tag = uuid4()
        data1, data2 = {"data1": "data1"}, {"data2": "data2"}

        self._many_to_one(
            ((id_tag, data1), (id_tag, data2)),
            ((id_tag, {**data1, **data2}),),
            1
        )

    def test_many_to_many_flow(self):
        id_tag1, data1 = uuid4(), self._basic_data_package("data1")
        id_tag2, data2 = uuid4(), self._basic_data_package("data2")

        self._many_to_many(((id_tag1, data1), (id_tag2, data2)), n=2)

    def test_many_to_many_flow_bcast(self):
        self.channel = Channel(self._loop, ["data"], True)
        id_tag1, data1 = uuid4(), self._basic_data_package("data2")
        id_tag2, data2 = uuid4(), self._basic_data_package("data1")

        self._many_to_many(
            ((id_tag1, data1), (id_tag2, data2)), n=4
        )

    def test_many_to_many_flow_partial(self):
        self.channel = Channel(self._loop, ["data1", "data2"])

        id_tag1, id_tag2 = uuid4(), uuid4()
        data11, data12 = {"data1": "data11"}, {"data2": "data12"}
        data21, data22 = {"data1": "data21"}, {"data2": "data22"}

        self._many_to_many(
            (
                (id_tag1, data11), (id_tag1, data12),
                (id_tag2, data21), (id_tag2, data22),
            ),
            (
                (id_tag1, {**data11, **data12}),
                (id_tag2, {**data21, **data22})
            ),
            2
        )

    def test_many_to_many_flow_partial_bcast(self):
        self.channel = Channel(self._loop, ["data1", "data2"], True)

        id_tag1, id_tag2 = uuid4(), uuid4()
        data11, data12 = {"data1": "data11"}, {"data2": "data12"}
        data21, data22 = {"data1": "data21"}, {"data2": "data22"}

        self._many_to_many(
            (
                (id_tag1, data11), (id_tag1, data12),
                (id_tag2, data21), (id_tag2, data22),
            ),
            (
                (id_tag1, {**data11, **data12}),
                (id_tag2, {**data21, **data22})
            ),
            4
        )

    def _setup_subscribers(self, n_in, n_out):
        self.sub_in = list(Subscriber(
            name="Sub_in{}".format(i)
        ) for i in range(n_in))

        self.sub_out = list(Subscriber(
            name="Sub_out{}".format(i)
        ) for i in range(n_out))

        for sub in self.sub_in:
            self.channel.add_subscriber(sub, Channel.Sub.IN)

        for sub in self.sub_out:
            self.channel.add_subscriber(sub, Channel.Sub.OUT)

    def _run_test(self, data_points):
        end_cnd = CloseCondition()

        self.channel.start(lambda: end_cnd)

        trans = self._loop.create_task(
            self._transmit_data(data_points)
        )
        trans.add_done_callback(
            async_close_channels_callback(self._close_connections, self._loop,
                                          end_cnd))

        results = self._loop.create_task(
            self._get_results()
        )

        self._loop.run_until_complete(
            self.channel.wait_for_completion()
        )
        self._loop.run_until_complete(results)
        return results.result()

    async def _collect_results(self, task, end_cnd):
        await end_cnd
        return await task

    def _one_to_many(self, data_points, n):
        self._setup_subscribers(1, 2)
        results = self._run_test(data_points)
        self._assert_data_points(results, dict(data_points), n)
        self._assert_output_subscribers()
        self._assert_channel()

    def _many_to_one(self, data_points, ret_data=None, n=2):
        self._setup_subscribers(2, 1)
        results = self._run_test(data_points)
        self._assert_data_points(
            results, dict(ret_data if ret_data else data_points), n
        )
        self._assert_output_subscribers()
        self._assert_channel()

    def _many_to_many(self, data_points, ret_data=None, n=0):
        self._setup_subscribers(2, 2)
        results = self._run_test(data_points)
        self._assert_data_points(
            results, dict(ret_data if ret_data else data_points), n
        )
        self._assert_output_subscribers()
        self._assert_channel()

    async def _transmit_data(self, data_points):
        for trans in asyncio.as_completed([
            sub.transmit(*data)
            for sub, data in zip(cycle(self.sub_in), data_points)
        ]):
            await trans

    async def _close_connections(self):
        for sub in self.sub_in:
            await sub.shutdown()

    async def _get_results(self):
        results = []
        alive = True
        for s in self.sub_out:
            alive = alive and s.is_alive()

        while alive:
            for input in filter(lambda s: s.is_alive() or s.data_ready(), self.sub_out):
                try:
                    ret_id_tag, ret_data = await input.yield_data()
                    results.append((ret_id_tag, ret_data))
                except asyncio.CancelledError:
                    pass

            for s in self.sub_out:
                alive = alive and s.is_alive()

            await asyncio.sleep(0)

        return results

    def _basic_data_package(self, value="data"):
        return {"data": value}

    def _assert_data_points(self, data, awaited_data, awaited_n):
        i = 0
        for id_tag, dt in data:
            assert id_tag in awaited_data.keys()
            assert awaited_data[id_tag] == dt
            i += 1

        assert i == awaited_n, "{} data points received versus {}".format(
            i, awaited_n
        )

    def _assert_output_subscribers(self):
        time.sleep(1)
        for sub in self.sub_out:
            assert not sub.is_alive()

    def _assert_channel(self):
        self._loop.run_until_complete(
            self.channel.wait_for_completion()
        )
        assert not self.channel.running()
