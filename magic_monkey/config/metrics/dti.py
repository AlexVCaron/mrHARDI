from abc import ABCMeta

import nibabel as nib

from numpy import float32

from magic_monkey.base.application import BaseMetric
from magic_monkey.compute.math.linalg import compute_fa, compute_md, \
    compute_ad, compute_rd, compute_peaks
from magic_monkey.compute.math.tensor import compute_eigenvalues


class DTIMetric(BaseMetric, metaclass=ABCMeta):
    def _get_eigs(self):
        return self.load_from_cache(
            "eigs", lambda _: compute_eigenvalues(
                nib.load(
                    "{}_dti.nii.gz".format(self.prefix)
                ).get_fdata().squeeze(),
                self.get_mask()
            )
        )

    def _get_peaks(self):
        return self.load_from_cache(
            "peaks", lambda _: compute_peaks(self._get_eigs(), self.get_mask())
        )


class FaMetric(DTIMetric):
    def measure(self):
        fa = self.load_from_cache(
            "fa", lambda _: compute_fa(self._get_eigs(), self.get_mask())
        )

        nib.save(
            nib.Nifti1Image(fa, self.affine),
            "{}_fa.nii.gz".format(self.output)
        )

        _, evecs = self._get_eigs()

        self._color("fa", evecs)


class MdMetric(DTIMetric):
    def measure(self):
        md = self.load_from_cache(
            "md", lambda _: compute_md(self._get_eigs(), self.get_mask())
        )

        nib.save(
            nib.Nifti1Image(md, self.affine),
            "{}_md.nii.gz".format(self.output)
        )


class AdMetric(DTIMetric):
    def measure(self):
        ad = self.load_from_cache(
            "ad", lambda _: compute_ad(self._get_eigs(), self.get_mask())
        )

        nib.save(
            nib.Nifti1Image(ad, self.affine),
            "{}_ad.nii.gz".format(self.output)
        )


class RdMetric(DTIMetric):
    def measure(self):
        rd = self.load_from_cache(
            "rd", lambda _: compute_rd(self._get_eigs(), self.get_mask())
        )

        nib.save(
            nib.Nifti1Image(rd, self.affine),
            "{}_rd.nii.gz".format(self.output)
        )


class PeaksMetric(DTIMetric):
    def measure(self):
        peaks = self._get_peaks()

        nib.save(
            nib.Nifti1Image(peaks.astype(float32), self.affine),
            "{}_peaks.nii.gz".format(self.output)
        )
