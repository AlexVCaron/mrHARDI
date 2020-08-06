from os import getcwd

from traitlets import Instance, List, Unicode, Dict

from magic_monkey.base.application import MagicMonkeyBaseApplication
from magic_monkey.base.shell import launch_shell_process
from magic_monkey.config.ants import AntsConfiguration, \
                                     AntsTransformConfiguration


_reg_aliases = {
    'target': 'AntsRegistration.target_images',
    'moving': 'AntsRegistration.moving_images',
    'out': 'AntsRegistration.output_prefix'
}


class AntsRegistration(MagicMonkeyBaseApplication):
    configuration = Instance(AntsConfiguration).tag(config=True)

    target_images = List(Unicode).tag(config=True, required=True)
    moving_images = List(Unicode).tag(config=True, required=True)

    output_prefix = Unicode().tag(config=True, required=True)

    aliases = Dict(_reg_aliases)

    def start(self):
        current_path = getcwd()

        ants_config_fmt = self.configuration.serialize()
        config_dict = {}
        for i, (target, moving) in enumerate(zip(
            self.target_images, self.moving_images
        )):
            config_dict["t{}".format(i)] = target
            config_dict["m{}".format(i)] = moving

        ants_config_fmt.format(config_dict)

        ants_config_fmt += " --output [{},{}]".format(
            "{}.mat".format(self.output_prefix),
            "{}_warped.nii.gz".format(self.output_prefix)
        )

        launch_shell_process(
            "antsRegistration {}".format(ants_config_fmt), current_path
        )


_tr_aliases = {
    'in': 'AntsTransform.image',
    'out': 'AntsTransform.output',
    'mat': 'AntsTransform.transformation_matrix',
    'ref': 'AntsTransform.transformation_ref'
}


class AntsTransform(MagicMonkeyBaseApplication):
    configuration = Instance(AntsTransformConfiguration).tag(
        config=True, required=True
    )

    image = Unicode().tag(config=True, required=True)
    transformation_matrix = Unicode().tag(config=True, required=True)
    transformation_ref = Unicode().tag(config=True, required=True)

    output = Unicode().tag(config=True, required=True)

    aliases = Dict(_tr_aliases)

    def _start(self):
        current_path = getcwd()

        command = "antsApplyTransform -i {} -r {} -t {} -o {} {}".format(
            self.image, self.transformation_matrix, self.transformation_ref,
            self.output, self.configuration.serialize()
        )

        launch_shell_process(command, current_path)
