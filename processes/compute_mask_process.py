from config import append_image_extension
from multiprocess.pipeline.process import Process


class ComputeMaskProcess(Process):
    def __init__(self, output_prefix, img_key_deriv="img"):
        super().__init__("Compute bet mask", output_prefix, [img_key_deriv])

    def set_inputs(self, package):
        self._input = package[self.primary_input_key]

    def _execute(self, cmd, *args, **kwargs):
        return cmd.format(*args)

    def execute(self):
        output_img = append_image_extension(self._get_prefix())

        super().execute(
            "fslmaths {0} -Tmean {1}_mean", self._input, output_img
        )
        super().execute("bet {0}_mean {0} -m -R -v", output_img)

        self._output_package.update({
            "mask": output_img
        })
