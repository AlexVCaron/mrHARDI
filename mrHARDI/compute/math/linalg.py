from numpy import (allclose,
                   append,
                   apply_along_axis,
                   isclose,
                   mean,
                   moveaxis,
                   sqrt,
                   std,
                   vstack,
                   zeros, ones, absolute)


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


def homo_mat(_m, _d=4):
    return vstack((vstack((_m, [0, 0, 0])).T, [0, 0, 0, 1])).T \
        if len(_m) < _d else _m

def homo_vec(_v, _d=4):
    return append(_v, [1.]) if len(_v) < _d else _v


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


def color(metric, evecs, mask=None):
    if mask is None:
        mask = ones(metric.shape[:3]).astype(bool)
    cmetric = zeros(metric.shape[:3] + (3,))
    cmetric[mask] = absolute(metric[mask, None] * evecs[mask, 0, :])
    return cmetric
