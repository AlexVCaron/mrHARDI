from os import getcwd
from os.path import basename, join

from traitlets import Dict, Instance, Unicode

from magic_monkey.base.application import (MagicMonkeyBaseApplication,
                                           mask_arg,
                                           output_file_argument,
                                           required_file)
from magic_monkey.base.shell import launch_shell_process
from magic_monkey.config.diamond import DiamondConfiguration

_aliases = {
    'in': 'Diamond.image',
    'out': 'Diamond.output',
    'mask': 'Diamond.mask',
    'ms': 'Diamond.model_selection',
    'dti': 'Diamond.initial_dti'
}

_description = """
Computes diffusion tensor distributions of fiber populations over diffusion 
weighted images. The program uses the diamond reconstruction algorithm [1] to 
perform the optimization of the distributions over the voxels of the input 
image. If an image resulting from a concatenation of multiple tensor-valued 
acquisitions is supplied instead, the magic diamond version [2] of the 
algorithm is used.

References : 
------------
[1] Scherrer, B., Schwartzman, A., Taquet, M., Sahin, M., Prabhu, S.P. and 
    Warfield, S.K. (2016), Characterizing brain tissue by assessment of the 
    distribution of anisotropic microstructural environments in 
    diffusion‐compartment imaging (DIAMOND). Magn. Reson. Med., 76: 963-977. 
    doi:10.1002/mrm.25912.
[2] A. Reymbaut and A. Valcourt Caron and G. Gilbert and F. Szczepankiewicz 
    and M. Nilsson and S. K. Warfield and M. Descoteaux and B. Scherrer. Magic 
    DIAMOND: Multi-Fascicle Diffusion Compartment Imaging with Tensor 
    Distribution Modeling and Tensor-Valued Diffusion Encoding. Arxiv, 
    2004.07340, 2020.
"""


class Diamond(MagicMonkeyBaseApplication):
    name = u"Diamond"
    description = _description
    configuration = Instance(DiamondConfiguration).tag(config=True)

    image = required_file(
        description="Input dwi volume. B-values, b-vectors "
                    "(and encoding file if using Magic Diamond) must "
                    "use the same base filename for them to be detected "
                    "by diamond"
    )
    output = output_file_argument()

    mask = mask_arg()

    model_selection = Unicode(
        help="Pre-computed model selection for the dataset"
    ).tag(config=True)
    initial_dti = Unicode(
        help="Pre-computed dti reconstruction used to initialize "
             "the stick model of the diamond algorithms"
    ).tag(config=True)

    aliases = Dict(_aliases)

    def _validate_required(self):
        if self.model_selection:
            self.configuration.estimate_mose = False
        else:
            self.configuration.traits()["mose_model"].tag(required=True)

        if self.initial_dti:
            self.configuration.traits()["initial_stick"].tag(required=True)

        super()._validate_required()

    def _start(self):
        current_path = getcwd()
        optionals = []

        if self.mask:
            optionals.append("-m {}".format(self.mask))

        if self.model_selection:
            optionals.append("--mosemask {}".format(self.model_selection))

        if self.initial_dti:
            optionals.append("--init_dti {}".format(self.initial_dti))

        optionals.append(self.configuration.serialize())

        command = "crlDCIEstimate -i {} -o {} {}".format(
            self.image, self.output, " ".join(optionals)
        )

        launch_shell_process(command, join(current_path, "{}.log".format(
            basename(self.output).split(".")[0]
        )))
