import queue

from multiprocess.cpu.thread import ManagedThread


class Sequence:
    def __init__(self, sequence):
        self._sequence = sequence

    def process(self):
        for unit in self._sequence:
            unit.process()


class ParallelLayer:
    def __init__(self, layer):
        self._layer = layer

    def process(self):
        threads = [
            self._execute_threaded(l.process)
            for l in self._layer
        ]

        while True:
            for th in threads:
                if th.get_thread().isAlive():
                    try:
                        exc = th.get(block=False)
                    except queue.Empty:
                        pass
                    else:
                        exc_type, exc_obj, exc_trace = exc
                        print(exc_type)
                        print(exc_obj)
                        print(exc_trace)

                    th.join_thread(0.1)

            if not any(t.get_thread().isAlive() for t in threads):
                break

    def _execute_threaded(self, fn):
        th = ManagedThread(fn, daemon=True)
        th.start()
        return th.get_exception_bucket()


class Block:
    def __init__(self, sequence):
        self._sequence = sequence

    def process(self):
        for unit in self._sequence:
            unit.process()
