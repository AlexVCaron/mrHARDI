import sys
from shutil import copyfile

from piper.pipeline.process import PythonProcess


class CopyFilesProcess(PythonProcess):
    def __init__(self):
        super().__init__(
            "Copy {} files",
            ["files_in", "files_out"]
        )

    @property
    def required_output_keys(self):
        return [self.primary_input_key]

    def execute(self):
        self._launch_process(self._execute)

    def _execute(self, log_file_path):
        std_out = sys.stdout
        with open(log_file_path, "w+") as log_file:
            for input, output in zip(*self._input):
                log_file.write("Copying files :\n")
                log_file.write("    - From : {}\n".format(input))
                log_file.write("    - To : {}\n".format(output))
                sys.stdout = log_file
                copyfile(input, output)
                sys.stdout = std_out

        self._output_package.update({
            self.primary_input_key: [o_img for o_img in self._input[1]]
        })
