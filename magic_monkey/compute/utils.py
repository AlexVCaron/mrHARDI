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


def concatenate_dwi(dwi_list, bvals_in=None, bvecs_in=None):
    return concatenate(dwi_list, axis=-1), \
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


def validate_affine(aff_a, aff_b, shape_b):
    def _get_strides(_aff):
        _val, _vec = np.linalg.eigh(_aff)
        _sort = list(
            np.where([np.allclose(_a, _r) for _r in _aff])[0][0]
            for _a in _vec @ np.diag(_val) @ np.linalg.inv(_vec)
        )
        return _val[_sort]

    same_origin = np.allclose(aff_a[:3, -1], aff_b[:3, -1])
    same_trans = np.allclose(aff_a[:3, :3], aff_b[:3, :3])
    if same_origin:
        if same_trans:
            return True, aff_a
        return False, None

    b_in_a = [b if df else nb for b, df, nb in zip(
        aff_b[:3, -1],
        np.equal(
            np.sign(_get_strides(aff_a[:3, :3])),
            np.sign(_get_strides(aff_b[:3, :3]))
        ),
        voxel_to_world(np.array(shape_b) - 1., aff_b)
    )]

    return np.allclose(b_in_a, aff_a[:3, -1]), aff_a
