import asyncio
import time
from functools import partial
from itertools import cycle
from threading import Thread
from unittest import TestCase
from uuid import uuid4

from multiprocess.pipeline.channel import Channel
from multiprocess.pipeline.sentinel import Sentinel
from multiprocess.pipeline.subscriber import Subscriber


class TestChannel(TestCase):
    def setUp(self):
        self._event_loop = asyncio.get_event_loop()
        self._event_loop.set_debug(True)

        self.sub_in = [Subscriber()]
        self.sub_out = [Subscriber()]

        self.channel = Channel(self._event_loop, ["data"])
        self.channel.add_subscriber(self.sub_in[0], Channel.Sub.IN)
        self.channel.add_subscriber(self.sub_out[0], Channel.Sub.OUT)

    def tearDown(self):
        time.sleep(2)
        assert not self.channel.running()

    def test_start(self):
        def assert_end():
            assert not self.channel.running()

        end_cnd = False
        future = self.channel.start(lambda: end_cnd)
        future.add_done_callback(assert_end)

        self._start_event_loop()

        end_cnd = True
        asyncio.run_coroutine_threadsafe(self.sub_in[0].shutdown(), self._event_loop)

    def test_has_inputs(self):
        assert self.channel.has_inputs()

        channel = Channel(["data"])
        assert not channel.has_inputs()

    def test_one_to_one_flow(self):
        id_tag, data = uuid4(), self._basic_data_package()
        end_cnd = False
        # self._start_event_loop()
        future = self.channel.start(self._event_loop, lambda: end_cnd)

        t = asyncio.run_coroutine_threadsafe(self.sub_in[0].transmit(id_tag, data), self._event_loop)
        f = asyncio.run_coroutine_threadsafe(self._get_results(), self._event_loop)

        def closing(fn, loop, *args, **kwargs):
            global end_cnd
            end_cnd = True
            asyncio.run_coroutine_threadsafe(fn, loop)

        t.add_done_callback(partial(closing, fn=self._close_connections, loop=self._event_loop))

        # while f.running():
        #     time.sleep(1)

        ret_data = f.result()
        self._assert_data_point(ret_data, {id_tag: data})

        asyncio.run_coroutine_threadsafe(self._assert_output_subscribers(), self._event_loop)

    def test_one_to_many_flow(self):
        self.add_output_subscribers([Subscriber()])
        self.channel.add_subscriber(self.sub_out[-1], Channel.Sub.OUT)

        id_tag1, data1 = uuid4(), self._basic_data_package("data2")
        id_tag2, data2 = uuid4(), self._basic_data_package("data1")

        self._one_to_many(((id_tag1, data1), (id_tag2, data2)))

    def test_one_to_many_flow_bcast(self):
        self.add_output_subscribers([Subscriber()])
        self.channel = Channel(["data"], True)

        self.channel.add_subscriber(self.sub_in[0], Channel.Sub.IN)
        for sub in self.sub_out:
            self.channel.add_subscriber(sub, Channel.Sub.OUT)

        id_tag, data = uuid4(), self._basic_data_package()

        self._one_to_many(((id_tag, data),))

    def test_many_to_one_flow(self):
        self.add_input_subscribers([Subscriber()])
        self.channel.add_subscriber(self.sub_in[-1], Channel.Sub.IN)

        id_tag1, data1 = uuid4(), self._basic_data_package("data2")
        id_tag2, data2 = uuid4(), self._basic_data_package("data1")

        self._many_to_one(((id_tag1, data1), (id_tag2, data2)))

    def test_many_to_one_flow_partial(self):
        self.channel = Channel(["data1", "data2"])
        self.channel.add_subscriber(self.sub_out[0], Channel.Sub.OUT)

        self.add_input_subscribers([Subscriber()])
        for sub in self.sub_in:
            self.channel.add_subscriber(sub, Channel.Sub.IN)

        id_tag = uuid4()
        data1, data2 = {"data1": "data1"}, {"data2": "data2"}

        self._many_to_one(
            ((id_tag, data1), (id_tag, data2)),
            ((id_tag, {**data1, **data2}),)
        )

    def test_many_to_many_flow(self):
        self.add_input_subscribers([Subscriber()])
        self.channel.add_subscriber(self.sub_in[-1], Channel.Sub.IN)
        self.add_output_subscribers([Subscriber()])
        self.channel.add_subscriber(self.sub_out[-1], Channel.Sub.OUT)

        id_tag1, data1 = uuid4(), self._basic_data_package("data2")
        id_tag2, data2 = uuid4(), self._basic_data_package("data1")

        self._many_to_many(((id_tag1, data1), (id_tag2, data2)))

    def test_many_to_many_flow_bcast(self):
        self.channel = Channel(["data"], True)
        self.add_input_subscribers([Subscriber()])
        for sub in self.sub_in:
            self.channel.add_subscriber(sub, Channel.Sub.IN)
        self.add_output_subscribers([Subscriber()])
        for sub in self.sub_out:
            self.channel.add_subscriber(sub, Channel.Sub.OUT)

        id_tag1, data1 = uuid4(), self._basic_data_package("data2")
        id_tag2, data2 = uuid4(), self._basic_data_package("data1")

        self._many_to_many(
            ((id_tag1, data1), (id_tag2, data2))
        )

    def test_many_to_many_flow_partial(self):
        self.channel = Channel(["data1", "data2"])
        self.add_input_subscribers([Subscriber()])
        for sub in self.sub_in:
            self.channel.add_subscriber(sub, Channel.Sub.IN)
        self.add_output_subscribers([Subscriber()])
        for sub in self.sub_out:
            self.channel.add_subscriber(sub, Channel.Sub.OUT)

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
            )
        )

    def test_many_to_many_flow_partial_bcast(self):
        self.channel = Channel(["data1", "data2"], True)
        self.add_input_subscribers([Subscriber()])
        for sub in self.sub_in:
            self.channel.add_subscriber(sub, Channel.Sub.IN)
        self.add_output_subscribers([Subscriber()])
        for sub in self.sub_out:
            self.channel.add_subscriber(sub, Channel.Sub.OUT)

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
            )
        )

    def add_input_subscribers(self, subs):
        for sub in subs:
            self.sub_in.append(sub)

    def add_output_subscribers(self, subs):
        for sub in subs:
            sub.listen_for_data(self.out_event)
            self.sub_out.append(sub)

    def _basic_data_package(self, value="data"):
        return {"data": value}

    async def _close_connections(self):
        for sub in self.sub_in:
            await sub.shutdown()

    async def _get_results(self):
        results = {}
        alive = True
        for s in self.sub_out:
            alive = alive and await s.is_alive()

        while alive:
            for input in self.sub_out:
                while await input.data_ready():
                    ret_id_tag, ret_data = await input.yield_data()
                    results[ret_id_tag] = ret_data

            for s in self.sub_out:
                alive = alive and await s.is_alive()

        return results

    def _assert_data_point(self, data, awaited_data):
        i = 0
        for id_tag, dt in data.items():
            assert id_tag in awaited_data.keys()
            assert awaited_data[id_tag] == dt
            i += 1

        assert i > 0

    def _assert_many_out(self, data_points):
        while any(s.is_alive() for s in self.sub_out):
            self._assert_data_point(dict(data_points))

        print("Assert has ended")

    def _many_to_one(self, data_points, ret_data=None):
        threads = []

        end_cnd = False
        self.channel.start(lambda: end_cnd)

        in_iter = cycle(self.sub_in)
        for data in data_points:
            next(in_iter).transmit(*data)

        for data in ret_data if ret_data else data_points:
            threads.append(Thread(target=self._assert_data_point, args=(dict((data,)),)))
            threads[-1].start()

        end_cnd = True
        self._close_connections()

        for th in threads:
            th.join()

        self._assert_output_subscribers()

    def _one_to_many(self, data_points):
        end_cnd = False
        self.channel.start(lambda: end_cnd)

        for data in data_points:
            self.sub_in[0].transmit(*data)

        th = Thread(target=self._assert_many_out, args=(data_points,))
        th.start()

        end_cnd = True
        self._close_connections()
        th.join()

        self._assert_output_subscribers()

    def _many_to_many(self, data_points, ret_data=None):
        end_cnd = False
        self.channel.start(lambda: end_cnd)

        in_iter = cycle(self.sub_in)
        for data in data_points:
            next(in_iter).transmit(*data)

        th = Thread(target=self._assert_many_out, args=(ret_data if ret_data else data_points,))
        th.start()

        end_cnd = True
        self._close_connections()
        th.join()

        self._assert_output_subscribers()

    async def _assert_output_subscribers(self):
        time.sleep(1)
        for sub in self.sub_out:
            assert not await sub.is_alive()

    def _start_event_loop(self):
        th = Thread(target=self._start_event_loop_threaded, daemon=True)
        th.start()

    def _start_event_loop_threaded(self):
        self._event_loop.run_forever()
        self._event_loop.close()
        self._event_loop.stop()
