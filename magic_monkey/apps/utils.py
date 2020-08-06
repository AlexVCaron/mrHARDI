import nibabel as nib
import numpy as np

from traitlets import Instance, Unicode, Integer, Enum, List, Dict

from magic_monkey.config.algorithms.b0 import extract_b0, squash_b0
from magic_monkey.base.application import MagicMonkeyBaseApplication
from magic_monkey.config.utils import B0UtilsConfiguration, apply_mask_on_data, \
    concatenate_dwi


class B0Utils(MagicMonkeyBaseApplication):
    configuration = Instance(B0UtilsConfiguration).tag(
        config=True, required=True
    )

    image = Unicode().tag(config=True, required=True)
    bvals = Unicode().tag(config=True, required=True)
    bvecs = Unicode().tag(config=True, required=True)

    prefix = Unicode().tag(config=True, required=True)

    aliases = Dict({
        'in': 'B0Utils.image',
        'bvals': 'B0Utils.bvals',
        'bvecs': 'B0Utils.bvecs',
        'out': 'B0Utils.prefix'
    })

    def _start(self):
        if self.configuration.current_util == "extract":
            self._extract_b0()
        if self.configuration.current_util == "squash":
            self._extract_b0()

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


class ApplyMask(MagicMonkeyBaseApplication):
    image = Unicode().tag(config=True, required=True)
    mask = Unicode().tag(config=True, required=True)
    fill_value = Integer(0).tag(config=True, required=True)
    dtype = Enum(
        [np.int, np.long, np.float], np.int
    ).tag(config=True, required=True)

    output = Unicode().tag(config=True, required=True)

    aliases = Dict({
        'in': 'ApplyMask.image',
        'out': 'ApplyMask.output',
        'mask': 'ApplyMask.mask',
        'fill': 'ApplyMask.fill_falue',
        'type': 'ApplyMask.dtype'
    })

    def _start(self):
        data = nib.load(self.image)
        mask = nib.load(self.mask).get_fdata().astype(bool)

        out_data = apply_mask_on_data(data.get_fdata(), mask, self.dtype)

        nib.save(nib.Nifti1Image(out_data, data.affine), self.output)


class Concatenate(MagicMonkeyBaseApplication):
    images = List(Unicode).tag(config=True, required=True)
    bvals = List(Unicode).tag(config=True)
    bvecs = List(Unicode).tag(config=True)

    prefix = Unicode().tag(config=True, required=True)

    aliases = Dict({
        'in': 'Concatenate.images',
        'out': 'Concatenate.prefix',
        'bvals': 'Concatenate.bvals',
        'bvecs': 'Concatenate.bvecs'
    })

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
