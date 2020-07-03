import asyncio
import logging
from functools import partial
from unittest import TestCase
from uuid import uuid4

from piper.comm import Subscriber
from piper.exceptions import TransmitClosedException


class TestSubscriber(TestCase):
    def setUp(self):
        self._loop = asyncio.get_event_loop()

    def test_data_ready(self):
        sub = Subscriber()

        assert not sub.data_ready()

        id_tag, data = uuid4(), {}
        self._loop.run_until_complete(sub.transmit(id_tag, data))

        assert sub.data_ready()

        self._loop.run_until_complete(sub.yield_data())

        assert not sub.data_ready()

    def test_transmit_and_yield(self):
        sub = Subscriber()
        id_tag, data = uuid4(), {"data": "data"}

        self._loop.run_until_complete(sub.transmit(id_tag, data))
        ret_id_tag, ret_data = self._loop.run_until_complete(sub.yield_data())

        assert ret_id_tag == id_tag
        assert ret_data == data

    def test_shutdown_sub(self):
        logging.basicConfig(level="DEBUG")
        sub = Subscriber()
        id_tag, data = uuid4(), {"data": "data"}

        assert sub.is_alive()

        self._loop.run_until_complete(sub.transmit(id_tag, data))
        assert sub.data_ready()

        def assert_after_shutdown(*args):
            assert not sub.is_alive()

        shutdown = self._loop.create_task(sub.shutdown())
        shutdown.add_done_callback(assert_after_shutdown)

        yield_task = self._loop.create_task(sub.yield_data())

        self._loop.run_until_complete(yield_task)

        def assert_raises(loop):
            loop.run_until_complete(sub.transmit(id_tag, data))

        self.assertRaises(
            TransmitClosedException, partial(assert_raises, self._loop)
        )
