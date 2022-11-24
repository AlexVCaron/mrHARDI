import numpy as np
from numpy import (concatenate,
                   ones_like,
                   ceil,
                   floor,
                   array,
                   dtype as datatype,
                   r_ as row)


def apply_mask_on_data(
    in_data, in_mask, fill_value=0., dtype=float, in_place=True
):
    if isinstance(dtype, datatype):
        fill_value = array([fill_value], dtype=dtype)[0]
    else:
        fill_value = dtype(fill_value)

    if in_place:
        in_data[~in_mask] = fill_value
        return in_data

    out_data = (ones_like(in_data, dtype=float) * fill_value).astype(dtype)
    out_data[in_mask] = in_data[in_mask]
    return out_data


def concatenate_dwi(dwi_list, bvals_in=None, bvecs_in=None, dwi_axis=-1):
    return concatenate(dwi_list, axis=dwi_axis), \
           concatenate(bvals_in)[None, :] if bvals_in else None, \
           concatenate(bvecs_in, axis=1).T if bvecs_in else None


def value_first(indexes, s, j):
    for i in range(s.stop - s.start):
        indexes += [j]
    j += 1

    return indexes, j


def value_closest(indexes, s, j):
    for i in range(int(floor(0.5 * (s.stop - s.start)))):
        indexes += [j]
    j += 1
    for i in range(int(ceil(0.5 * (s.stop - s.start)))):
        indexes += [j]

    return indexes, j


def voxel_to_world(coord, affine):
    """Takes a n dimensionnal voxel coordinate and returns its 3 first
    coordinates transformed to world space from a given voxel to world affine
    transformation."""
    normalized_coord = row[coord[0:3], 1.0].astype(float)
    world_coord = np.dot(affine, normalized_coord)
    return world_coord[0:3]


def world_to_voxel(coord, affine):
    """Takes a n dimensionnal world coordinate and returns its 3 first
    coordinates transformed to voxel space from a given voxel to world affine
    transformation."""

    normalized_coord = row[coord[0:3], 1.0].astype(float)
    iaffine = np.linalg.inv(affine)
    vox_coord = np.dot(iaffine, normalized_coord)
    vox_coord = np.round(vox_coord).astype(int)
    return vox_coord[0:3]


def validate_affine(aff_a, aff_b, shape):
    # Code from dicm2nii
    def _reorient_to_ras(_r):
        _a = np.abs(_r[:-1, :-1])
        _ix = np.argmax(_a, axis=1)
        if _ix[1] == _ix[0]:
            _a[_ix[1], 1] = 0
            _ix[1] = np.argmax(_a[:, 1])
        if np.any(_ix[:2] == _ix[2]):
            _ix[3] = np.setdiff1d(np.arange(0, 3, dtype=int), _ix[:3])
        _perm = np.argsort(_ix)
        _r[:, :3] = _r[:, _perm]
        _flp = np.diag(_r[:3, :3]) < 0
        _flp[0] = ~_flp[0]
        _rm = np.diag(np.concatenate((1. - _flp * 2., [1.])))
        _rm[:3, -1] = (np.array(shape)[:3][_perm] - 1) * _flp
        _r = _r @ np.linalg.inv(_rm)

        return _r, _perm, _flp

    _a, _, _ = _reorient_to_ras(aff_a)
    _b, _, _ = _reorient_to_ras(aff_b)

    if np.allclose(_a, _b):
        return True, aff_a

    return False, None
