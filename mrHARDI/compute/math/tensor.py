from functools import partial

from numpy import (apply_along_axis,
                   diag,
                   eye,
                   flip,
                   isclose,
                   trace,
                   zeros,
                   moveaxis)

from numpy.linalg import eigh


def vec_to_tens(dt, convention=(0, 1, 2, 3, 4, 5)):
    i1, i2, i3, i4, i5, i6 = convention
    return [
        [dt[i1], dt[i2], dt[i4]],
        [dt[i2], dt[i3], dt[i5]],
        [dt[i4], dt[i5], dt[i6]]
    ]


def compute_eigenvalues(
    tensors, mask, convention=(0, 1, 2, 3, 4, 5), reorder=True
):
    vtt = partial(vec_to_tens, convention=convention)
    evals, evecs = zeros(mask.shape + (3,)), zeros(mask.shape + (3, 3))
    evals[mask], evecs[mask] = eigh(
        apply_along_axis(vtt, 1, tensors[mask])
    )

    neg_evals = evals < 0
    evals[neg_evals] = 0.

    if reorder:
        evals, evecs = flip(evals, -1), moveaxis(flip(evecs, -1), -2, -1)

    return evals, evecs


def compute_haeberlen(tensors, mask):
    diso, daniso = zeros(mask.shape), zeros(mask.shape)
    ddelta, deta = zeros(mask.shape), zeros(mask.shape)

    tensors = apply_along_axis(
        vec_to_tens, 1, tensors.reshape((-1, 6))
    ).reshape(mask.shape + (3, 3))

    diso[mask] = trace(tensors[mask], axis1=-2, axis2=-1) / 3.
    daniso[mask] = trace(
        (tensors - diso[..., None, None])[mask] @ diag([-1., -1., 0.5]),
        axis1=-2, axis2=-1
    ) / 3.

    mask &= ~isclose(diso, 0.)

    ddelta[mask] = daniso[mask] / diso[mask]

    mask &= ~isclose(ddelta, 0.)

    deta[mask] = trace(
        (
            (
                tensors[mask] / diso[mask, None, None] - eye(3)
            ) / ddelta[mask, None, None] - diag([-1, -1, 2])
        )[..., :-1, :-1] @ diag([-1, 1]),
        axis1=-2, axis2=-1
    ) / 2.

    return diso, daniso, ddelta, deta
