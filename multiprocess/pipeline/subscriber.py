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

    def timestamp(self, timestamp):
        if self._timestamp == timestamp:
            return True

        self._timestamp = timestamp
        return False

    def is_alive(self):
        return self._alive

    def data_ready(self):
        return not self._id_tags.empty()

    async def transmit(self, id_tag, package):
        logger.debug("{} transmitting".format(self._name))
        if id_tag not in self._queue:
            current_loop = asyncio.get_running_loop()
            future = asyncio.Future(loop=current_loop)

            self._queue[id_tag] = package
            logger.debug("{} queuing id".format(self._name))
            asyncio.run_coroutine_threadsafe(
                self._put_id(id_tag), self._async_loop
            ).add_done_callback(lambda fut: set_future_in_loop(future, fut))

            for fut in asyncio.as_completed([future]):
                await fut

        else:
            self._queue[id_tag].update(package)

        logger.debug("{} has finished transmitting".format(self._name))

    async def yield_data(self):
        yield_task = asyncio.create_task(self._inner_yield())
        yield_task.add_done_callback(
            lambda fut: yield_task.cancel() if fut.cancelled() else
            asyncio.run_coroutine_threadsafe(
                self._done_signal(), self._async_loop
            ).result()
        )

        return await yield_task

    async def _inner_yield(self):
        logger.debug("{} awaiting for data".format(self._name))
        future = asyncio.Future(loop=asyncio.get_running_loop())

        asyncio.run_coroutine_threadsafe(
            self._id_tags.get(), self._async_loop
        ).add_done_callback(
            lambda fut: cancel_future_in_loop(future) if fut.cancelled() else
            set_future_in_loop(future, fut.result())
        )

        for fut in asyncio.as_completed([future]):
            id_tag = await fut

            logger.debug("{} returning data".format(self._name))
            return id_tag, self._queue.pop(id_tag)

    async def wait_for_dequeuing(self):
        logger.debug("{} waiting for dequeue : {} ids in queue".format(
            self._name, self._id_tags.qsize()
        ))
        await self._id_tags.join()
        logger.debug("{} dequeued".format(self._name))

    async def shutdown(self):
        logger.info("{} shutdown initiated".format(self._name))
        self._alive = False
        self.transmit = self._shutdown_exception
        task = asyncio.run_coroutine_threadsafe(
            self.wait_for_dequeuing(), self._async_loop
        )
        task.add_done_callback(lambda *args: self._cancel_tasks())

    def _cancel_tasks(self):
        logger.debug("{} cancelling tasks".format(self._name))
        task = asyncio.run_coroutine_threadsafe(
            self._cancel_tasks_job(), self._async_loop
        )
        task.add_done_callback(lambda *args: self._close())

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
        await asyncio.gather(
            *filter(lambda task: not task.done(), running_tasks),
            loop=self._async_loop
        )
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
