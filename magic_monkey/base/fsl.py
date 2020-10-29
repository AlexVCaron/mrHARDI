from typing import Generator

from numpy import less_equal, repeat, array, absolute, concatenate, clip
from numpy.ma import clump_masked, clump_unmasked, masked_array

from magic_monkey.compute.utils import value_closest, value_first


def serialize_fsl_args(args_dict, separator="\n", bool_as_flags=False):
    base_string = ""
    if bool_as_flags:
        base_string = separator.join([
            "--{}".format(key) for key, val in filter(
                lambda kv: isinstance(kv[1], bool) and kv[1],
                args_dict.items()
            )
        ])
        if base_string:
            base_string += separator

        args_dict = dict(
            filter(lambda kv: not isinstance(kv[1], bool), args_dict.items())
        )

    def serialize_value(val):
        if isinstance(val, (list, tuple, Generator)):
            return ",".join(str(v) for v in val).strip(",")
        return str(val)

    return base_string + separator.join(
        "--{}={}".format(name, serialize_value(val))
        for name, val in args_dict.items()
    )


def prepare_topup_index(
    bvals, dir0=1, strategy="closest", ceil=0.9, b0_comp=less_equal
):
    strat = value_closest if strategy == "closest" else value_first
    indexes = []
    mask = masked_array(bvals, b0_comp(bvals, ceil))
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

    return clip(indexes, a_min=1, a_max=len(b0_clumps))


def prepare_acqp_file(ap_b0_shapes, pa_b0_shapes, dwell, direction):
    if len(direction) == 1:
        dirs = repeat(direction, len(ap_b0_shapes), 0)
        d1 = concatenate(
            (repeat(dirs, s, 0) for s in ap_b0_shapes),
            axis=0
        )
        d2 = concatenate(
            (repeat(-dirs, s, 0) for s in pa_b0_shapes),
            axis=0
        )
        dirs = concatenate((d1, d2), axis=0)
    elif len(direction) == len(ap_b0_shapes):
        assert len(ap_b0_shapes) == len(pa_b0_shapes), \
            "This way of passing the directions is limited " \
            "to cases of equal sets of ap and pa shapes"

        dirs = concatenate((direction, -array(direction)), axis=0)
    elif len(direction) == len(ap_b0_shapes) + len(pa_b0_shapes):
        if len(array(direction).shape) == 2:
            dirs = array(direction)
        else:
            dirs = concatenate(direction, axis=0)
    else:
        dirs = array(direction)

    print("Here are the dirs !!!!! {}".format(dirs))
    dirs[less_equal(absolute(dirs), 1e-8)] = 0.

    return "\n".join("{} {:.8f}".format(
        " ".join(str(dd) for dd in d), dwell
    ) for d in dirs)
