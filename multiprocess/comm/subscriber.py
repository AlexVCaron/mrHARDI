import asyncio
import logging
from asyncio import Queue

from multiprocess.cpu.thread import ThreadedAsyncEntity
from multiprocess.exceptions import SubscriberClosedException
from test.tests_pipeline.helpers.async_helpers import cancel_future_in_loop, \
    set_future_in_loop


class Subscriber(ThreadedAsyncEntity):
    def __init__(self, name="sub"):
        super().__init__(name=name)
        self._timestamp = None
        self._queue = {}
        self._alive = True
        self._chan_in = None
        self._chan_out = None
        ready_evt = self.start()
        ready_evt.wait()
        self._id_tags = Queue(loop=self._async_loop)
        self._transmit_futures = []

    def timestamp(self, timestamp):
        if self._timestamp == timestamp:
            return False

        self._timestamp = timestamp
        return True

    def is_alive(self):
        return self._alive

    def data_ready(self):
        return not self._id_tags.empty()

    def promise_data(self):
        return self.is_alive() or self.data_ready()

    async def transmit(self, id_tag, package):
        logger.debug("{} transmitting".format(self._name))

        if id_tag not in self._queue:
            self._queue[id_tag] = package
            logger.debug("{} queuing id".format(self._name))

            task = asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
                self._put_id(id_tag), self._async_loop
            ))

            self._transmit_futures.append(task)
            await task
            self._transmit_futures.remove(task)
        else:
            self._queue[id_tag].update(package)

        logger.debug("{} has finished transmitting".format(self._name))

    def _process_yield_task_callback(self, future, outer_future):
        try:
            if future.cancelled():
                cancel_future_in_loop(outer_future)
            else:
                set_future_in_loop(outer_future, future.result())
        except RuntimeError:
            pass

    async def yield_data(self):
        try:
            task = asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
                self._inner_yield(), self._async_loop
            ))

            return await task
        except RuntimeError as e:
            if self._async_loop.is_closed():
                raise asyncio.CancelledError(self)
            else:
                raise e

    async def _inner_yield(self):
        logger.debug("{} awaiting for data".format(self._name))
        id_tag = await self._id_tags.get()

        logger.debug("{} returning data".format(self._name))
        self._id_tags.task_done()

        return id_tag, self._queue.pop(id_tag)

    async def wait_for_dequeuing(self):
        logger.debug("{} waiting for dequeue : {} ids in queue".format(
            self._name, self._id_tags.qsize()
        ))
        await self._id_tags.join()
        self.yield_data = self._shutdown_yield_data
        logger.debug("{} dequeued".format(self._name))

    async def shutdown(self):
        logger.info("{} shutdown initiated".format(self._name))
        self._alive = False
        self.transmit = self._shutdown_exception

        for fut in asyncio.as_completed(self._transmit_futures):
            await fut

        await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
            self.wait_for_dequeuing(), self._async_loop
        ))

        logger.debug("{} cancelling tasks".format(self._name))
        await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
            self._cancel_tasks_job(), self._async_loop
        ))

        self._close()

    async def _put_id(self, id_tag):
        logger.debug("{} putting tag in queue".format(self._name))
        await self._id_tags.put(id_tag)
        logger.debug("{} putting tag done".format(self._name))

    async def _yield_id(self):
        logger.debug("{} getting tag from queue".format(self._name))
        tag = await self._id_tags.get()
        logger.debug("{} getting tag done".format(self._name))
        return tag

    async def _cancel_tasks_job(self):
        self_task = asyncio.current_task(self._async_loop)
        running_tasks = list(filter(
            lambda task: not task.done() and task is not self_task,
            asyncio.all_tasks(self._async_loop)
        ))
        logger.debug(
            "{} cancelling {} tasks".format(self._name, len(running_tasks))
        )
        is_cancelled = all([task.cancel() for task in running_tasks])

        return is_cancelled

    def _close(self):
        self.yield_data = self._shutdown_yield_data
        super()._close()

    async def _done_signal(self):
        self._id_tags.task_done()

    async def _shutdown_yield_data(self):
        logger.warning("{} yield has been shutdown".format(self._name))
        raise asyncio.CancelledError(self)

    async def _shutdown_exception(self, *args, **kwargs):
        logger.error(
            "{} was asked to transmit but has shutdown".format(self._name)
        )
        raise SubscriberClosedException(self)


logger = logging.getLogger(Subscriber.__name__)
