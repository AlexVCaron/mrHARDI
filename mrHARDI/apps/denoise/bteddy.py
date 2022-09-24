from tempfile import TemporaryDirectory
import nibabel as nib
import numpy as np
from os.path import join
from traitlets import Instance, Unicode

from mrHARDI.base.application import (input_dwi_prefix,
                                      mrHARDIBaseApplication,
                                      output_prefix_argument,
                                      required_file)
from mrHARDI.config.bteddy import BTEddyConfiguration


class Eddy(mrHARDIBaseApplication):
    name = u"B-Tensor Adapted Eddy"
    configuration = Instance(BTEddyConfiguration).tag(config=True)

    image = input_dwi_prefix()
    bvals = required_file(help="b-value file")
    bvecs = required_file(help="b-vectors file")

    output = output_prefix_argument()

    temp_dir = Unicode(None, allow_none=True).tag(config=True)

    def execute(self):
        img = nib.load(self.image)
        bvals = np.loadtxt(self.bvals)
        bvecs = np.loadtxt(self.bvecs)
        low_b_mask = bvals <= self.configuration.low_b_threshold

        with self._get_temp_dir() as tmpd:
            nib.save(
                nib.Nifti1Image(
                    img.get_fdata()[..., low_b_mask],
                    img.affine,
                    img.header
                ),
                join(tmpd, "low_b.nii.gz")
            )
            np.savetxt(join(tmpd, "low_b.bval"), bvals[low_b_mask], newline=" ")
            np.savetxt(
                join(tmpd, "low_b.bvec"), bvecs[:, low_b_mask], fmt="%.8f"
            )
            nib.save(
                nib.Nifti1Image(
                    img.get_fdata()[..., ~low_b_mask],
                    img.affine,
                    img.header
                ),
                join(tmpd, "high_b.nii.gz")
            )

            low_b_reg, low_b_bvals, low_b_bvecs = self._register_low_b(
                join(tmpd, "low_b.nii.gz"),
                join(tmpd, "low_b.bval"),
                join(tmpd, "low_b.bvec"),
                tmpd
            )
            self._register_high_b(
                low_b_reg, low_b_bvals, low_b_bvecs, join(tmpd, "high_b.nii.gz")
            )

    def _register_low_b(self, dwi, bvals, bvecs, output_directory):
        bvals = np.loadtxt(bvals)
        min_b = np.argmin(bvals)
        img = nib.load(dwi)
        nib.save(
            nib.Nifti1Image(img.get_fdata()[..., min_b], img.affine),
            join(output_directory, "reference.nii.gz")
        )

        return self._coregister_images(
            dwi,
            join(output_directory, "reference.nii.gz"),
            bvals,
            bvecs,
            output_directory
        )

    def _register_high_b(self, low_dwi, low_bvals, low_bvecs, output_directory):
        ref = self._extrapolate_reference(
            low_dwi, low_bvals, low_bvecs
        )
        return self._coregister_images(
            self.image, ref, self.bvals, self.bvecs, output_directory
        )

    def _extrapolate_reference(self, dwi, bvals, bvecs):
        return dwi

    def _coregister_images(self, dwi, ref, bvals, bvecs, output_directory):
        return dwi

    def _get_temp_dir(self):
        if self.temp_dir:
            _tmp = self.temp_dir
            class _DummyTemp:
                def __enter__(self):
                    return _tmp
                def __exit__(self ,type, value, traceback):
                    pass

            return _DummyTemp()
        return TemporaryDirectory()
