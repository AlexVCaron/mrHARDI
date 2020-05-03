import time
from itertools import cycle
from unittest import TestCase
from uuid import uuid4

from multiprocess.pipeline.channel import Channel
from multiprocess.pipeline.subscriber import Subscriber


class TestChannel(TestCase):
    def setUp(self):
        self.sub_in = [Subscriber()]
        self.sub_out = [Subscriber()]
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

        self._assert_data_point(self.sub_out[0], id_tag, data)

        end_cnd = True

    def test_one_to_many_flow(self):
        self.sub_out.append(Subscriber())
        self.channel.add_subscriber(self.sub_out[-1], Channel.Sub.OUT)

        id_tag1, data1 = uuid4(), self._basic_data_package("data2")
        id_tag2, data2 = uuid4(), self._basic_data_package("data1")

        self._one_to_many(((id_tag1, data1), (id_tag2, data2)))

    def test_one_to_many_flow_bcast(self):
        self.sub_out.append(Subscriber())
        self.channel = Channel(["data"], True)

        self.channel.add_subscriber(self.sub_in[0], Channel.Sub.IN)
        for sub in self.sub_out:
            self.channel.add_subscriber(sub, Channel.Sub.OUT)

        id_tag, data = uuid4(), self._basic_data_package()

        self._one_to_many(((id_tag, data),), True)

    def test_many_to_one_flow(self):
        self.sub_in.append(Subscriber())
        self.channel.add_subscriber(self.sub_in[-1], Channel.Sub.IN)

        id_tag1, data1 = uuid4(), self._basic_data_package("data2")
        id_tag2, data2 = uuid4(), self._basic_data_package("data1")

        self._many_to_one(((id_tag1, data1), (id_tag2, data2)))

    def test_many_to_one_flow_partial(self):
        self.channel = Channel(["data1", "data2"])
        self.channel.add_subscriber(self.sub_out[0], Channel.Sub.OUT)

        self.sub_in.append(Subscriber())
        for sub in self.sub_in:
            self.channel.add_subscriber(sub, Channel.Sub.IN)

        id_tag = uuid4()
        data1, data2 = {"data1": "data1"}, {"data2": "data2"}

        self._many_to_one(
            ((id_tag, data1), (id_tag, data2)),
            ((id_tag, {**data1, **data2}),)
        )

    def test_many_to_many_flow(self):
        self.sub_in.append(Subscriber())
        self.channel.add_subscriber(self.sub_in[-1], Channel.Sub.IN)
        self.sub_out.append(Subscriber())
        self.channel.add_subscriber(self.sub_out[-1], Channel.Sub.OUT)

        id_tag1, data1 = uuid4(), self._basic_data_package("data2")
        id_tag2, data2 = uuid4(), self._basic_data_package("data1")

        self._many_to_many(((id_tag1, data1), (id_tag2, data2)))

    def test_many_to_many_flow_bcast(self):
        self.channel = Channel(["data"], True)
        self.sub_in.append(Subscriber())
        for sub in self.sub_in:
            self.channel.add_subscriber(sub, Channel.Sub.IN)
        self.sub_out.append(Subscriber())
        for sub in self.sub_out:
            self.channel.add_subscriber(sub, Channel.Sub.OUT)

        id_tag1, data1 = uuid4(), self._basic_data_package("data2")
        id_tag2, data2 = uuid4(), self._basic_data_package("data1")

        self._many_to_many(
            ((id_tag1, data1), (id_tag2, data2)),
            bcast=True
        )

    def test_many_to_many_flow_partial(self):
        self.channel = Channel(["data1", "data2"])
        self.sub_in.append(Subscriber())
        for sub in self.sub_in:
            self.channel.add_subscriber(sub, Channel.Sub.IN)
        self.sub_out.append(Subscriber())
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
        self.sub_in.append(Subscriber())
        for sub in self.sub_in:
            self.channel.add_subscriber(sub, Channel.Sub.IN)
        self.sub_out.append(Subscriber())
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
            ),
            bcast=True
        )

    def _basic_data_package(self, value="data"):
        return {"data": value}

    def _assert_data_point(self, sub, id_tag, data):
        time.sleep(1)
        ret_id_tag, ret_data = sub.yield_data()
        assert ret_id_tag == id_tag
        assert ret_data == data

    def _assert_many_out(self, data_points, bcast):
        for i in range(len(self.sub_out)):
            if bcast:
                for data in data_points:
                    self._assert_data_point(
                        self.sub_out[i], *data
                    )
            else:
                self._assert_data_point(
                    self.sub_out[i], *(data_points[i])
                )

    def _many_to_one(self, data_points, ret_data=None):
        end_cnd = False
        self.channel.start(lambda: end_cnd)

        in_iter = cycle(self.sub_in)
        for data in data_points:
            next(in_iter).transmit(*data)

        for data in ret_data if ret_data else data_points:
            self._assert_data_point(self.sub_out[0], *data)

        end_cnd = True

    def _one_to_many(self, data_points, bcast=False):
        end_cnd = False
        self.channel.start(lambda: end_cnd)

        for data in data_points:
            self.sub_in[0].transmit(*data)

        self._assert_many_out(data_points, bcast)

        end_cnd = True

    def _many_to_many(self, data_points, ret_data=None, bcast=False):
        end_cnd = False
        self.channel.start(lambda: end_cnd)

        in_iter = cycle(self.sub_in)
        for data in data_points:
            next(in_iter).transmit(*data)

        self._assert_many_out(ret_data if ret_data else data_points, bcast)

        end_cnd = True
