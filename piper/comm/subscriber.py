import asyncio
import logging
from asyncio import Queue
from functools import partial

from piper.drivers.asyncio import AsyncLoopManager, \
    set_future_in_loop, \
    cancel_future_in_loop
from piper.exceptions import TransmitClosedException, YieldClosedException, \
    AlreadyShutdownException


class Subscriber(AsyncLoopManager):
    async def _async_run(self, *args, **kwargs):
        pass

    def __init__(self, name="sub", includes=None, excludes=None):
        super().__init__(name=name)

        assert includes is None or excludes is None, \
            "Only supply of both includes or excludes"

        if includes is not None:
            self._filter_data = partial(
                self._filter_includes, includes=includes
            )

        if excludes is not None:
            self._filter_data = partial(
                self._filter_excludes, excludes=excludes
            )

        self._timestamp = None
        self._queue = {}
        self._alive = True
        self._depth = 0
        ready_evt = self.start()
        ready_evt.wait()
        self._done.init_future(self._async_loop)
        self._id_tags = Queue(loop=self._async_loop)
        self._transmit_futures = []

    def timestamp(self, timestamp):
        if self._timestamp == timestamp:
            return False

        self._timestamp = timestamp
        return True

    @property
    def depth(self):
        return self._depth

    @depth.setter
    def depth(self, val):
        self._depth = val

    def is_alive(self):
        return self._alive

    def data_ready(self):
        return not self._id_tags.empty()

    def promise_data(self):
        return (self.is_alive() or self.data_ready()) and not self._closing

    async def transmit(self, id_tag, package):
        logger.debug("{} transmitting".format(self._name))

        if id_tag not in self._queue:
            self._queue[id_tag] = self._filter_data(package)
            logger.debug("{} queuing id".format(self._name))

            task = asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
                self._put_id(id_tag), self._async_loop
            ))

            self._transmit_futures.append(task)
            await task
            self._transmit_futures.remove(task)
        else:
            self._queue[id_tag].update(self._filter_data(package))

        logger.debug("{} has finished transmitting".format(self._name))

    def _process_yield_task_callback(self, future, outer_future):
        try:
            if future.cancelled():
                cancel_future_in_loop(outer_future)
            else:
                set_future_in_loop(outer_future, future.result())
        except RuntimeError:
            pass

    def _filter_data(self, data):
        return data

    def _filter_includes(self, data, includes):
        return dict(filter(lambda d: d[0] in includes, data.items()))

    def _filter_excludes(self, data, excludes):
        return dict(filter(lambda d: d[0] not in excludes, data.items()))

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
        logger.warning("{} waiting for dequeue : {} ids in queue".format(
            self._name, self._id_tags.qsize()
        ))
        await self._id_tags.join()
        self.yield_data = self._shutdown_yield_data
        logger.warning("{} dequeued".format(self._name))

    async def _acquire_lock(self):
        await self._shutdown_lock.acquire()

    async def shutdown(self, force=False):
        try:
            shutdown_fn = self._inner_shutdown
            self._inner_shutdown = self._already_shut_bypass
            await shutdown_fn(force)
        except AlreadyShutdownException:
            pass

    async def _inner_shutdown(self, force):
        try:
            if not self._closing:
                self._closing = force
                logger.warning("{} shutdown initiated".format(self._name))
                self._alive = False
                self.transmit = self._shutdown_transmit_data

                if force:
                    self.yield_data = self._shutdown_yield_data
                else:
                    for fut in asyncio.as_completed(self._transmit_futures):
                        await fut

                    await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
                        self.wait_for_dequeuing(), self._async_loop
                    ))

                logger.warning("{} cancelling tasks".format(self._name))
                await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
                    self._cancel_tasks_job(), self._async_loop
                ))

                self._close()
                logger.warning("{} closed".format(self._name))
        except RuntimeError:
            pass

    async def _already_shut_bypass(self, *args, **kwargs):
        raise AlreadyShutdownException(self)

    async def _put_id(self, id_tag):
        logger.debug("{} putting tag in queue".format(self._name))
        await self._id_tags.put(id_tag)
        logger.debug("{} putting tag done".format(self._name))

    async def _yield_id(self):
        logger.debug("{} getting tag from queue".format(self._name))
        tag = await self._id_tags.get()
        logger.debug("{} getting tag done".format(self._name))
        return tag

    def _close(self):
        super()._close()

    async def _done_signal(self):
        self._id_tags.task_done()

    async def _shutdown_yield_data(self):
        logger.warning("{} yield has been shutdown".format(self._name))
        raise YieldClosedException(self)

    async def _shutdown_transmit_data(self, *args, **kwargs):
        logger.error(
            "{} was asked to transmit but has shutdown".format(self._name)
        )
        raise TransmitClosedException(self)


logger = logging.getLogger(Subscriber.__name__)
