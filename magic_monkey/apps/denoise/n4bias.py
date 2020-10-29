from os import getcwd
from os.path import join, basename

import nibabel as nib
import numpy as np

from traitlets import Unicode, Bool, Instance, Dict

from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    required_file, mask_arg, output_prefix_argument
from magic_monkey.base.dwi import load_metadata
from magic_monkey.base.shell import launch_shell_process
from magic_monkey.config.n4bias import N4BiasCorrectionConfiguration


_aliases = {
    "in": 'N4BiasCorrection.image',
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


class N4BiasCorrection(MagicMonkeyBaseApplication):

    configuration = Instance(N4BiasCorrectionConfiguration).tag(config=True)

    image = required_file(description="Input image to correct")
    output = output_prefix_argument()

    mask = mask_arg()
    weights = Unicode(
        help="Weight image to use during b-spline fitting"
    ).tag(config=True)

    output_bias = Bool(
        False, help="If true, outputs the estimated bias field"
    ).tag(config=True)

    aliases = Dict(_aliases)
    flags = Dict(_flags)

    def execute(self):
        image = nib.load(self.image)
        current_path = getcwd()

        input_image = nib.load(self.image)

        output_fmt = "[{}.nii.gz".format(self.output)
        if self.output_bias:
            output_fmt += ",{}_bias_field.nii.gz]".format(self.output)
        else:
            output_fmt += "]"

        arguments = "--input-image {} -d {} --output {}".format(
            self.image, len(input_image.shape), output_fmt
        )

        if self.mask:
            msk = nib.load(self.mask)
            if len(msk.shape) == 3:
                msk_data = np.repeat(
                    msk.get_fdata()[..., None], image.shape[-1], -1
                )
                nib.save(
                    nib.Nifti1Image(msk_data, msk.affine),
                    "{}_4d_mask.nii.gz".format(self.output)
                )
                self.mask = "{}_4d_mask.nii.gz".format(self.output)

            arguments += " --mask-image {}".format(self.mask)
        if self.weights:
            arguments += " --weight-image {}".format(self.weights)

        metadata = load_metadata(self.image)
        self.configuration.spacing = metadata.get_spacing()

        if len(self.configuration.spacing) < len(input_image.shape):
            self.configuration.spacing += [1.]

        launch_shell_process(
            "N4BiasFieldCorrection {} {}".format(
                arguments, self.configuration.serialize()
            ),
            join(current_path, "{}.log".format(basename(self.output)))
        )
