import asyncio
from abc import abstractmethod, ABCMeta
from tempfile import TemporaryDirectory
from uuid import uuid4

from multiprocess.pipeline.channel import Channel
from multiprocess.pipeline.subscriber import Subscriber
from multiprocess.pipeline.unit import Unit
from test.tests_pipeline.helpers.async_helpers import \
    async_close_channels_callback


class LayerTestBase(metaclass=ABCMeta):
    def setUp(self):
        self._loop = asyncio.new_event_loop()
        self.log_dir = TemporaryDirectory()

        self.sub_in = Subscriber("sub_in")
        self.sub_out = Subscriber("sub_out")
        self.channel_in = Channel(self._loop, ["init"], name="channel_in")
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
        self.layer.process()
        id_tag = uuid4()
        task = self._loop.create_task(
            self.sub_in.transmit(id_tag, {"init": None})
        )
        task.add_done_callback(async_close_channels_callback(
            lambda *args: self.sub_in.shutdown(), self._loop
        ))
        result_task = self._loop.create_task(self.sub_out.yield_data())

        self._loop.run_until_complete(result_task)
        self._loop.run_until_complete(self.layer.wait_for_completion())
        self._loop.run_until_complete(self.channel_in.wait_for_completion())
        if self.channel_out:
            self._loop.run_until_complete(
                self.channel_out.wait_for_completion()
            )

        res_id_tag, result = result_task.result()
        self._assert_test(id_tag, res_id_tag, result)

    @abstractmethod
    def _assert_test(self, id_tag, res_id_tag, result):
        pass
