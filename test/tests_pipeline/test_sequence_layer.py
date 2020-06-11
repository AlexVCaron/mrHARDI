from unittest import TestCase

from multiprocess.pipeline.channel import Channel
from multiprocess.pipeline.layer import SequenceLayer
from test.tests_pipeline.helpers.layer_test_base import LayerTestBase
from test.tests_pipeline.helpers.process import AddUniqueArgProcess


class SequenceLayerTest(LayerTestBase, TestCase):
    def setUp(self):
        LayerTestBase.setUp(self)

        self.process_chain = self._chain_process(
            AddUniqueArgProcess("process", "process", ["init"]), 6
        )

        self.channel_out = Channel(
            self._loop, self.process_chain[-1].get_output_keys(),
            name="channel_out"
        )
        self.channel_out.add_subscriber(self.sub_out, Channel.Sub.OUT)

        self.layer = SequenceLayer(
            self.channel_in, self.channel_out, self._loop
        )

        self._link_layer_to_processes()

    def _assert_test(self, id_tag, res_id_tag, result):
        assert res_id_tag == id_tag
        processes_keys = [p.get_unique_key() for p in self.process_chain]
        assert all(k in result for k in processes_keys)
        assert all(
            result[k] == p for k, p in zip(processes_keys, self.process_chain)
        )

    def _chain_process(self, process, n, lst=[]):
        if len(lst) == n - 1:
            return lst + [process]

        lst.append(process)

        return self._chain_process(AddUniqueArgProcess(
            "process", "process", process.get_output_keys()
        ), n, lst)
