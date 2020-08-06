from abc import ABCMeta

import nibabel as nib

from numpy import apply_along_axis, zeros, allclose, std, mean, sqrt, isclose, \
    moveaxis, float32, flip
from numpy.linalg import eigh

from magic_monkey.base.application import BaseMetric


def vec_to_tens(dt):
    return [
        [dt[0], dt[1], dt[3]],
        [dt[1], dt[2], dt[4]],
        [dt[3], dt[4], dt[5]]
    ]


def _fa(evals, axis=0):
    fa_mask = apply_along_axis(lambda e: not allclose(e, 0), axis, evals)
    fa = zeros(evals.shape[:-1])

    var = std(evals[fa_mask], axis) ** 2.
    mn2 = mean(evals[fa_mask], axis) ** 2.

    mask2 = ~isclose(var, 0.)
    fa_mask[fa_mask] &= mask2

    denom = 1. + mn2[mask2] / var[mask2]

    mask3 = ~isclose(denom, 0.)
    fa_mask[fa_mask] &= mask3

    fa[fa_mask] = sqrt(3. / (2. * denom[mask3]))

    return fa


def compute_eigenvalues(dti, mask):
    evals, evecs = zeros(mask.shape + (3,)), zeros(mask.shape + (3, 3))
    evals[mask], evecs[mask] = eigh(
        apply_along_axis(vec_to_tens, 1, dti[mask])
    )
    return flip(evals, -1), flip(evecs, -1).swapaxes(-1, -2)


def compute_fa(eigs, mask):
    evals, _ = eigs

    fa_map = zeros(mask.shape)
    fa_map[mask] = _fa(evals[mask], 1)

    return fa_map


def compute_md(eigs, mask):
    evals, _ = eigs

    md_map = zeros(mask.shape)
    md_map[mask] = mean(evals[mask], 1)

    return md_map


def compute_ad(eigs, mask):
    evals, _ = eigs

    ad_map = zeros(mask.shape)
    ad_map[mask] = evals[mask][..., 0]

    return ad_map


def compute_rd(eigs, mask):
    evals, _ = eigs

    rd_map = zeros(mask.shape)
    rd_map[mask] = mean(evals[mask][..., 1:], axis=1)

    return rd_map


def compute_peaks(eigs, mask):
    _, evecs = eigs

    peaks = zeros((5,) + mask.shape + (3,))
    peaks[0, mask] = evecs[mask, 0, :]

    return moveaxis(peaks, 0, -2).reshape(mask.shape + (15,))


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
