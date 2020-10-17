import numpy as np

from magic_monkey.compute.math.spherical import voronoi_sn


def get_bshells_voronoi(
    bvals, bvecs, regroup=True, bval_thr=40, precision=1E-2
):
    if regroup:
        ubv = np.unique(bvals)

        ubv_masks = np.apply_along_axis(
            lambda bv: np.logical_and(
                bvals > (bv[0] - bval_thr),
                bvals < (bv[0] + bval_thr)
            ),
            0, ubv[None, :]
        ).T

        for idx in np.argsort(np.count_nonzero(ubv_masks, 1))[::-1]:
            bvals[ubv_masks[idx]] = ubv[idx]

    return bvals, voronoi_sn(bvals[:, None] * bvecs, precision)
