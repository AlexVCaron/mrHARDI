from config import append_image_extension
from piper.pipeline.process import ShellProcess


class ComputeMaskProcess(ShellProcess):
    def __init__(self, output_prefix, img_key_deriv="img"):
        super().__init__("Compute bet mask", output_prefix, [img_key_deriv])

    def set_inputs(self, package):
        self._input = package[self.primary_input_key]

    def get_required_output_keys(self):
        return ["mask"]

    def _execute(self, cmd, *args, **kwargs):
        return cmd.format(*args)

    def execute(self, *args, **kwargs):
        output_img = append_image_extension(self._get_prefix())

        super().execute(
            "fslmaths {0} -Tmean {1}_mean", *args,
            self._input, output_img, **kwargs
        )
        super().execute(
            "bet {0}_mean {0} -m -R -v", *args, output_img, **kwargs
        )

        self._output_package.update({
            "mask": output_img
        })
