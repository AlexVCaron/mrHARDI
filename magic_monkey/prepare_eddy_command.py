from numpy.ma import clump_masked, clump_unmasked, masked_array
from numpy import isclose, floor, ceil


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


def prepare_eddy_index(bvals, dir0=1, strategy="closest"):
    strat = value_closest if strategy == "closest" else value_first
    indexes = []
    mask = masked_array(bvals, isclose(bvals, 0))
    b0_clumps = list(clump_masked(mask))
    dw_clumps = list(clump_unmasked(mask))
    j = dir0
    for s1, s2 in zip(b0_clumps[:len(dw_clumps)], dw_clumps):
        for i in range(s1.stop - s1.start):
            indexes += [j]
        indexes, j = strat(indexes, s2, j)

    if len(b0_clumps) > len(dw_clumps):
        for i in range(b0_clumps[-1].stop - b0_clumps[-1].start):
            indexes += [j]

    return indexes
