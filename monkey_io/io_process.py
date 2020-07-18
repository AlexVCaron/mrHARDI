from abc import ABCMeta
from os.path import join

from piper.pipeline import PythonProcess, ShellProcess


def monkey_io_metadata_prefix_unpacker(metadata):
    return join(metadata['subject'], metadata['rep'])


class _IOProcessBase(metaclass=ABCMeta):
    def __init__(
        self, metadata_prefix_unpacker=monkey_io_metadata_prefix_unpacker
    ):
        self.metadata = None
        self._prefix_unpacker = metadata_prefix_unpacker
        self._output_package = {}

    @property
    def prefix_unpacker(self):
        return self._prefix_unpacker

    def append_prefix(self, base_prefix):
        if self.metadata:
            return join(base_prefix, self._prefix_unpacker(self.metadata))

        return base_prefix


class PythonIOProcess(_IOProcessBase, PythonProcess, metaclass=ABCMeta):
    def __init__(
        self, name, output_prefix, input_keys=(), optional_keys=(),
        prefix_unpacker=monkey_io_metadata_prefix_unpacker
    ):
        _IOProcessBase.__init__(self, prefix_unpacker)
        PythonProcess.__init__(
            self, name, output_prefix, input_keys, optional_keys
        )

    def get_outputs(self):
        return {**self._output_package, **{"prefix": self.path_prefix}}

    @property
    def path_prefix(self):
        return _IOProcessBase.append_prefix(
            self, PythonProcess.path_prefix.fget(self)
        )


class PythonShellProcess(_IOProcessBase, ShellProcess, metaclass=ABCMeta):
    def __init__(
        self, name, output_prefix, input_keys=(), optional_keys=(),
        prefix_unpacker=monkey_io_metadata_prefix_unpacker
    ):
        _IOProcessBase.__init__(self, prefix_unpacker)
        ShellProcess.__init__(
            self, name, output_prefix, input_keys, optional_keys
        )

    def get_outputs(self):
        return {**self._output_package, **{"prefix": self.path_prefix}}

    @property
    def path_prefix(self):
        return _IOProcessBase.append_prefix(
            self, ShellProcess.path_prefix.fget(self)
        )
