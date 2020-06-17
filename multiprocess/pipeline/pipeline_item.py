from abc import abstractmethod, ABCMeta


class PipelineItem(metaclass=ABCMeta):
    def __init__(self, input, output, name=""):
        self._connections = [input, output]
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def input(self):
        return self._connections[0]

    @property
    def output(self):
        return self._connections[-1]

    @abstractmethod
    def connect_input(self, channel):
        return self

    @abstractmethod
    def connect_output(self, channel):
        return self

    @abstractmethod
    async def process(self):
        pass

    @abstractmethod
    def get_package_keys(self):
        pass
