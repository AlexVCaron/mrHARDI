from multiprocessing import cpu_count
from os.path import basename
from traitlets import Dict, Float, Integer, Bool

from mrHARDI.base.application import (mask_arg,
                                      mrHARDIBaseApplication,
                                      output_prefix_argument,
                                      required_file)
from mrHARDI.base.dwi import load_metadata, save_metadata
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
    use_piesno = Bool(False).tag(config=True)
    sigma_all_voxels = Bool(False).tag(config=True)

    aliases = Dict(default_value=_aliases)

    def execute(self):
        metadata = load_metadata(self.image)
        if metadata:
            n_coils = metadata.number_of_coils

        command = "scil_denoising_nlmeans.py {image} {output} {p}".format(
            image=self.image,
            output="{}.nii.gz".format(self.output),
            p="--processes {}".format(self.processes)
        )

        if self.force_sigma is not None:
            command += " --sigma {}".format(self.force_sigma)
        elif self.use_piesno:
            command += " --piesno"
        else:
            command += " --basic_sigma"
        if self.use_piesno or not self.force_sigma:
            if n_coils <= 0:
                n_coils = self.default_n_coils
    
            command += " --number_coils {}".format(n_coils)

            if self.sigma_all_voxels:
                command += " --sigma_from_all_voxels"
            elif self.mask:
                command += " --mask_sigma {}".format(self.mask)

        launch_shell_process(
            command,
            "{}.log".format(basename(self.output))
        )

        if metadata:
            save_metadata(self.output, metadata)
