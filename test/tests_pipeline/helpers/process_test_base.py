from os import chmod
from os.path import join
from tempfile import TemporaryDirectory, TemporaryFile


class ProcessTestBase:
    def __init__(self):
        self.test_dir = TemporaryDirectory()
        self.payload = ([], {"data": "data"})
        self.process = None

    def _execute(self, exec_kwargs={}):
        args = self.payload[0] if self.payload[0] else []
        self.process.set_inputs(self.payload[1])
        self.process.execute(*args, **exec_kwargs)

    def tearDown(self):
        self.test_dir.cleanup()


class ShellProcessTestBase(ProcessTestBase):
    def __init__(self):
        super().__init__()
        self.log_handle = TemporaryFile(dir=self.test_dir.name, delete=False)
        self.log_handle.close()
        self.payload = ([{"log_file_path": self.log_handle.name}], self.payload[1])

    def tearDown(self):
        # self.log_handle.close()
        super().tearDown()

    def _get_args(self):
        return ":".join(self.payload[1].keys())

    def _write_args_case(self, script):
        for arg in self.payload[1].keys():
            script.write("{}) {}=$OPTARG;;\n".format(arg, arg.capitalize()))

    def _write_variables(self, script):
        for arg in self.payload[1].keys():
            script.write("{}=NULL\n".format(arg.capitalize()))

        if self.payload[0] and len(self.payload[0]) > 1:
            for i in range(len(self.payload[0])):
                script.write("P_ARG{}=NULL\n".format(i))

    def _write_positional_args(self, script):
        if self.payload[0] and len(self.payload[0]) > 1:
            for i in range(len(self.payload[0])):
                script.write("".join([
                    "P_ARG{}=$".format(i),
                    "{@:$OPTIND+",
                    "{}:1".format(i),
                    "}\n"
                ]))

    def _write_script_func(self, script):
        script.write("function assert() {\n")
        script.write("    cond=$1\n")
        script.write("    message=$2\n")
        script.write("    if $cond; then\n")
        script.write("        echo \"Success\"\n")
        script.write("    else\n")
        script.write("        echo \"Error : $message\"\n")
        script.write("        exit 2\n")
        script.write("    fi\n")
        script.write("}\n")

    def _write_args_assert(self, script):
        fmt = "assert [ ${} {} {} ] \"Awaited {} Received ${}\"\n"
        str_types = (str, bool)

        for arg, val in self.payload[1].items():
            op = "==" if isinstance(val, str_types) else "-eq"
            script.write(fmt.format(
                arg.capitalize(), op, val, val, arg.capitalize()
            ))

        if self.payload[0] and len(self.payload[0]) > 1:
            for i in range(len(self.payload[0])):
                val = self.payload[0][i]
                op = "==" if isinstance(val, str_types) else "-eq"
                script.write(fmt.format(
                    "P_ARG{}".format(i), op,
                    val, val, "P_ARG{}".format(i)
                ))

    def _get_script(self, fail=False):
        output = {"completion_flag": join(self.test_dir.name, "complete.flag")}
        script = join(self.test_dir.name, "script.sh")

        file = open(script, "w+")
        file.write("#!/usr/bin/env bash\n")
        file.write("# This script is generated to test processes\n")
        file.write("# Error codes :\n")
        file.write("#   - 1 : the script has failed (awaited behaviour)\n")
        file.write("#   - 2 : assertation error\n")
        file.write("#\n\n")

        self._write_variables(file)

        file.write("while getopts {}: opts; do\n".format(self._get_args()))
        file.write("case ${opts} in\n")

        self._write_args_case(file)

        file.write("esac\n")
        file.write("done\n")

        self._write_positional_args(file)
        self._write_script_func(file)
        self._write_args_assert(file)

        if fail:
            file.write("exit 1\n")

        file.write("touch {}\n".format(output["completion_flag"]))
        file.write("exit 0\n")

        file.close()

        chmod(script, 777)

        return script, output

    def _assert_shell(self):
        pass
