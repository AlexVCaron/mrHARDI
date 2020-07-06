import asyncio
from tempfile import TemporaryDirectory
from unittest import TestCase
from uuid import uuid4

from piper.comm import Channel
from piper.comm import Subscriber
from piper.comm.close_condition import CloseCondition
from piper.pipeline.unit import Unit
from piper.test.helpers.async_helpers import \
    async_close_channels_callback
from piper.test.helpers.process import AssertPythonProcess


class TestUnit(TestCase):
    def setUp(self):
        self._loop = asyncio.new_event_loop()

        self.log_dir = TemporaryDirectory()

        self.sub_in = Subscriber()
        self.sub_out = Subscriber()

        self.channel_in = Channel(["data"])
        self.channel_in.add_subscriber(self.sub_in, Channel.Sub.IN)

        self.channel_out = Channel(["data"])
        self.channel_out.add_subscriber(self.sub_out, Channel.Sub.OUT)

        self.payloads = {}

        self.unit = None
        self.end = CloseCondition()

    def tearDown(self):
        self.log_dir.cleanup()
        self._loop.stop()
        self._loop.close()

    def test_process(self):
        awaited_payload = {"data": "data"}
        output_prefix = "opr"
        process = AssertPythonProcess(output_prefix, awaited_payload)

        self.bind_unit(process)
        self.update_payloads({uuid4(): awaited_payload})

        results = self._run_process()
        self._assert_outputs(results, output_prefix)

    def test_process_batch(self):
        awaited_payload = {"data": "data"}
        output_prefix = "opr"
        process = AssertPythonProcess(output_prefix, awaited_payload)

        self.bind_unit(process)
        self.update_payloads({
            uuid4(): awaited_payload for i in range(5)
        })

        results = self._run_process()
        self._assert_outputs(results, output_prefix)

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

        self._loop.create_task(self.unit.process())

        transmission = self._loop.create_task(self._transmit_data())
        transmission.add_done_callback(
            async_close_channels_callback(lambda *args: self.sub_in.shutdown(),
                                          self._loop, self.end)
        )

        results = self._loop.create_task(self._collect_outputs())

        return self._loop.run_until_complete(results)

    async def _transmit_data(self):
        for transmission in asyncio.as_completed([
            self.sub_in.transmit(id_tag, payload)
            for id_tag, payload in self.payloads.items()
        ]):
            await transmission

    async def _collect_outputs(self):
        results = []
        while self.sub_out.promise_data():
            try:
                res_id_tag, result = await self.sub_out.yield_data()
                results.append((res_id_tag, result))
            except asyncio.CancelledError:
                pass

        return results

    def _assert_outputs(self, results, output_prefix):
        id_tags = list(self.payloads.keys())
        for res_id_tag, result in results:
            assert res_id_tag in id_tags

            id_tags.remove(res_id_tag)
            assert result == {
                **self.payloads[res_id_tag], **{"prefix": output_prefix}
            }