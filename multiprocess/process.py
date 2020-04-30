from abc import ABCMeta, abstractmethod


class Process(metaclass=ABCMeta):
    def __init__(self, name, output_prefix):
        self._name = name
        self._input = None
        self._output_package = {
            "prefix": output_prefix
        }
        self._n_cores = 1

    def set_process_launcher(self, method):
        self._launch_process = method
        return self

    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def set_inputs(self, package):
        pass

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

    def _get_prefix(self):
        return self._output_package["prefix"]

    def _launch_process(self, command):
        pass
