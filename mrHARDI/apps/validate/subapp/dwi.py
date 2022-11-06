import nibabel as nib
import numpy as np
from traitlets import Bool, Dict, Integer

from mrHARDI.base.application import (mrHARDIBaseApplication,
                                      output_prefix_argument,
                                      required_file)


_aliases = {
    "in": "DWIValidation.dwi",
    "bvals": "DWIValidation.bvals",
    "bvecs": "DWIValidation.bvecs",
    "out": "AffineValidation.output",
    "b0-thr": "DWIValidation.b0_threshold"
}

_flags = dict(
    stdout=(
        {"DWIValidation": {"output_stdout": True}},
        "Redirect output information to stdout (else quiet)"
    )
)


class DWIValidation(mrHARDIBaseApplication):
    dwi = required_file(description="Input DWI image")
    bvals = required_file(description="Input b-values file")
    bvecs = required_file(description="Input b-vectors file")
    output = output_prefix_argument(required=False)
    output_stdout = Bool(False).tag(config=True)
    b0_threshold = Integer(
        20, help="Higher bound determining a valid b-value for a b0 volume"
    ).tag(config=True)

    aliases = Dict(default_value=_aliases)
    flags = Dict(default_value=_flags)

    def execute(self):
        img = nib.load(self.dwi)
        bvals = np.loadtxt(self.bvals)
        bvecs = np.loadtxt(self.bvecs)

        bvecs_is_row = True
        if bvecs.shape[0] > bvecs.shape[1]:
            bvecs_is_row = False
            bvecs = bvecs.T

        n_volumes = img.shape[-1]

        valid_bvals = len(bvals) == n_volumes
        valid_bvecs = bvecs.shape[1] == n_volumes

        has_b0 = np.sum(bvals < self.b0_threshold) > 0

        if self.output_stdout:
            if not has_b0:
                print("DWI image does not have b0 volumes\n")
            if not bvecs_is_row:
                print("b-vectors should be arranged in columns\n")
            if not valid_bvals:
                print(
                    "Mismatch between the number of b-values "
                    "({}) and DWI volumes ({})\n".format(
                        len(bvals), n_volumes
                    )
                )
            if bvecs_is_row and not valid_bvecs:
                print(
                    "Mismatch between the number of b-vectors "
                    "({}) and DWI volumes ({})\n".format(
                        bvecs.shape[1], n_volumes
                    )
                )

        if self.output:
            if not (
                has_b0 and bvecs_is_row and valid_bvecs and valid_bvals
            ):
                with open("{}_errors.txt".format(self.output), "w+") as f:
                    if not has_b0:
                        f.write("DWI image does not have b0 volumes\n")
                    if not bvecs_is_row:
                        f.write("b-vectors should be arranged in columns\n")
                    if not valid_bvals:
                        f.write(
                            "Mismatch between the number of b-values "
                            "({}) and DWI volumes ({})\n".format(
                                len(bvals), n_volumes
                            )
                        )
                    if bvecs_is_row and not valid_bvecs:
                        f.write(
                            "Mismatch between the number of b-vectors "
                            "({}) and DWI volumes ({})\n".format(
                                bvecs.shape[1], n_volumes
                            )
                        )
