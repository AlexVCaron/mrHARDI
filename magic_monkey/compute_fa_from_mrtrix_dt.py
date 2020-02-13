from numpy.linalg import eigh
from numpy import std, mean, sqrt, allclose


def compute_eigens(dt_coeffs):
    evals, evecs = eigh([
        [dt_coeffs[0], 0, 0],
        [dt_coeffs[3], dt_coeffs[1], 0],
        [dt_coeffs[4], dt_coeffs[5], dt_coeffs[2]]
    ])
    return evals[::-1], evecs[::-1, :]


def compute_fa(evals):
    if allclose(evals, 0):
        return 0
    else:
        var = std(evals) ** 2.
        mn = mean(evals)
        return sqrt(3. * var / (2 * (mn * mn + var)))
