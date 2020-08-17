from os import getcwd

from traitlets import Bool, Dict, Instance

from magic_monkey.base.application import (MagicMonkeyBaseApplication,
                                           mask_arg,
                                           output_prefix_argument,
                                           required_file)
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

_description = """
Computes a tensor reconstruction over a diffusion-weighted image using 
*Mrtrix* [1].

References :
------------
[1] https://mrtrix.readthedocs.io/en/latest/reference/commands/dwi2tensor.html
[2] Tournier, J.-D.; Smith, R. E.; Raffelt, D.; Tabbara, R.; Dhollander, T.; 
    Pietsch, M.; Christiaens, D.; Jeurissen, B.; Yeh, C.-H. & Connelly, A. 
    MRtrix3: A fast, flexible and open software framework for medical image 
    processing and visualisation. NeuroImage, 2019, 202, 116137.
[3] Basser, P.J.; Mattiello, J.; LeBihan, D. Estimation of the effective 
    self-diffusion tensor from the NMR spin echo. J Magn Reson B., 1994, 103, 
    247–254.
[4] Veraart, J.; Sijbers, J.; Sunaert, S.; Leemans, A. & Jeurissen, B. 
    Weighted linear least squares estimation of diffusion MRI parameters: 
    strengths, limitations, and pitfalls. NeuroImage, 2013, 81, 335-346.
"""


class DTI(MagicMonkeyBaseApplication):
    description = _description
    configuration = Instance(DTIConfiguration).tag(config=True)

    image = required_file(description="Input dwi image")
    bvals = required_file(description="Input b-values")
    bvecs = required_file(description="Input b-vectors")

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
