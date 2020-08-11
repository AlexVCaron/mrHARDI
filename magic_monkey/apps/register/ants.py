from os import getcwd

from traitlets import Instance, Unicode, Dict

from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    MultipleArguments, required_arg, output_prefix_argument, \
    output_file_argument, required_file
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

    target_images = required_arg(
        MultipleArguments, traits_args=(Unicode,),
        help="List of target images used in the passes of registration. "
             "Those must equal the number of metric evaluations of the "
             "resulting output command, including the initial transform "
             "(if selected) as well as repetitions"
    )
    moving_images = required_arg(
        MultipleArguments, traits_args=(Unicode,),
        help="List of moving images used in the passes of registration. "
             "Those must equal the number of metric evaluations of the "
             "resulting output command, including the initial transform "
             "(if selected) as well as repetitions"
    )

    output_prefix = output_prefix_argument()

    aliases = Dict(_reg_aliases)

    def _start(self):
        current_path = getcwd()

        ants_config_fmt = self.configuration.serialize()
        config_dict = {}
        for i, (target, moving) in enumerate(zip(
            self.target_images, self.moving_images
        )):
            config_dict["t{}".format(i)] = target
            config_dict["m{}".format(i)] = moving

        ants_config_fmt.format(**config_dict)

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
    configuration = Instance(AntsTransformConfiguration).tag(config=True)

    image = required_file(help="Input image to transform")
    transformation_matrix = required_file(
        help="Input transformation matrix computed by ants to apply"
    )
    transformation_ref = required_file(
        help="Input transformation field computed by ants to apply "
             "or reference image for affine/rigid transformation"
    )

    output = output_file_argument()

    aliases = Dict(_tr_aliases)

    def _start(self):
        current_path = getcwd()

        command = "antsApplyTransform -i {} -r {} -t {} -o {} {}".format(
            self.image, self.transformation_matrix, self.transformation_ref,
            self.output, self.configuration.serialize()
        )

        launch_shell_process(command, current_path)
