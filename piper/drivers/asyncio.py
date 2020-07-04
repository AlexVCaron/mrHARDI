import asyncio
import logging
import traceback
from abc import abstractmethod
from functools import partial
from threading import Event

from .thread import ThreadManager


async def async_wrapper(func, *args, **kwargs):
    return func(*args, **kwargs)


def queue_task_from_other_thread(coro, loop):
    return asyncio.wrap_future(asyncio.run_coroutine_threadsafe(coro, loop))


class DoneEvent:
    def __init__(self, task_manager):
        self._event = None
        self._loop = None
        self._t_man = task_manager

    async def wait_on_future(self):
        self._t_man.protect_task(asyncio.current_task())
        await queue_task_from_other_thread(self._wait_on_future(), self._loop)

    def init_future(self, loop):
        self._event = asyncio.Event(loop=loop)
        self._loop = loop

    def get_loop(self):
        return self._loop

    async def set_result(self, res):
        if not (self.done() or self._loop.is_closed()):
            task = asyncio.run_coroutine_threadsafe(
                async_wrapper(self._event.set),
                self._loop
            )
            task.add_done_callback(lambda *args: print("future done !!!!!!!!!!!!!!!!!!!!!!!!!!!!"))
            await asyncio.shield(asyncio.wrap_future(task))

    def done(self):
        return self._event is not None and self._event.is_set()

    async def _wait_on_future(self):
        self._t_man.protect_task(asyncio.current_task())
        wait_task = self._loop.create_task(self._event.wait())
        self._t_man.protect_task(wait_task)
        await wait_task


class AsyncLoopManager(ThreadManager):
    def __init__(self, name="AsyncLoopManager"):
        super().__init__(name)
        self._done = DoneEvent(self)
        self._ready = Event()
        self._closing = False
        self._async_loop = None
        self._main_async_task = None
        self._cancel_exclude_tasks = []
        self._base_exception_handler = None

        self._add_callback_categories(['ready', 'start', 'done', 'end'])

    @property
    def serialize(self):
        return {**super().serialize, **{
            'started': self.running(),
            'ended': self._done.done()
        }}

    def add_started_callback(self, fn):
        self._callbacks['start'].append(fn)

    def add_ready_callback(self, fn):
        self._callbacks['ready'].append(fn)

    def add_done_callback(self, fn):
        self._callbacks['done'].append(fn)

    async def _set_completed(self):
        await asyncio.shield(self._done.set_result(True))

    def start(
        self, *args, daemon=True, exception_handler=None, **kwargs
    ):
        self._base_exception_handler = exception_handler

        super().start(daemon=daemon)
        return self._ready

    def threaded_run(self, main_loop, *args, **kwargs):
        self._main_async_task = self.queue_new_task(
            self._async_run(*args, **kwargs), main_loop
        )

    def queue_new_task(self, coro, main_loop):
        if main_loop is not asyncio.get_event_loop():
            return queue_task_from_other_thread(
                coro, main_loop
            )
        else:
            return self._async_loop.create_task(coro)

    @abstractmethod
    async def _async_run(self, *args, **kwargs):
        pass

    def running(self):
        return self._async_loop and self._async_loop.is_running()

    def done(self):
        return self._done.done()

    def _closed(self):
        return self._async_loop.is_closed()

    def _thread_loop(self):
        try:
            super()._thread_loop()

            logger.debug("{} starting async loop".format(self._name))
            self._async_loop = asyncio.new_event_loop()
            self._async_loop.set_exception_handler(partial(
                self._async_exception_handler,
                basic_handler=self._base_exception_handler
            ))
            self._async_loop.set_debug(True)
            self._trigger_callbacks('ready')

            logger.debug("{} async loop is running".format(self._name))
            if len(self._callbacks['start']) > 0:
                self._async_loop.create_task(
                    self._trigger_loop_start_callbacks()
                )

            self._done.init_future(self._async_loop)
            self._ready.set()

            closing_task = self._async_loop.create_task(
                self._done.wait_on_future()
            )

            self._cancel_exclude_tasks.append(closing_task)
            self._async_loop.run_until_complete(closing_task)

            dequeue_task = self._async_loop.create_task(self._clear_loop())
            self._cancel_exclude_tasks.append(dequeue_task)
            self._async_loop.run_until_complete(dequeue_task)
            self._async_loop.stop()

            logger.debug("{} async loop closed".format(self._name))
            self._async_loop.close()
            logger.info("{} has shutdown".format(self._name))
            if self._thread.daemon:
                self.stop(False)
        except Exception as e:
            raise e

    def protect_task(self, task):
        self._cancel_exclude_tasks.append(task)

    async def _clear_loop(self):
        curr_task = asyncio.current_task(self._async_loop)
        tasks = list(filter(
            lambda a: a is not curr_task,
            asyncio.all_tasks(self._async_loop)
        ))
        while len(tasks) > 0:
            await asyncio.wait(filter(
                lambda a: a is not curr_task,
                tasks
            ))
            tasks = list(filter(
                lambda a: a is not curr_task,
                asyncio.all_tasks(self._async_loop)
            ))

    def _close(self):
        if not self._done.done():
            asyncio.run_coroutine_threadsafe(
                self._set_completed(), self._async_loop
            )
            logger.error("{} completed flag sent".format(self._name))

    def _async_exception_handler(self, loop, context, base_handler=None):
        exception = context["exception"] if "exception" in context else None
        logger.warning("{} loop received an exception".format(self.name))
        if exception:
            logger.warning(exception)
            logger.warning(traceback.print_exception(
                type(exception), exception, exception.__traceback__
            ))

        if base_handler:
            base_handler(loop, context)

    async def _trigger_loop_start_callbacks(self):
        self._trigger_callbacks('start')

    async def _cancel_tasks_job(self, excludes=[]):
        excludes += [asyncio.current_task(self._async_loop)]
        excludes += self._cancel_exclude_tasks
        running_tasks = list(filter(
            lambda task: not task.done() and task not in excludes,
            asyncio.all_tasks(self._async_loop)
        ))
        if len(running_tasks) > 0:
            logger.debug(
                "{} cancelling {} tasks".format(self._name, len(running_tasks))
            )
            all([task.cancel() for task in running_tasks])

            await asyncio.wait(running_tasks)

            return True

        return True


logger = logging.getLogger(AsyncLoopManager.__name__)


def set_future_in_loop(future, result):
    asyncio.run_coroutine_threadsafe(
        _set_future(result, future),
        future.get_loop()
    )


def cancel_future_in_loop(future):
    asyncio.run_coroutine_threadsafe(
        _cancel_future(future),
        future.get_loop()
    ).result()


async def _set_future(result, future):
    future.set_result(result)


async def _cancel_future(future):
    future.cancel()
