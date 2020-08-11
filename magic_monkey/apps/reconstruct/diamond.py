from os import getcwd

from traitlets import Instance, Unicode, Dict

from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    required_file, output_prefix_argument, mask_arg
from magic_monkey.base.shell import launch_shell_process
from magic_monkey.config.diamond import DiamondConfiguration


_aliases = {
    'in': 'Diamond.image',
    'out': 'Diamond.output',
    'mask': 'Diamond.mask',
    'ms': 'Diamond.model_selection',
    'dti': 'Diamond.initial_dti'
}


class Diamond(MagicMonkeyBaseApplication):
    configuration = Instance(DiamondConfiguration).tag(config=True)

    image = required_file(
        help="Input dwi volume. B-values, b-vectors "
             "(and encoding file if using Magic Diamond) must "
             "use the same base filename for them to be detected by diamond"
    )
    output = output_prefix_argument()

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
        if not self.model_selection:
            self.configuration.mose_model.tag(required=True)

        if self.initial_dti:
            self.configuration.initial_stick.tag(required=True)

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

        launch_shell_process(command, current_path)
