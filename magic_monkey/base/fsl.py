from numpy import isclose
from numpy.ma import clump_masked, clump_unmasked, masked_array

from magic_monkey.compute.utils import value_closest, value_first


def serialize_fsl_args(args_dict, separator="\n", bool_as_flags=False):
    base_string = ""
    if bool_as_flags:
        base_string = separator.join([
            "--{}".format(args_dict.pop(key)) for key, val in filter(
                lambda kv: isinstance(kv[1], bool) and kv[1], args_dict
            )
        ])
        base_string += separator

    return base_string + separator.join(
        "--{}={}".format(name, ",".join(str(v) for v in val).strip(","))
        for name, val in args_dict.items()
    )


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


def prepare_acqp_file(ap_b0_shapes, pa_b0_shapes, dwell):
    param_string = ""
    for ap_b0, pa_b0 in zip(ap_b0_shapes, pa_b0_shapes):
        for _ in range(ap_b0[-1]):
            param_string += "0.0 1.0 0.0 {:.8f}\n".format(dwell)
        for _ in range(pa_b0[-1]):
            param_string += "0.0 -1.0 0.0 {:.8f}\n".format(dwell)

    return param_string
