import random
import time

from old_remove_multiprocess.utils.scheduler import Scheduler

from piper.pipeline.process import Process


class DummyWaiter(Process):
    def __init__(self, name):
        super().__init__(name)
        self._n_cores = 1

    def execute(self):
        print("{} starting wait".format(self.name))
        time.sleep(random.randrange(5, 11))
        print("{} ending wait".format(self.name))


scheduler = Scheduler()
scheduler.add_phase("test_dummy", [
    DummyWaiter("dummy wait 1"),
    DummyWaiter("dummy wait 2"),
    DummyWaiter("dummy wait 3"),
    DummyWaiter("dummy wait 4")
])

scheduler.execute()
