from os import getcwd
from os.path import join, basename
from mrHARDI.base.dwi import DwiMetadata

import nibabel as nib
import numpy as np

from traitlets import Unicode, Bool, Instance, Dict

from mrHARDI.base.application import (mrHARDIBaseApplication,
                                      required_file,
                                      mask_arg,
                                      output_prefix_argument)
from mrHARDI.base.image import (load_metadata,
                                load_metadata_file,
                                save_metadata)
from mrHARDI.base.shell import launch_shell_process
from mrHARDI.config.n4bias import N4BiasCorrectionConfiguration


_aliases = {
    "in": 'N4BiasCorrection.image',
    "apply": 'N4BiasCorrection.apply_to',
    "mask": 'N4BiasCorrection.mask',
    "weights": 'N4BiasCorrection.weights',
    "out": 'N4BiasCorrection.output'
}

_flags = dict(
    bias=(
        {"N4BiasCorrection": {"output_bias": True}},
        "Outputs estimated bias field"
    )
)


class N4BiasCorrection(mrHARDIBaseApplication):

    configuration = Instance(N4BiasCorrectionConfiguration).tag(config=True)

    image = required_file(description="Input image to correct")
    output = output_prefix_argument()

    apply_to = Unicode(
        None, allow_none=True,
        help="Apply the transformation to another image after correction"
    ).tag(config=True)

    mask = mask_arg()
    weights = Unicode(
        help="Weight image to use during b-spline fitting"
    ).tag(config=True)

    output_bias = Bool(
        False, help="If true, outputs the estimated bias field"
    ).tag(config=True)

    aliases = Dict(default_value=_aliases)
    flags = Dict(default_value=_flags)

    def execute(self):
        image = nib.load(self.image)
        current_path = getcwd()

        input_image = nib.load(self.image)
        max_spacing = np.max(input_image.header.get_zooms()[:3])

        n4_output = self.output if not self.apply_to else "tmp_n4denoised"
        output_fmt = "[{}.nii.gz".format(n4_output)
        if self.output_bias or self.apply_to:
            output_fmt += ",{}_bias_field.nii.gz]".format(n4_output)
        else:
            output_fmt += "]"

        d = len(input_image.shape)
        if input_image.shape[-1] <= 1:
            d -= 1

        arguments = "--input-image {} -d {} --output {}".format(
            self.image, d, output_fmt
        )

        if self.mask:
            mask_name = self.mask
            msk = nib.load(self.mask)
            if len(msk.shape) == 3 and (
                len(msk.shape) != len(np.squeeze(input_image.shape))
            ):
                mask_name = "{}_4d_mask.nii.gz".format(self.output)
                msk_data = np.repeat(
                    msk.get_fdata()[..., None], image.shape[-1], -1
                ).astype(np.uint8)
                nib.save(nib.Nifti1Image(msk_data, msk.affine), mask_name)

            arguments += " --mask-image {}".format(mask_name)
        if self.weights:
            arguments += " --weight-image {}".format(self.weights)

        metadata = load_metadata(self.image)
        if metadata is None and self.metadata:
            metadata = load_metadata_file(self.metadata)

        command = [
            "N4BiasFieldCorrection {} {}".format(
                arguments, self.configuration.serialize(max_spacing)
            )
        ]

        if self.apply_to:
            scil_cmd = (
                "scil_apply_bias_field_on_dwi.py {} "
                "{}_bias_field.nii.gz {}.nii.gz -f".format(
                    self.apply_to, n4_output, self.output
                )
            )

            if self.mask:
                scil_cmd += " --mask {}".format(self.mask)

            command.append(scil_cmd)

        additional_env = None
        if self.configuration.seed is not None:
            additional_env = {
                "ANTS_RANDOM_SEED": self.configuration.seed
            }

        for i, cmd in enumerate(command):
            launch_shell_process(
                cmd,
                join(current_path, "{}_cmd{}.log".format(
                    basename(self.output), i
                )),
                additional_env=additional_env
            )

        if self.apply_to:
            metadata = load_metadata(self.apply_to, DwiMetadata)

        if metadata:
            save_metadata(self.output, metadata)
