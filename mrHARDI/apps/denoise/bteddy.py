from os import makedirs
from tempfile import TemporaryDirectory
import nibabel as nib
import numpy as np
from os.path import join
from scipy.ndimage import gaussian_filter
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

            low_b_reg, low_b_bvecs = self._register_low_b(
                join(tmpd, "low_b.nii.gz"),
                join(tmpd, "low_b.bval"),
                join(tmpd, "low_b.bvec"),
                tmpd
            )
            dwi, bvecs = self._register_high_b(
                low_b_reg, join(tmpd, "low_b.bval"), low_b_bvecs, tmpd
            )

            np.savetxt(
                "{}.bval".format(self.output), bvals, newline=" ", fmt="%d"
            )
            np.savetxt("{}.bvec".format(self.output), bvecs, fmt="%.8f")

            nib.save(
                nib.Nifti1Image(dwi, img.affine, img.header),
                "{}.nii.gz".format(self.output)
            )

    def _register_low_b(self, dwi, bvals, bvecs, output_directory):
        bvals = np.loadtxt(bvals)
        min_b = np.argmin(bvals)
        img = nib.load(dwi)
        nib.save(
            nib.Nifti1Image(img.get_fdata()[..., min_b], img.affine),
            join(output_directory, "reference.nii.gz")
        )

        dwi, bvecs, _ =  self._coregister_images(
            dwi,
            join(output_directory, "reference.nii.gz"),
            bvecs,
            output_directory
        )

        return dwi, bvecs

    def _register_high_b(self, low_dwi, low_bvals, low_bvecs, output_directory):
        ref = self._extrapolate_reference(
            low_dwi, low_bvals, low_bvecs
        )
        dwi, bvecs, _ = self._coregister_images(
            self.image, ref, self.bvecs, output_directory
        )

        return dwi, bvecs

    def _extrapolate_reference(self, dwi, bvals, bvecs, output_directory):
        source = nib.load(dwi)
        target = nib.load(self.image)
        smooth = np.empty(source.shape)

        workdir = join(output_directory, ".extrapol_workdir")
        makedirs(workdir)

        for c in range(source.shape[-1]):
            smooth[..., c] = gaussian_filter(
                source.get_fdata()[..., c],
                self.configuration.smoothing_sigma
            )

        smooth_img = nib.Nifti1Image(smooth, source.affine, source.header)

        reference = extrapolate_reference(
            smooth_img, source, target
        )



    def _coregister_images(self, dwi, ref, bvecs=None, output_directory="."):
        moving, target = nib.load(dwi), nib.load(ref)
        n_moving = moving.shape[-1]
        n_target = target.shape[-1] if len(target.shape) == 4 else 1
        out = np.empty(target.shape[:3] + (n_moving,))
        params = np.empty((12, n_moving))

        workdir = join(output_directory, ".coreg_workdir")
        makedirs(workdir)

        if n_target == 1:
            get_target = lambda _: ref
        else:
            def _get_target(c):
                nib.save(
                    nib.Nifti1Image(
                        target.get_fdata()[..., min(c, n_target - 1)],
                        target.affine,
                        target.header
                    ),
                    join(workdir, "temp_target.nii.gz")
                )
                return join(workdir, "temp_target.nii.gz")
            get_target = _get_target

        for i in range(n_moving):
            res, p = self._run_registration_command(
                get_target(i), join(workdir, "temp_moving.nii.gz")
            )
            out[..., i] = res
            params[:, i] = p

        if bvecs is not None:
            bvecs = self._correct_bvecs(bvecs, params)

        return out, bvecs, params

    def _correct_bvecs(self, bvecs, params):
        return bvecs

    def _run_registration_command(self, target, moving):
        return target, moving

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
