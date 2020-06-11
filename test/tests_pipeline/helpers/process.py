from os.path import exists, dirname
from uuid import uuid4

from multiprocess.pipeline.process import Process
from multiprocess.scheduler import Scheduler


class BaseTestProcess:
    def __init__(self, awaited_payload):
        self._awaited_payload = awaited_payload
        self._received_payload = None

    def _assert_payload(self):
        assert self._received_payload
        assert self._received_payload == self._awaited_payload

    def set_inputs(self, package):
        self._received_payload = package

    def get_input_keys(self):
        return self._awaited_payload.keys()


class AssertPythonProcess(BaseTestProcess, Process):
    def __init__(self, output_prefix, awaited_payload):
        BaseTestProcess.__init__(self, awaited_payload)
        Process.__init__(self, self.__class__.__name__, output_prefix)
        self.set_process_launcher(Scheduler.Launchers.PYTHON)

    def _execute(self, log_file_path, *args, **kwargs):
        self._assert_payload()

        assert log_file_path
        assert exists(dirname(log_file_path))

        self._output_package.update(self._received_payload)


class AssertShellProcess(BaseTestProcess, Process):
    def __init__(
        self, test_script, output_prefix, awaited_payload,
        awaited_output, assert_shell_fn=lambda: None
    ):
        BaseTestProcess.__init__(self, awaited_payload)
        Process.__init__(self, self.__class__.__name__, output_prefix)

        self._script = test_script
        self._awaited_output = awaited_output
        self._assert_shell = assert_shell_fn
        self._launch_process = Scheduler.Launchers.SHELL

    def _execute(self, *args, **kwargs):
        return "sh {} {} {}".format(
            self._script,
            " ".join(args),
            " ".join([
                "-{} {}".format(k, v)
                for k, v in kwargs.items()
            ])
        )

    def execute(self, *args, **kwargs):
        self._assert_payload()

        if "l_conf" in kwargs:
            args = (kwargs.pop("l_conf"),) + args

        Process.execute(self, *args, **{**kwargs, **self._received_payload})

        self._assert_shell()

        self._output_package.update(self._awaited_output)


def shell_launcher_change_payload(method, l_conf, *args, **kwargs):
    args, kwargs = _modify_arguments(*args, **kwargs)
    return Scheduler.Launchers.SHELL.value()(method, l_conf, *args, **kwargs)


def python_launcher_changes_payload(method, *args, **kwargs):
    args, kwargs = _modify_arguments(*args, **kwargs)
    return Scheduler.Launchers.PYTHON.value()(method, *args, **kwargs)


def _modify_arguments(*args, **kwargs):
    if args and len(args) > 0:
        args = args[1:]

    if kwargs and len(kwargs) > 0:
        kwargs.popitem()

    return args, kwargs


class DummyProcess(Process):
    def __init__(self, name, output_prefix, input_keys, new_output_keys):
        super().__init__(name, output_prefix)
        self._input_keys = input_keys
        self._output_keys = new_output_keys
        self._input = None
        self.set_process_launcher(Scheduler.Launchers.PYTHON)

    def _execute(self, *args, **kwargs):
        self._output_package.update(self._input)
        self._output_package.update({k: None for k in self._output_keys})

    def get_input_keys(self):
        return self._input_keys

    def get_output_keys(self):
        return self._input_keys + self._output_keys

    def set_inputs(self, package):
        self._input = package


class AddUniqueArgProcess(DummyProcess):
    def __init__(self, name, output_prefix, input_keys):
        super().__init__(name, output_prefix, input_keys, [str(uuid4())])
        self._input_keys = input_keys
        self._input = None
        self.set_process_launcher(Scheduler.Launchers.PYTHON)

    def get_unique_key(self):
        return self._output_keys[0]

    def assert_process(self):
        assert all(k in self._input for k in self._input_keys)

    def _execute(self, *args, **kwargs):
        self._output_package.update(self._input)
        self._output_package[self.get_unique_key()] = self
