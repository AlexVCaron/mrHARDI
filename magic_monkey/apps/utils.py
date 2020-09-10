from copy import deepcopy
from os import getcwd
from os.path import basename, join

import nibabel as nib
import numpy as np
from traitlets import Dict, Enum, Instance, Integer, Unicode, re
from traitlets.config import Config

from magic_monkey.base.application import (MagicMonkeyBaseApplication,
                                           MultipleArguments,
                                           output_file_argument,
                                           output_prefix_argument,
                                           required_arg,
                                           required_file)
from magic_monkey.base.shell import launch_shell_process
from magic_monkey.compute.b0 import extract_b0, squash_b0
from magic_monkey.compute.utils import apply_mask_on_data, concatenate_dwi
from magic_monkey.config.utils import B0UtilsConfiguration

_b0_aliases = {
    'in': 'B0Utils.image',
    'bvals': 'B0Utils.bvals',
    'bvecs': 'B0Utils.bvecs',
    'out': 'B0Utils.prefix'
}

_b0_description = """
Utility program used to either extract B0 from a diffusion-weighted image or 
squash those B0 and output the resulting image.
"""


class B0Utils(MagicMonkeyBaseApplication):
    name = u"B0 Utilities"
    description = _b0_description
    configuration = Instance(B0UtilsConfiguration).tag(config=True)

    image = required_file(description="Input dwi image")
    bvals = required_file(description="Input b-values")
    bvecs = Unicode(help="Input b-vectors").tag(config=True, ignore_write=True)

    prefix = output_prefix_argument()

    aliases = Dict(_b0_aliases)

    def initialize(self, argv=None):
        assert argv and len(argv) > 0
        if not (
            any("help" in a for a in argv) or
            any("out-config" in a for a in argv) or
            any("safe" in a for a in argv)
        ):
            command, argv = argv[0], argv[1:]
            assert re.match(r'^\w(-?\w)*$', command), \
                "First argument must be the sub-utility to use {}".format(
                    B0UtilsConfiguration.current_util.values
                )
            super().initialize(argv)

            config = deepcopy(self.config)
            config['B0UtilsConfiguration'] = Config(current_util=command)
            self.update_config(config)
        else:
            super().initialize(argv)

    def _example_command(self, sub_command):
        return "magic_monkey {} [extract|squash] <args> <flags>".format(
            sub_command
        )

    def _start(self):
        if self.configuration.current_util == "extract":
            self._extract_b0()
        elif self.configuration.current_util == "squash":
            self._squash_b0()
        else:
            self.print_help()

    def _extract_b0(self):
        in_dwi = nib.load(self.image)
        bvals = np.loadtxt(self.bvals)

        data = extract_b0(
            in_dwi.get_fdata(), bvals,
            self.configuration.strides,
            self.configuration.mean_strategy
        )

        nib.save(
            nib.Nifti1Image(data, in_dwi.affine),
            "{}.nii.gz".format(self.prefix)
        )

    def _squash_b0(self):
        in_dwi = nib.load(self.image)
        bvals = np.loadtxt(self.bvals)

        if self.bvecs:
            bvecs = np.loadtxt(self.bvecs)
        else:
            bvecs = np.repeat([[1, 0, 0]], len(bvals), 0)

        data, bvals, bvecs = squash_b0(
            in_dwi.get_fdata(), bvals, bvecs, self.configuration.mean_strategy
        )

        nib.save(
            nib.Nifti1Image(
                data.astype(self.configuration.dtype), in_dwi.affine
            ),
            "{}.nii.gz".format(self.prefix)
        )

        np.savetxt("{}.bvals".format(self.prefix), bvals, fmt="%d")

        if self.bvecs:
            np.savetxt("{}.bvecs".format(self.prefix), bvecs, fmt="%.6f")


_apply_mask_aliases = {
    'in': 'ApplyMask.image',
    'out': 'ApplyMask.output',
    'mask': 'ApplyMask.mask',
    'fill': 'ApplyMask.fill_value',
    'type': 'ApplyMask.dtype'
}


class ApplyMask(MagicMonkeyBaseApplication):
    name = u"Apply Mask"
    description = "Applies a mask to an image an fill the outside."
    image = required_file(description="Input image to mask")
    mask = required_file(description="Mask to apply on image ")

    fill_value = Integer(
        0, help="Value used to fill the image outside the mask"
    ).tag(config=True, required=True)
    dtype = Enum(
        [np.int, np.long, np.float], np.int, help="Output type"
    ).tag(config=True, required=True)

    output = output_file_argument()

    aliases = Dict(_apply_mask_aliases)

    def _start(self):
        data = nib.load(self.image)
        mask = nib.load(self.mask).get_fdata().astype(bool)

        out_data = apply_mask_on_data(data.get_fdata(), mask, self.dtype)

        nib.save(nib.Nifti1Image(out_data, data.affine), self.output)


_cat_aliases = {
    'in': 'Concatenate.images',
    'out': 'Concatenate.prefix',
    'bvals': 'Concatenate.bvals',
    'bvecs': 'Concatenate.bvecs'
}


class Concatenate(MagicMonkeyBaseApplication):
    name = u"Concatenate"
    description = "Concatenates multiple images together"
    images = required_arg(
        MultipleArguments, traits_args=(Unicode,),
        description="Input images to concatenate"
    )

    bvals = MultipleArguments(
        Unicode, help="If provided, will be also concatenated"
    ).tag(config=True)
    bvecs = MultipleArguments(
        Unicode, help="If provided, will be also concatenated"
    ).tag(config=True)

    prefix = output_prefix_argument()

    aliases = Dict(_cat_aliases)

    def _start(self):
        dwi_list = [nib.load(dwi) for dwi in self.images]
        bvals_list = [
            np.loadtxt(bvals) for bvals in self.bvals
        ] if self.bvals else None
        bvecs_list = [
            np.loadtxt(bvecs) for bvecs in self.bvecs
        ] if self.bvecs else None

        reference_affine = dwi_list[0].affine

        out_dwi, out_bvals, out_bvecs = concatenate_dwi(
            [dwi.get_fdata() for dwi in dwi_list],
            bvals_list,
            bvecs_list
        )

        nib.save(
            nib.Nifti1Image(out_dwi, reference_affine),
            "{}.nii.gz".format(self.prefix)
        )

        if out_bvals is not None:
            np.savetxt("{}.bvals".format(self.prefix), out_bvals, fmt="%d")

        if out_bvecs is not None:
            np.savetxt("{}.bvecs".format(self.prefix), out_bvecs.T, fmt="%.6f")


class ApplyTopup(MagicMonkeyBaseApplication):
    name = u"Apply Topup"
    description = "Apply a Topup transformation to an image"

    topup_prefix = required_file(
        description="Path and file prefix of the files corresponding "
                    "to the transformation calculated by Topup"
    )

    images = required_arg(
        MultipleArguments, traits_args=(Unicode,),
        description="Input forward acquired images"
    )

    rev_images = MultipleArguments(
        Unicode, help="Input reverse acquired images"
    ).tag(config=True, ignore_write=True)

    output_prefix = output_prefix_argument()

    mode = Enum(
        ["interlaced", "sequential"], "interlaced",
        help="Mode in which Topup was applied to the dataset. Either the "
             "forward and reversed acquisition B0 volumes were interlaced, "
             "one pair after another, or the forward block is all put in "
             "first, the revered in last."
    ).tag(config=True)

    resampling = Enum(
        ["jac", "slr"], "slr", help="Resampling method"
    ).tag(config=True)

    interpolation = Enum(
        ["trilinear", "spline"], "spline",
        help="Interpolation method, only used with jacobian resampling (jac)"
    ).tag(Config=True)

    dtype = Enum(
        ["char", "short", "int", "float", "double"], None, allow_none=True,
        help="Force output type. If none supplied, "
             "will be the same as the input type."
    ).tag(config=True)

    def _start(self):
        working_dir = getcwd()

        args = "--topup={} --out={} --method={} --interp={}".format(
            self.topup_prefix, self.output_prefix,
            self.resampling, self.interpolation
        )

        if self.mode == "interlaced" and len(self.rev_images) > 0:
            args = "--imain={} {}".format(
                ",".join([
                    img for p in zip(self.images, self.rev_images) for img in p
                ]),
                args
            )
        else:
            args = "--imain={} {}".format(
                ",".join(self.images + self.rev_images), args
            )

        args += " --inindex={}".format(
            ",".join(str(i) for i in range(
                1, len(self.images) + len(self.rev_images) + 1
            ))
        )

        if self.dtype:
            args += " --datatype={}".format(self.dtype)

        launch_shell_process(
            'applytopup {}'.format(args), join(working_dir, "{}.log".format(
                basename(self.output_prefix)
            ))
        )
