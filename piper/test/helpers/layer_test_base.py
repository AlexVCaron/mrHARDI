import asyncio
from abc import abstractmethod, ABCMeta
from tempfile import TemporaryDirectory
from uuid import uuid4

from piper.comm import Channel
from piper.comm import Subscriber
from piper.pipeline.unit import Unit
from piper.test.helpers.async_helpers import \
    async_close_channels_callback


class LayerTestBase(metaclass=ABCMeta):
    def setUp(self):
        self._loop = asyncio.new_event_loop()
        self.log_dir = TemporaryDirectory()

        self.sub_in = Subscriber("sub_in")
        self.sub_out = Subscriber("sub_out")
        self.channel_in = Channel(["init"], name="channel_in")
        self.channel_in.add_subscriber(self.sub_in, Channel.Sub.IN)
        self.channel_out = None

        self.layer = None
        self.process_chain = []

    def tearDown(self):
        self.log_dir.cleanup()

    def _link_layer_to_processes(self):
        for i, process in enumerate(self.process_chain):
            self.layer.add_unit(
                Unit(process, self.log_dir.name, name="unit_{}".format(i))
            )

    def test_process(self):
        self.layer.initialize()
        self._loop.create_task(self.layer.process())
        id_tag = uuid4()
        task = self._loop.create_task(
            self.sub_in.transmit(id_tag, {"init": None})
        )
        task.add_done_callback(async_close_channels_callback(
            lambda *args: self.sub_in.shutdown(), self._loop
        ))
        result_task = self._loop.create_task(self._dequeue_layer())

        self._loop.run_until_complete(result_task)

        results = result_task.result()
        for res_id_tag, result in results:
            self._assert_test(id_tag, res_id_tag, result)

    @abstractmethod
    def _assert_test(self, id_tag, res_id_tag, result):
        pass

    async def _dequeue_layer(self):
        results = []
        while self.sub_out.promise_data():
            try:
                results.append(await self.sub_out.yield_data())
            except asyncio.CancelledError:
                break

        return results
