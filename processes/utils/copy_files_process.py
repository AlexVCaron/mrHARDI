import sys
from shutil import copyfile

from multiprocess.pipeline.process import Process


class CopyFilesProcess(Process):
    def __init__(self, files_in, files_out):
        super().__init__("Copy {} files")
        self._input = files_in
        self._output = files_out

    def execute(self):
        self._launch_process(self._execute)

    def _execute(self, log_file_path):
        std_out = sys.stdout
        with open(log_file_path, "w+") as log_file:
            for input, output in zip(self._input, self._output):
                log_file.write("Copying files :\n")
                log_file.write("    - From : {}\n".format(input))
                log_file.write("    - To : {}\n".format(output))
                sys.stdout = log_file
                copyfile(input, output)
                sys.stdout = std_out
