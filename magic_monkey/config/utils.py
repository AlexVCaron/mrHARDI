import numpy as np
from numpy import ones_like, concatenate
from traitlets import Enum, Integer

from magic_monkey.config.algorithms.b0 import B0PostProcess
from magic_monkey.base.application import convert_enum, MagicMonkeyConfigurable


def serialize_fsl(args_dict, separator="\n", bool_as_flags=False):
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


class B0UtilsConfiguration(MagicMonkeyConfigurable):
    def validate(self):
        pass

    def serialize(self):
        pass

    current_util = Enum(
        ["extract", "squash"], None
    ).tag(config=True, required=True)
    mean_strategy = convert_enum(
        B0PostProcess, B0PostProcess.batch
    ).tag(config=True, required=True)
    dtype = Enum(
        [np.int, np.long, np.float], np.int
    ).tag(config=True, required=True)
    strides = Integer(None, allow_none=True).tag(config=True, required=True)


def apply_mask_on_data(in_data, in_mask, fill_value=0., dtype=float):
    out_data = (ones_like(in_data, dtype=dtype) * fill_value).as_type(dtype)
    out_data[in_mask] = in_data[in_mask]
    return out_data


def concatenate_dwi(dwi_list, bvals_in, bvecs_in):
    return concatenate(dwi_list, axis=-1), \
           concatenate(bvals_in)[None, :] if bvals_in else None, \
           concatenate(bvecs_in, axis=1).T if bvecs_in else None
