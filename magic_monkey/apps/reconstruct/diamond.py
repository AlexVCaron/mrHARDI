from os import getcwd

from traitlets import Instance, Unicode, Dict

from magic_monkey.base.application import MagicMonkeyBaseApplication
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

    image = Unicode().tag(config=True, required=True)
    output = Unicode().tag(config=True, required=True)

    mask = Unicode().tag(config=True)
    model_selection = Unicode().tag(config=True)
    initial_dti = Unicode().tag(config=True)

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
