from multiprocessing import cpu_count
from os.path import basename
from traitlets import Dict, Float,Integer

from mrHARDI.base.application import (mask_arg,
                                      mrHARDIBaseApplication,
                                      output_prefix_argument,
                                      required_file)
from mrHARDI.base.image import load_metadata, save_metadata
from mrHARDI.base.shell import launch_shell_process


_aliases = {
    "in": "NonLocalMeans.image",
    "out": "NonLocalMeans.output",
    "mask": "NonLocalMeans.mask",
    "coils": "NonLocalMeans.default_n_coils",
    "sigma": "NonLocalMeans.force_sigma",
    "processes": "NonLocalMeans.processes"
}

class NonLocalMeans(mrHARDIBaseApplication):

    image = required_file(description="Input image to correct")
    output = output_prefix_argument()

    mask = mask_arg()
    default_n_coils = Integer(0).tag(config=True)
    force_sigma = Float(None, allow_none=True).tag(config=True)
    processes = Integer(cpu_count()).tag(config=True)

    aliases = Dict(default_value=_aliases)

    def execute(self):
        n_coils = self.default_n_coils

        metadata = load_metadata(self.image)
        if metadata:
            n_coils = metadata.number_of_coils

        command = "scil_run_nlmeans.py {image} {output} {n_coils} {p}".format(
            image=self.image,
            output="{}.nii.gz".format(self.output),
            n_coils=n_coils,
            p="--processes {}".format(self.processes)
        )

        if self.force_sigma is not None:
            command += " --sigma {}".format(self.force_sigma)

        if self.mask:
            command += " --mask {}".format(self.mask)

        launch_shell_process(
            command,
            "{}.log".format(basename(self.output))
        )

        if metadata:
            save_metadata(self.output, metadata)
