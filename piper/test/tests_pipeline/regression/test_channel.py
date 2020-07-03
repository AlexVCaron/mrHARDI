import asyncio
from unittest import TestCase
from uuid import uuid4

from piper.comm import Channel
from piper.comm import Subscriber
from piper.comm.close_condition import CloseCondition


class RegressionTestChannel(TestCase):
    def setUp(self):
        self.n_short = 100
        self.n_long = 10
        self.to_short = 6
        self.to_long = 200
        self.data = {"data": "data"}
        self.loop = asyncio.new_event_loop()
        self.channel = Channel(["data"])
        self.sub_in = Subscriber("sub_in")
        self.sub_out = Subscriber("sub_out")
        self.end_cnd = CloseCondition()
        self.channel.add_subscriber(self.sub_in, Channel.Sub.IN)
        self.channel.add_subscriber(self.sub_out, Channel.Sub.OUT)

    def test_yield_then_shutdown(self):
        self._run_test_n_times(self.n_short, self._test_yield_then_shutdown)

    def test_shutdown_then_yield(self):
        self._run_test_n_times(self.n_short, self._test_shutdown_then_yield)

    def test_yield_then_shutdown_100_datapoints(self):
        self._run_test_n_times(
            self.n_long, self._test_yield_then_shutdown, n=100,
            task_creator=self._create_long_timeout_task
        )

    def test_shutdown_then_yield_100_datapoints(self):
        self._run_test_n_times(
            self.n_long, self._test_shutdown_then_yield, n=100,
            task_creator=self._create_long_timeout_task
        )

    def _run_test_n_times(self, times, test, *args, **kwargs):
        try:
            print("Test completed {} / {}".format(0, times))
            for i in range(times):
                test(*args, **kwargs)
                self.tearDown()
                self.setUp()
                print("Test completed {} / {}".format(i + 1, times))
        except Exception as e:
            self.fail("Test has raised an exception !!!!!!\n{}".format(e))

    def _test_yield_then_shutdown(self, n=1, task_creator=None):
        tk = task_creator if task_creator else self._create_short_timeout_task
        future = asyncio.Future(loop=self.loop)
        self.channel.start(lambda: self.end_cnd)
        transmit_task, ids = self._transmit_n_times(
            n, task_creator=tk
        )
        yield_task = self._yield_n_times(
            n, lambda *args: self._create_short_timeout_task(
                self.sub_in.shutdown()
            ).add_done_callback(lambda *args: future.set_result(True)),
            task_creator=tk
        )
        self.loop.run_until_complete(yield_task)
        self.loop.run_until_complete(future)
        self.loop.stop()

        assert transmit_task.done()
        assert yield_task.done()
        self._assert_result(yield_task, ids)

    def _test_shutdown_then_yield(self, n=1, task_creator=None):
        tk = task_creator if task_creator else self._create_short_timeout_task
        future = asyncio.Future(loop=self.loop)
        shutdown_queued = asyncio.Future(loop=self.loop)
        self.channel.start(lambda: self.end_cnd)
        transmit_task, ids = self._transmit_n_times(
            n, lambda *args: [
                self._create_short_timeout_task(
                    self.sub_in.shutdown()
                ).add_done_callback(lambda *args: future.set_result(True)),
                shutdown_queued.set_result(True)
            ],
            task_creator=tk
        )
        yield_task = self._yield_n_times(
            n, task_creator=tk
        )

        self.loop.run_until_complete(transmit_task)
        self.loop.run_until_complete(shutdown_queued)
        self.loop.run_until_complete(yield_task)
        self.loop.run_until_complete(future)
        self.loop.stop()

        assert transmit_task.done()
        assert yield_task.done()
        self._assert_result(yield_task, ids)

    def _assert_result(self, yield_task, ids):
        result = dict(yield_task.result())
        for id_tag in ids:
            assert id_tag in result
            res_data = result.pop(id_tag)
            assert res_data == self.data

    def _create_short_timeout_task(self, coro, n=1):
        return self.loop.create_task(
            asyncio.wait_for(coro, n * self.to_short, loop=self.loop)
        )

    def _create_long_timeout_task(self, coro, n=1):
        return self.loop.create_task(
            asyncio.wait_for(coro, n * self.to_long, loop=self.loop)
        )

    def _yield_n_times(self, n, callback=None, task_creator=None):
        tk = task_creator if task_creator else self.loop.create_task
        coro = self._yield_n(n)
        yield_task = tk(*(coro, n) if task_creator else (coro,))

        if callback:
            yield_task.add_done_callback(callback)

        return yield_task

    async def _yield_n(self, n):
        results = []
        for task in asyncio.as_completed([
            self.sub_out.yield_data() for _ in range(n)
        ], loop=self.loop):
            try:
                results.append(await task)
            except asyncio.CancelledError as e:
                pass
            except BaseException as e:
                raise e

        return results

    def _transmit_n_times(self, n, callback=None, task_creator=None):
        ids = [uuid4() for _ in range(n)]
        tk = task_creator if task_creator else self.loop.create_task
        coro = self._transmit_n(ids)
        transmit_task = tk(*((coro, n) if task_creator else (coro,)))

        if callback:
            transmit_task.add_done_callback(callback)

        return transmit_task, ids

    async def _transmit_n(self, ids):
        for task in asyncio.as_completed([
            self.sub_in.transmit(id_tag, self.data) for id_tag in ids
        ], loop=self.loop):
            await task
