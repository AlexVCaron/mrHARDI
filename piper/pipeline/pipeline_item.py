from abc import abstractmethod, ABCMeta

from piper.comm import Channel
from piper.graph.serializable import Serializable


class PipelineItem(Serializable, metaclass=ABCMeta):
    def __init__(self, input, output, name=""):
        super().__init__()
        self._connections = [input, output]
        self._name = name
        self._initialized = False
        self._test_mode = False

    @property
    def name(self):
        return self._name

    @property
    def serialize(self):
        return {**super().serialize, **{
            'name': self.name,
            'initialized': self._initialized,
            'subscriber_in': self.input.serialize,
            'subscriber_out': self.output.serialize
        }}

    @property
    def input(self):
        return self._connections[0]

    @property
    def output(self):
        return self._connections[-1]

    def initialize(self, *args, depth=0, **kwargs):
        self.input.depth = depth
        self.output.depth = depth

    def set_test(self, on=True):
        self._test_mode = on

    @abstractmethod
    def connect_input(self, *args, **kwargs):
        return self

    @abstractmethod
    def connect_output(self, *args, **kwargs):
        return self

    @abstractmethod
    async def process(self):
        pass

    @property
    @abstractmethod
    def package_keys(self):
        pass

    @abstractmethod
    async def wait_for_shutdown(self):
        pass


def connect_pipeline_items(item_up, item_down, includes=None, excludes=None):
    inter_channel = Channel(
        item_down.package_keys,
        name="chan_{}_to_{}".format(item_up.name, item_down.name)
    )
    item_up.connect_output(inter_channel)
    item_down.connect_input(inter_channel, includes, excludes)
    return inter_channel
