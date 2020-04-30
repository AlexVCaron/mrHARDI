from config import append_image_extension
from multiprocess.process import Process


class ComputeMaskProcess(Process):
    def __init__(self, output_prefix):
        super().__init__("Compute bet mask", output_prefix)

    def set_inputs(self, package):
        self._input = package["img"]

    def execute(self):
        output_img = append_image_extension(self._get_prefix())

        self._launch_process(
            "fslmaths {0} -Tmean {1}_mean".format(
                self._input,
                output_img
            )
        )
        self._launch_process(
            "bet {0}_mean {0} -m -R -v".format(
                output_img
            ),
            keep_log=True
        )

        self._output_package.update({
            "mask": output_img
        })
