import logging
from unittest import TestCase

from piper.comm import Channel
from piper.pipeline import ParallelLayer
from piper.test.helpers.layer_test_base import LayerTestBase
from piper.test.helpers.process import DummyProcess

logging.basicConfig(level="DEBUG")


class TestParallelLayer(LayerTestBase, TestCase):
    def setUp(self):
        LayerTestBase.setUp(self)
        logging.basicConfig(level="DEBUG")
        for i in range(6):
            self.process_chain.append(
                DummyProcess("process", "process", ["init"], ["new_output"])
            )

        self.channel_out = Channel(
            self.process_chain[-1].get_required_output_keys(),
            name="channel_out"
        )
        self.channel_out.add_subscriber(self.sub_out, Channel.Sub.OUT)

        self.layer = ParallelLayer(
            self.channel_in, self.channel_out
        )

        self._link_layer_to_processes()

    def _assert_test(self, id_tag, res_id_tag, result):
        assert id_tag == res_id_tag

