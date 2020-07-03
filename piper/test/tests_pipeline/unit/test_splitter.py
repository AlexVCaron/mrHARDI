import asyncio
from unittest import TestCase
from uuid import uuid4

from numpy import unique

from piper.comm import Splitter
from piper.comm import Subscriber
from piper.comm.close_condition import CloseCondition
from piper.test.helpers.async_helpers import async_close_channels_callback


class TestSplitter(TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        self.sub_in = Subscriber("sub_into_splitter")
        self.sub_out = []
        self.splitter = Splitter(self.sub_in)
        self.end_cnd = CloseCondition()

    def test_split_dataset(self):
        data = {"data_{}".format(n): n for n in range(10)}
        for i in range(10):
            self.sub_out.append(Subscriber("sub_from_splitter_{}".format(i)))
            self.splitter.add_subscriber(
                self.sub_out[-1], ["data_{}".format(i)]
            )

        self.splitter.start(lambda: self.end_cnd)

        sub_task = self.loop.create_task(
            self.sub_in.transmit(uuid4(), data)
        )
        sub_task.add_done_callback(
            async_close_channels_callback(
                lambda *args: self.sub_in.shutdown(), self.loop, self.end_cnd
            )
        )
        result_task = self.loop.create_task(self._dequeue_output())

        self.loop.run_until_complete(sub_task)
        self.loop.run_until_complete(result_task)

        results = result_task.result()
        self._assert_results(data, results)

    def _assert_results(self, initial_data, results, all_unique_outputs=True):
        res_keys = [k for r in results for k in r[1].keys()]
        assert all([k in initial_data for k in res_keys])
        assert all([k in res_keys for k in initial_data.keys()])

        if all_unique_outputs:
            assert len(unique(res_keys)) == len(res_keys)

        recons_package = {k: v for r in results for k, v in r[1].items()}
        assert recons_package == initial_data

    async def _dequeue_output(self):
        results = []
        subs = list(filter(lambda s: s.promise_data(), self.sub_out))
        while len(subs) > 0:
            for fut in asyncio.as_completed([s.yield_data() for s in subs]):
                try:
                    results.append(await fut)
                except asyncio.CancelledError:
                    pass

            subs = list(filter(lambda s: s.promise_data(), self.sub_out))

        return results
