import numpy as np
from traitlets import Enum, Integer, default

from magic_monkey.base.application import (MagicMonkeyConfigurable,
                                           convert_enum,
                                           ChoiceList)

from magic_monkey.base.dwi import AcquisitionDirection, AcquisitionType
from magic_monkey.compute.b0 import B0PostProcess

_b0_aliases = dict(
    mean="B0UtilsConfiguration.mean_strategy",
    type="B0UtilsConfiguration.dtype",
    strides="B0UtilsConfiguration.strides"
)


class B0UtilsConfiguration(MagicMonkeyConfigurable):
    def _validate(self):
        pass

    def serialize(self):
        pass

    @default("app_aliases")
    def _app_aliases_default(self):
        return _b0_aliases

    current_util = Enum(
        ["extract", "squash", None], None
    ).tag(config=True, required=True)

    mean_strategy = convert_enum(
        B0PostProcess, B0PostProcess.batch, allow_none=True
    ).tag(config=True)
    dtype = Enum(
        [
            np.dtype(t).name
            for t in [np.int16, np.int32, np.float32, np.float64]
        ],
        np.dtype(np.int32).name
    ).tag(config=True)
    strides = Integer(None, allow_none=True).tag(config=True)
