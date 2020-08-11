import nibabel as nib
import numpy as np

from traitlets import Instance, Unicode, Integer, Enum, Dict

from magic_monkey.compute.b0 import extract_b0, squash_b0
from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    required_file, output_prefix_argument, output_file_argument, required_arg, \
    MultipleArguments
from magic_monkey.config.utils import B0UtilsConfiguration
from magic_monkey.compute.utils import apply_mask_on_data, concatenate_dwi

_b0_aliases = {
    'in': 'B0Utils.image',
    'bvals': 'B0Utils.bvals',
    'bvecs': 'B0Utils.bvecs',
    'out': 'B0Utils.prefix'
}


class B0Utils(MagicMonkeyBaseApplication):
    configuration = Instance(B0UtilsConfiguration).tag(config=True)

    image = required_file(help="Input dwi image")
    bvals = required_file(help="Input b-values")
    bvecs = required_file(help="Input b-vectors")

    prefix = output_prefix_argument()

    aliases = Dict(_b0_aliases)

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
        bvecs = np.loadtxt(self.bvecs)

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
        np.savetxt("{}.bvecs".format(self.prefix), bvecs, fmt="%.6f")


_apply_mask_aliases = {
    'in': 'ApplyMask.image',
    'out': 'ApplyMask.output',
    'mask': 'ApplyMask.mask',
    'fill': 'ApplyMask.fill_value',
    'type': 'ApplyMask.dtype'
}


class ApplyMask(MagicMonkeyBaseApplication):
    image = required_file(help="Input image to mask")
    mask = required_file(help="Mask to apply on image ")

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
    images = required_arg(
        MultipleArguments, traits_args=(Unicode,),
        help="Input images to concatenate"
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
