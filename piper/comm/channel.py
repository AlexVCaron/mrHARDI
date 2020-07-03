import asyncio
import logging
from enum import Enum
from itertools import cycle
from uuid import uuid4

from piper.drivers.asyncio import AsyncLoopManager
from piper.exceptions import ChannelInnerCancelException, \
    TransmitClosedException, YieldClosedException
from .subscriber import Subscriber


class Channel(AsyncLoopManager):
    class Sub(Enum):
        IN = "in"
        OUT = "out"

    def __init__(
        self, package_keys, broadcast_out=False, name="chan"
    ):
        super().__init__(name)

        self._package_keys = package_keys
        self._broadcast_out = broadcast_out
        self._transmit_futures = []

        self._subscribers = {
            k: [] for k in Channel.Sub
        }
        self._out_iter = None
        self._idle_packages = {}

        self._main_loop_task = None
        self._main_async_task = None

        if self._broadcast_out:
            self._transmit = self._bcast_out

    @property
    def package_keys(self):
        return self._package_keys

    @property
    def is_broadcasting(self):
        return self._broadcast_out

    @property
    def serialize(self):
        return {**super().serialize, **{
            'keys': self.package_keys,
            'broadcast': self.is_broadcasting,
            'subscribers_in': [
                s.serialize for s in self._subscribers[Channel.Sub.IN]
            ],
            'subscribers_out': [
                s.serialize for s in self._subscribers[Channel.Sub.OUT]
            ]
        }}

    def add_subscriber(self, sub, type=Sub.IN):
        self._subscribers[type].append(sub)

    def has_inputs(self):
        will_be_data = any(list(
            s.promise_data() for s in self._subscribers[Channel.Sub.IN]
        ))

        return (
            len(self._subscribers[Channel.Sub.IN]) > 0 and will_be_data
        )

    def start(
        self, end_cnd=lambda: False,
        daemon=True, exception_handler=None, depth=0, **kwargs
    ):
        for sub in self._subscribers[Channel.Sub.IN]:
            sub.depth = depth
        for sub in self._subscribers[Channel.Sub.OUT]:
            sub.depth = depth

        ready_evt = super().start(
            daemon=daemon, exception_handler=exception_handler,
            **kwargs
        )
        ready_evt.wait()

        self.threaded_run(self._async_loop, end_cnd)
        return self._done

    def threaded_run(self, main_loop, end_cnd, *args, **kwargs):
        self.prepare_iterators()
        super().threaded_run(main_loop, end_cnd, *args, **kwargs)

    def prepare_iterators(self):
        self._out_iter = self._subscribers[Channel.Sub.OUT]
        if not self._broadcast_out:
            self._out_iter = cycle(self._out_iter)

    async def pool_data_package(self):
        timestamp = uuid4()
        while True:
            logger.debug("{} has started looping".format(self._name))
            inputs = list(filter(
                lambda s: s.timestamp(timestamp),
                self._subscribers[Channel.Sub.IN]
            ))
            has_transmitted = False
            inner_cancel = None

            logger.debug(
                "{} has {} up-to-date inputs".format(self._name, len(inputs))
            )

            for result in asyncio.as_completed([
                self._yield(i) for i in inputs
            ]):
                try:
                    logger.debug("{} awaits on subscriber".format(self._name))
                    id_tag = await result
                    logger.debug(
                        "{} received an id {}".format(self._name, id_tag)
                    )

                    try:
                        if id_tag and self._is_complete(id_tag):
                            logger.debug(
                                "{} is transmitting data".format(self._name)
                            )
                            package = self._get_package(id_tag)
                            await self._transmit(id_tag, package)
                            has_transmitted = True
                            logger.debug(
                                "{} has transmitted".format(self._name)
                            )
                        else:
                            logger.debug("{} package was not complete".format(
                                self._name)
                            )
                    except KeyError:
                        pass
                except YieldClosedException as e:
                    inner_cancel = e
                except asyncio.CancelledError as e:
                    inner_cancel = e
                except TransmitClosedException:
                    raise asyncio.CancelledError()

            if inner_cancel and self._subscribers_empty():
                raise ChannelInnerCancelException()

            await asyncio.sleep(0)

            if has_transmitted or all([not s.promise_data() for s in inputs]):
                logger.debug("{} is breaking the loop".format(self._name))
                break
            else:
                timestamp = uuid4()

    async def shutdown(self, force=False):
        try:
            if not self._closing and self.running():
                self._closing = True
                cancelled = await self.queue_new_task(
                    self._inner_cancel_task(self._main_loop_task),
                    self._async_loop
                )

                if force:
                    excluded_tasks = [self._main_async_task]
                    if asyncio.get_event_loop() is self._async_loop:
                        excluded_tasks.append(
                            asyncio.current_task(self._async_loop)
                        )
                    if not self._closed():
                        await self.queue_new_task(
                            self._cancel_tasks_job(
                                excludes=excluded_tasks
                            ),
                            self._async_loop
                        )

                if not self._closed():
                    shut_task = self._attempt_shutdown(force, True)
                    if shut_task:
                        await shut_task

                return cancelled

            return True
        except RuntimeError:
            pass

    def _get_package(self, id_tag, *args, **kwargs):
        return self._reconstruct_package(self._idle_packages.pop(id_tag))

    def _reconstruct_package(self, data):
        package = {}
        for item in sorted(data, key=lambda it: it['sort_val']):
            package.update(item['data'])
        return package

    def _is_complete(self, id_tag):
        try:
            package_keys = self._reconstruct_package(self._idle_packages[id_tag])
            return all(k in package_keys for k in self._package_keys)
        except BaseException as e:
            raise e

    def _looping_required(self, end_cnd):
        return not end_cnd() or self.has_inputs()

    async def _async_run(self, end_cnd):
        logger.info("{} async loop starting".format(self._name))
        try:
            while self._looping_required(end_cnd):
                logger.debug("{} pooling data".format(self._name))
                self._main_loop_task = self._async_loop.create_task(
                    self.pool_data_package()
                )
                await self._main_loop_task
        except ChannelInnerCancelException as e:
            self._attempt_shutdown()
        except asyncio.CancelledError as e:
            logger.warning("{} received a forced cancellation call".format(
                self._name
            ))
            self._attempt_shutdown(True)
        except BaseException as e:
            raise e
        else:
            self._attempt_shutdown()

    def _attempt_shutdown(self, force=False, ignore=False):
        if ignore or not self._closing:
            shut_task = self.queue_new_task(
                self._attempt_subscribers_shutdown(force),
                self._async_loop
            )
            shut_task.add_done_callback(lambda *args: self._close())
            return shut_task
        return None

    def _close(self):
        logger.warning(
            "{} attempting graceful shutdown in close".format(self._name)
        )
        super()._close()
        logger.warning("Goodbye {}".format(self._name))

    async def _attempt_subscribers_shutdown(self, force=False):
        if not self._closed():
            try:
                logger.warning(
                    "{} shutting output subscribers".format(self._name)
                )
                subs = self._subscribers[Channel.Sub.OUT]
                if force:
                    subs += self._subscribers[Channel.Sub.IN]
                for fut in asyncio.as_completed([
                    s.shutdown(force) for s in subs
                ]):
                    await fut

                logger.warning(
                    "{} subscribers down".format(self._name)
                )
            except RuntimeError as e:
                pass

    def _subscribers_empty(self):
        return all(
            not s.promise_data() for s in self._subscribers[Channel.Sub.IN]
        )

    async def _inner_cancel_task(self, task):
        return task.cancel()

    async def _yield(self, sub):
        id_tag, data = await sub.yield_data()

        if id_tag:
            if id_tag not in self._idle_packages:
                self._idle_packages[id_tag] = []

            logging.debug(
                "{} putting at {} : {}".format(
                    self._name, id_tag, data.keys() if data else None
                )
            )
            self._idle_packages[id_tag].append({
                "data": data, "sort_val": sub.depth
            })

        return id_tag

    async def _transmit(self, id_tag, package):
        sub = next(self._out_iter)
        task = asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
            sub.transmit(id_tag, package), self._async_loop
        ))
        self._transmit_futures.append(task)

        await task
        self._transmit_futures.remove(task)

    async def _bcast_out(self, id_tag, package):
        for fut in asyncio.as_completed([
            s.transmit(id_tag, package) for s in self._out_iter
        ]):
            await fut

    def _async_exception_handler(self, loop, context, basic_handler=None):
        super()._async_exception_handler(loop, context, basic_handler)


logger = logging.getLogger(Channel.__name__)


def create_connection(input_list, package_keys, name, bcast=False):
    channel = Channel(package_keys, bcast, name)

    for in_c in input_list:
        subscriber = Subscriber()

        channel.add_subscriber(subscriber, Channel.Sub.IN)
        in_c.add_subscriber(subscriber, Channel.Sub.OUT)

    return channel
