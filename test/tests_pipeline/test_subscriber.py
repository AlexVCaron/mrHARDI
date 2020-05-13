from unittest import TestCase
from uuid import uuid4

from multiprocess.exceptions import SubscriberClosedException
from multiprocess.pipeline.subscriber import Subscriber


class TestSubscriber(TestCase):
    def test_timestamp(self):
        sub = Subscriber()
        timestamp = uuid4()

        assert not sub.timestamp(timestamp)
        assert sub.timestamp(timestamp)

    def test_data_ready(self):
        sub = Subscriber()

        assert not sub.data_ready()

        id_tag, data = uuid4(), {}
        sub.transmit(id_tag, data)

        assert sub.data_ready()

        sub.yield_data()

        assert not sub.data_ready()

    def test_transmit_and_yield(self):
        sub = Subscriber()
        id_tag, data = uuid4(), {"data": "data"}

        sub.transmit(id_tag, data)
        ret_id_tag, ret_data = sub.yield_data()

        assert ret_id_tag == id_tag
        assert ret_data == data

    def test_shutdown_sub(self):
        sub = Subscriber()
        id_tag, data = uuid4(), {"data": "data"}

        assert sub.is_alive()

        sub.transmit(id_tag, data)
        assert sub.data_ready()

        sub.shutdown()
        assert not sub.is_alive()
        assert sub.data_ready()

        sub.yield_data()

        self.assertRaises(SubscriberClosedException, sub.transmit, id_tag, data)
