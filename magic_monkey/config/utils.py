import numpy as np
from traitlets import Enum, Integer

from magic_monkey.compute.b0 import B0PostProcess
from magic_monkey.base.application import convert_enum, MagicMonkeyConfigurable


# TODO : Check if interesting to add aliases and flags to cmdline
class B0UtilsConfiguration(MagicMonkeyConfigurable):
    def validate(self):
        pass

    def serialize(self):
        pass

    current_util = Enum(
        ["extract", "squash", None], None
    ).tag(config=True, required=True)
    mean_strategy = convert_enum(
        B0PostProcess, B0PostProcess.batch
    ).tag(config=True, required=True)
    dtype = Enum(
        [np.int, np.long, np.float], np.int
    ).tag(config=True, required=True)
    strides = Integer(None, allow_none=True).tag(config=True, required=True)
