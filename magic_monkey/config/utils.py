import numpy as np
from traitlets import Enum, Integer, default, Float, Bool, Unicode

from magic_monkey.base.application import (MagicMonkeyConfigurable,
                                           convert_enum,
                                           ChoiceList)

from magic_monkey.base.dwi import Direction, AcquisitionType
from magic_monkey.compute.b0 import B0PostProcess

_b0_aliases = dict(
    mean="B0UtilsConfiguration.mean_strategy",
    type="B0UtilsConfiguration.dtype",
    strides="B0UtilsConfiguration.strides",
    ceil="B0UtilsConfiguration.ceil_value"
)

_b0_flags = dict(
    strict=(
        {'B0UtilsConfiguration': {'strict': True}},
        "Test b0 b-values using \"less\" comparator "
        "instead of \"less or equal\""
    ),
)


class B0UtilsConfiguration(MagicMonkeyConfigurable):
    def _validate(self):
        pass

    def serialize(self, *args, **kwargs):
        pass

    @default("app_aliases")
    def _app_aliases_default(self):
        return _b0_aliases

    @default("app_flags")
    def _app_flags_default(self):
        return _b0_flags

    current_util = Enum(
        ["extract", "squash", None], None
    ).tag(config=True, required=True)

    mean_strategy = convert_enum(
        B0PostProcess, B0PostProcess.batch, allow_none=True
    ).tag(config=True)

    ceil_value = Float(
        0.9, help="Higher bound determining a valid b-value for a b0 volume"
    ).tag(config=True)

    strict = Bool(
        False, help="If True, test b0 b-values with "
                    "\"<\" comparator instead of \"<=\""
    ).tag(config=True)

    dtype = Enum(
        [
            np.dtype(t).name
            for t in [np.int16, np.int32, np.float32, np.float64]
        ], allow_none=True
    ).tag(config=True)

    strides = Integer(None, allow_none=True).tag(config=True)

    def get_mean_strategy_enum(self):
        return B0PostProcess[self.mean_strategy]


_meta_aliases = dict(
    dir="DwiMetadataUtilsConfiguration.direction",
    mb="DwiMetadataUtilsConfiguration.multiband_factor",
    sd="DwiMetadataUtilsConfiguration.slice_direction",
    gsl="DwiMetadataUtilsConfiguration.gslider_factor",
    acq="DwiMetadataUtilsConfiguration.acquisition",
    dwell="DwiMetadataUtilsConfiguration.dwell"
)

_meta_flags = dict(
    interleaved=(
        {"DwiMetadataUtilsConfiguration": {'interleaved': True}},
        "Set dataset acquisition as interleaved order (0, 2, 4, 1, 3 ...)"
    ),
    mbc=(
        {"DwiMetadataUtilsConfiguration": {'multiband_corrected': True}},
        "Set dataset as already corrected for multiband artifacts"
    ),
    tv=(
        {"DwiMetadataUtilsConfiguration": {'tensor_valued': True}},
        "Set dataset as tensor-valued acquisition"
    )
)


class DwiMetadataUtilsConfiguration(MagicMonkeyConfigurable):
    @default("app_aliases")
    def _app_aliases_default(self):
        return _meta_aliases

    @default("app_flags")
    def _app_flags_default(self):
        return _meta_flags

    direction = ChoiceList(
        [d.name for d in Direction], Unicode(),
        help="List of phase encoding directions of the input datasets. "
             "There can be N directions, with N either :\n"
             "   - 1 : the same direction will apply to all datasets\n"
             "   - N : one direction per dataset, applied to all slices"
    ).tag(config=True, required=True)

    slice_direction = ChoiceList(
        [d.name for d in Direction], Unicode(),
        help="List of acquisition directions of the input datasets. There can "
             "be N directions, with N either :\n"
             "   - 1 : the same direction will apply to all datasets\n"
             "   - N : one direction per dataset, applied to all slices"
    ).tag(config=True)

    dwell = Float(help="Acquisition readout time (in ms)").tag(
        config=True, required=True
    )

    multiband_factor = Integer(None, allow_none=True).tag(config=True)

    gslider_factor = Integer(None, allow_none=True).tag(config=True)

    interleaved = Bool(
        None, allow_none=True,
        help="If True, will output interleaved "
             "slices in the multiband index definition"
    ).tag(config=True)
    multiband_corrected = Bool(
        False, allow_none=True,
        help="Specifies if the dataset has been corrected "
             "for iter-slice and slice-to-vol motion"
    ).tag(config=True)

    tensor_valued = Bool(
        None, allow_none=True, help="Dataset acquisition is tensor-valued"
    ).tag(config=True)

    acquisition = convert_enum(
        AcquisitionType, None, allow_none=True
    ).tag(config=True)

    def _validate(self):
        pass

    def serialize(self, *args, **kwargs):
        pass
