from os import getcwd
from os.path import basename, join

import numpy as np
from traitlets import Dict, Enum, Instance, Unicode, Bool

import nibabel as nib

from magic_monkey.base.application import (MagicMonkeyBaseApplication,
                                           MultipleArguments,
                                           output_file_argument,
                                           output_prefix_argument,
                                           required_arg,
                                           required_file)
from magic_monkey.base.dwi import load_metadata, save_metadata
from magic_monkey.base.shell import launch_shell_process
from magic_monkey.config.ants import (AntsConfiguration,
                                      AntsTransformConfiguration,
                                      AntsMotionCorrectionConfiguration)

from magic_monkey.traits.ants import AntsAffine, AntsRigid, AntsSyN

_reg_aliases = {
    'target': 'AntsRegistration.target_images',
    'moving': 'AntsRegistration.moving_images',
    'out': 'AntsRegistration.output_prefix'
}

_reg_flags = dict(
    verbose=(
        {"AntsRegistration": {'verbose': True}},
        "Enables verbose output"
    )
)

_reg_description = """
Perform registration of a dataset over another one using Ants [1]. More 
information on the construction of an Ants command can be found here [2].

References :
------------
[1] http://stnava.github.io/ANTs/
[2] https://github.com/ANTsX/ANTs/wiki/Anatomy-of-an-antsRegistration-call
"""


class AntsRegistration(MagicMonkeyBaseApplication):
    name = u"ANTs Registration"
    description = _reg_description
    configuration = Instance(AntsConfiguration).tag(config=True)

    target_images = required_arg(
        MultipleArguments, traits_args=(Unicode,),
        description="List of target images used in the passes of "
                    "registration. Those must equal the number of metric "
                    "evaluations of the resulting output command, including "
                    "the initial transform (if selected)"
    )
    moving_images = required_arg(
        MultipleArguments, traits_args=(Unicode,),
        description="List of moving images used in the passes of "
                    "registration. Those must equal the number of metric "
                    "evaluations of the resulting output command, including "
                    "the initial transform (if selected)"
    )

    output_prefix = output_prefix_argument()

    verbose = Bool(False).tag(config=True)

    aliases = Dict(_reg_aliases)
    flags = Dict(_reg_flags)

    def _generate_config_file(self, filename):
        self.configuration.passes = [
            AntsRigid(), AntsAffine(), AntsSyN()
        ]
        super()._generate_config_file(filename)

    def execute(self):
        current_path = getcwd()

        ants_config_fmt, config_dict = self.configuration.serialize(), {}

        for i, (target, moving) in enumerate(zip(
            self.target_images, self.moving_images
        )):
            config_dict["t{}".format(i)] = target
            config_dict["m{}".format(i)] = moving

        ants_config_fmt = ants_config_fmt.format(**config_dict)

        ants_config_fmt += " --output [{},{}]".format(
            self.output_prefix, "{}_warped.nii.gz".format(self.output_prefix)
        )

        if self.verbose:
            ants_config_fmt += " --verbose"

        launch_shell_process(
            "antsRegistration {}".format(ants_config_fmt),
            join(current_path, "{}.log".format(
                basename(self.output_prefix)
            ))
        )

        metadata = load_metadata(self.moving_images[0])
        if metadata:
            save_metadata("{}_warped".format(self.output_prefix), metadata)


_tr_aliases = {
    'in': 'AntsTransform.image',
    'out': 'AntsTransform.output',
    'mat': 'AntsTransform.transformation_matrix',
    'ref': 'AntsTransform.transformation_ref',
    'trans': 'AntsTransform.transformations'
}

_tr_description = """
Apply a transformation (rigid, affine, non-linear) precomputed via Ants to an 
image.
"""


class AntsTransform(MagicMonkeyBaseApplication):
    name = u"ANTs Transform"
    description = _tr_description
    configuration = Instance(AntsTransformConfiguration).tag(config=True)

    image = required_file(description="Input image to transform")

    transformation_ref = required_file(
        description="Reference image for initial rigid transformation"
    )

    transformation_matrix = Unicode(
        help="Input affine transformation matrix computed by ants"
    ).tag(config=True, ignore_write=True)

    transformations = MultipleArguments(
        Unicode, help="List of transformations to apply after initial "
                      "rigid registration (and affine if supplied)"
    ).tag(config=True, ignore_write=True)

    output = output_file_argument()

    aliases = Dict(_tr_aliases)

    def execute(self):
        current_path = getcwd()

        image = nib.load(self.image)
        shape = image.shape
        dtype = image.get_data_dtype()

        is_3d_data = not (len(shape) == 4 and shape[-1] > 1)
        img_type = (
            0 if is_3d_data else
            1 if shape[-1] == 3 and np.issubtype(dtype, np.number.inexact) else
            2 if shape[-1] == 6 and np.issubtype(dtype, np.number.inexact) else
            3
        )

        args = "-i {} -e {} -r {} -o {}".format(
            self.image, img_type, self.transformation_ref, self.output
        )

        if self.transformations and len(self.transformations) > 0:
            args += "".join(" -t {}".format(t) for t in self.transformations)

        if self.transformation_matrix:
            args += " -t {}".format(self.transformation_matrix)

        command = "antsApplyTransforms {} {}".format(
            args, self.configuration.serialize()
        )

        launch_shell_process(command, join(current_path, "{}.log".format(
            basename(self.output).split(".")[0]
        )))

        metadata = load_metadata(self.image)
        if metadata:
            save_metadata(self.output.split(".")[0], metadata)


_motion_description = """
Perform motion correction (registration) of timeseries over templates using 
Ants [1]. The stages of registration are the same as antsRegistration, except 
there isn't a specification of convergence. The algorithm will thus run the 
total number of iterations specified for each stage before going to the next. 
An example of execution can be found at [2] or [3].

References :
------------
[1] http://stnava.github.io/ANTs/
[2] https://github.com/ANTsX/ANTs/blob/master/Scripts/antsMotionCorrExample
[3] https://stnava.github.io/fMRIANTs/
"""


class AntsMotionCorrection(MagicMonkeyBaseApplication):
    name = u"ANTs Motion Correction"
    description = _motion_description
    configuration = Instance(AntsMotionCorrectionConfiguration).tag(config=True)

    target_images = required_arg(
        MultipleArguments, traits_args=(Unicode,),
        description="List of target images (2D or 3D) used in the passes of "
                    "registration. Those must equal the number of metric "
                    "evaluations of the resulting output command"
    )

    moving_images = required_arg(
        MultipleArguments, traits_args=(Unicode,),
        description="List of moving images (must be 3D or 4D timeseries) used "
                    "in the passes of registration. Those must equal the "
                    "number of metric evaluations of the resulting output "
                    "command"
    )

    def execute(self):
        pass