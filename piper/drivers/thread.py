import logging
from abc import ABCMeta, abstractmethod
from threading import Thread

from piper.graph.serializable import Serializable


class ThreadManager(Serializable, metaclass=ABCMeta):
    def __init__(self, name="ThreadManager"):
        super().__init__()
        self._name = name
        self._thread = None
        self._callbacks = {'thread_started': [], 'thread_stopped': []}

    @property
    def name(self):
        return self._name

    @property
    def serialize(self):
        return {**super().serialize, **{
            'name': self.name,
            'thread_started': self.has_started()
        }}

    def has_started(self):
        return self._thread is not None

    def is_alive(self):
        return self._thread.is_alive()

    def add_thread_started_callback(self, fn):
        self._callbacks['thread_started'].append(fn)

    def add_thread_stopped_callback(self, fn):
        self._callbacks['thread_stopped'].append(fn)

    def start(self, *args, daemon=True, **kwargs):
        logger.debug("{} starting thread".format(self._name))
        self._thread = Thread(target=self._thread_loop, daemon=daemon)
        self._thread.start()

    def stop(self, join=True):
        if join:
            self._thread.join()

        self._trigger_callbacks('thread_stopped')

    @abstractmethod
    def _thread_loop(self):
        self._trigger_callbacks('thread_started')

    def _trigger_callbacks(self, key):
        for cbk in self._callbacks[key]:
            cbk()

    def _add_callback_categories(self, categories):
        for cat in filter(lambda c: c not in self._callbacks, categories):
            self._callbacks[cat] = []


logger = logging.getLogger(ThreadManager.__name__)
