import time
from itertools import cycle
from threading import Thread
from unittest import TestCase
from uuid import uuid4

from multiprocess.pipeline.channel import Channel
from multiprocess.pipeline.sentinel import Sentinel
from multiprocess.pipeline.subscriber import Subscriber


class TestChannel(TestCase):
    def setUp(self):
        self.sub_in = [Subscriber()]
        self.sub_out = [Subscriber()]
        self.out_event = Sentinel(self.sub_out)

        self.channel = Channel(["data"])
        self.channel.add_subscriber(self.sub_in[0], Channel.Sub.IN)
        self.channel.add_subscriber(self.sub_out[0], Channel.Sub.OUT)

    def tearDown(self):
        time.sleep(2)
        assert not self.channel.running()

    def test_start(self):
        end_cnd = False
        self.channel.start(lambda: end_cnd)

        assert self.channel.running()

        end_cnd = True
        self.sub_in[0].shutdown()
        time.sleep(1)

        assert not self.channel.running()

    def test_has_inputs(self):
        assert self.channel.has_inputs()

        channel = Channel(["data"])
        assert not channel.has_inputs()

    def test_one_to_one_flow(self):
        id_tag, data = uuid4(), self._basic_data_package()
        end_cnd = False

        self.channel.start(lambda: end_cnd)
        self.sub_in[0].transmit(id_tag, data)

        th = Thread(target=self._assert_data_point, args=({id_tag: data},))
        th.start()

        end_cnd = True
        self._close_connections()
        th.join()

        self._assert_output_subscribers()

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

    def _close_connections(self):
        for sub in self.sub_in:
            sub.shutdown()

    def _assert_data_point(self, awaited_data):
        inputs = self.out_event.wait()
        self.out_event.clear()
        for input in inputs:
            while input.data_ready():
                ret_id_tag, ret_data = input.yield_data()
                assert ret_id_tag in awaited_data.keys()
                assert awaited_data[ret_id_tag] == ret_data

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

    def _assert_output_subscribers(self):
        time.sleep(1)
        for sub in self.sub_out:
            assert not sub.is_alive()
