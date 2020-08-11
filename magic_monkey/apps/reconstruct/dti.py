from os import getcwd

from traitlets import Instance, Bool, Dict

from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    required_file, output_prefix_argument, mask_arg
from magic_monkey.base.shell import launch_shell_process
from magic_monkey.config.dti import DTIConfiguration


_aliases = {
    'in': 'DTI.image',
    'bvals': 'DTI.bvals',
    'bvecs': 'DTI.bvecs',
    'out': 'DTI.output_prefix',
    'mask': 'DTI.mask',
}


_flags = dict(
    b0=(
        {'DTI': {'output_b0': False}},
        "output estimated b0 volume"
    ),
    dkt=(
        {'DTIMetrics': {'output_dkt': False}},
        "output kurtosis model computed upon the dti reconstruction"
    )
)


class DTI(MagicMonkeyBaseApplication):
    configuration = Instance(DTIConfiguration).tag(config=True)

    image = required_file(help="Input dwi image")
    bvals = required_file(help="Input b-values")
    bvecs = required_file(help="Input b-vectors")

    output_prefix = output_prefix_argument()

    mask = mask_arg()

    output_b0 = Bool(
        False,
        help="Outputs the b0 volume computed by the DTI estimation algorithm"
    ).tag(config=True)
    output_dkt = Bool(
        False,
        help="Outputs the kurtosis moment estimations"
    ).tag(config=True)

    aliases = Dict(_aliases)
    flags = Dict(_flags)

    def _start(self):
        current_path = getcwd()
        optionals = []

        if self.output_b0:
            optionals.append("-b0 {}_b0.nii.gz".format(
                self.output_prefix
            ))

        if self.output_dkt:
            optionals.append("-dkt {}_dkt.nii.gz".format(
                self.output_prefix
            ))

        if self.configuration.predicted_signal:
            optionals.append("-predicted_signal {}_pred_s.nii.gz".format(
                self.output_prefix
            ))

        if self.mask:
            optionals.append("-mask {}".format(
                self.mask
            ))

        optionals.append("-fslgrad {} {}".format(self.bvals, self.bvecs))
        optionals.append(self.configuration.serialize())

        command = "dwi2tensor {} {} {}".format(
            " ".join(optionals), self.image,
            "{}_dti.nii.gz".format(self.output_prefix)
        )

        launch_shell_process(command, current_path)
