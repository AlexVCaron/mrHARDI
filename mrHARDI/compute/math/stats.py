
import numpy as np
from scipy.ndimage import center_of_mass

from mrHARDI.compute.math.linalg import homo_vec


def center_of_mass_difference(_arr1, _arr2, _aff2to1=np.eye(4)):
    _cm1 = center_of_mass(_arr1)
    _cm2in1 = (_aff2to1 @ homo_vec(center_of_mass(_arr2)))[:3]

    return (_cm1 - _cm2in1)
