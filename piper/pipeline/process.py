from abc import ABCMeta, abstractmethod

from piper import piper_config
from piper.drivers.shell import launch_shell_process
from piper.graph.serializable import Serializable


class Process(Serializable, metaclass=ABCMeta):
    def __init__(self, name, output_prefix, input_keys=[], optional_keys=[]):
        super().__init__()
        self._name = name
        self._output_package = {
            "prefix": output_prefix
        }
        self._input_keys = input_keys
        self._opt_keys = optional_keys
        self._input = None
        self._n_cores = 1

    @property
    def serialize(self):
        return {**super().serialize, **{
            'name': self.name,
            'required_inputs': self._input_keys,
            'optional_inputs': self._opt_keys,
            'n_cores': self._n_cores,
            'process_executor': str(self._launch_process)
        }}

    @property
    def launcher(self):
        return self._launch_process

    def override_process_launcher(self, launcher):
        self._launch_process = launcher
        return self

    @abstractmethod
    def _execute(self, *args, **kwargs):
        pass

    @property
    def primary_input_key(self):
        return self.get_input_keys()[0]

    def get_input_keys(self):
        return self._input_keys

    @abstractmethod
    def get_required_output_keys(self):
        pass

    def set_inputs(self, package):
        pkg = self._fill_optional(package)
        self._input = [pkg[key] for key in self._input_keys]

    def get_outputs(self):
        return self._output_package

    @property
    def name(self):
        return self._name

    @property
    def n_cores(self):
        return self._n_cores

    @n_cores.setter
    def n_cores(self, n_cores):
        self._n_cores = n_cores

    def execute(self, *args, **kwargs):
        result = self._launch_process(self._execute, *args, **kwargs)
        if result and isinstance(result, dict):
            self._output_package.update(result)

    def _get_prefix(self):
        return self._output_package["prefix"]

    def _fill_optional(self, package):
        return {**{opt: None for opt in self._opt_keys}, **package}

    @abstractmethod
    def _launch_process(self, runnable, *args, **kwargs):
        pass


class PythonProcess(Process, metaclass=ABCMeta):
    def _launch_process(self, py_method, *args, **kwargs):
        return py_method(*args, **kwargs)


class ShellProcess(Process, metaclass=ABCMeta):
    def _launch_process(self, command, log_file, *args, **kwargs):
        log_conf = piper_config.generate_shell_config()
        return launch_shell_process(
            command(*args, **kwargs), log_file, **log_conf
        )
