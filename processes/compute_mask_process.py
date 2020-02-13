from multiprocessing import cpu_count

from multiprocess.process import Process


class ComputeMaskProcess(Process):
    def __init__(self, in_b0, out_mask):
        super().__init__("Compute bet mask on {}".format(in_b0.split("/")[-1]))
        self._input = in_b0
        self._output = out_mask

    def execute(self):
        self._launch_process(
            "fslmaths {0} -Tmean {1}_mean".format(
                self._input,
                self._output
            )
        )
        self._launch_process(
            "bet {0}_mean {0} -m -R -v".format(
                self._output
            ),
            keep_log=True
        )
