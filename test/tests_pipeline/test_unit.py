import time
from tempfile import TemporaryDirectory
from unittest import TestCase
from uuid import uuid4

from multiprocess.pipeline.sentinel import Sentinel
from multiprocess.pipeline.subscriber import Subscriber

from multiprocess.pipeline.channel import Channel
from multiprocess.pipeline.unit import Unit
from test.tests_pipeline.helpers.process import AssertPythonProcess


class TestUnit(TestCase):
    def setUp(self):
        self.log_dir = TemporaryDirectory()

        self.sub_in = Subscriber()
        self.sub_out = Subscriber()
        self.sentinel = Sentinel([self.sub_out])

        self.channel_in = Channel(["data"])
        self.channel_in.add_subscriber(self.sub_in, Channel.Sub.IN)

        self.channel_out = Channel(["data"])
        self.channel_out.add_subscriber(self.sub_out, Channel.Sub.OUT)

        self.payloads = {}

        self.unit = None
        self.end = False

    def test_process(self):
        awaited_payload = {"data": "data"}
        output_prefix = "opr"
        process = AssertPythonProcess(output_prefix, awaited_payload)

        self.bind_unit(process)
        self.update_payloads({uuid4(): awaited_payload})
        self._run_process()
        self._get_and_assert_outputs(output_prefix)

    def test_process_batch(self):
        awaited_payload = {"data": "data"}
        output_prefix = "opr"
        process = AssertPythonProcess(output_prefix, awaited_payload)

        self.bind_unit(process)
        self.update_payloads({
            uuid4(): awaited_payload for i in range(5)
        })

        self._run_process()
        self._get_and_assert_outputs(output_prefix)

    @property
    def channels(self):
        return [self.channel_in, self.channel_out]

    def update_payloads(self, payloads):
        self.payloads.update(payloads)

    def bind_unit(self, process):
        self.unit = Unit(
            process, self.log_dir.name
        ).connect_input(self.channel_in).connect_output(self.channel_out)

    def _run_process(self):
        for channel in self.channels:
            channel.start(lambda: self.end)
            channel.start(lambda: self.end)

        self.unit.process()

        for id_tag, payload in self.payloads.items():
            self.sub_in.transmit(id_tag, payload)

        self.sub_in.shutdown()

    def _get_and_assert_outputs(self, output_prefix):
        while self.sub_out.is_alive() or self.sub_out.data_ready():
            id_tags = list(self.payloads.keys())
            inputs = self.sentinel.wait()
            self.sentinel.clear()

            for input in inputs:
                while input.data_ready():
                    res_id_tag, result = input.yield_data()
                    assert res_id_tag in id_tags

                    id_tags.remove(res_id_tag)
                    assert result == {**self.payloads[res_id_tag], **{"prefix": output_prefix}}
