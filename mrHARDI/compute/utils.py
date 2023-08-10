import numpy as np
from numpy import (concatenate,
                   ones_like,
                   ceil,
                   floor,
                   array,
                   dtype as datatype,
                   r_ as row)
from scipy.io import loadmat
from scipy.spatial.transform import Rotation

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


def resampling_affine(ref_affine, ref_shape, ref_zooms, new_zooms):
    zoom_matrix = np.eye(4)
    zoom_matrix[:3, :3] = np.diag(1. / ref_zooms)
    affine = np.dot(ref_affine, zoom_matrix)

    for j in range(3):
        extent = ref_shape[j] * ref_zooms[j]
        axis = np.round(extent / new_zooms[j] - 1E-4)
        mod = 0.5 * (
            (1. - axis) * new_zooms[j] - ref_zooms[j] + extent
        )

        for i in range(3):
            affine[i, 3] += mod * affine[i, j]

    zoom_matrix = np.eye(4)
    zoom_matrix[:3, :3] = np.diag(new_zooms)
    return np.dot(affine, zoom_matrix)


def load_transform(filename):
    mat = loadmat(filename)

    def _affine(_type, t_sign=-1.):
        _m = np.vstack((mat[_type].reshape((4, 3)).T, [0, 0, 0, 1])).T
        _m[[0, 1, 2, -1, -1, -1], [-1, -1, -1, 0, 1, 2]] = \
            _m[[-1, -1, -1, 0, 1, 2], [0, 1, 2, -1, -1, -1]]
        offset = mat['fixed'].flatten()[:3]
        _m[:3, -1] += offset - np.dot(_m[:3, :3], offset)
        _m[:3, -1] *= t_sign
        return _m

    def _euler(_type, t_sign=-1.):
        _r = Rotation.from_euler('zyx', mat[_type][:3].flatten()).as_matrix()
        _m = np.vstack((np.vstack((_r.T, mat[_type][3:])).T, [0, 0, 0, 1]))
        offset = mat['fixed']
        _m[:3, -1] += offset - np.dot(_m[:3, :3], offset)
        _m[:3, -1] *= t_sign
        return _m

    if "AffineTransform_double_3_3" in mat:
        return _affine("AffineTransform_double_3_3")
    elif "AffineTransform_float_3_3" in mat:
        return _affine("AffineTransform_float_3_3")
    elif "MatrixOffsetTransformBase_double_3_3" in mat:
        return _affine("MatrixOffsetTransformBase_double_3_3", 1.)
    elif "MatrixOffsetTransformBase_float_3_3" in mat:
        return _affine("MatrixOffsetTransformBase_float_3_3", 1.)
    elif "Euler3DTransform_double_3_3" in mat:
        return _euler("Euler3DTransform_double_3_3")
    elif "Euler3DTransform_float_3_3" in mat:
        return _euler("Euler3DTransform_float_3_3")
    else:
        print("Could not load rotation matrix from : {}".format(filename))
        return np.eye(4)
