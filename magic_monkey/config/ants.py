from traitlets import Float, Integer, default
from traitlets.config import Bool, Enum, List
from traitlets.config.loader import ConfigError

from magic_monkey.base.application import (DictInstantiatingInstance,
                                           MagicMonkeyConfigurable)
from magic_monkey.traits.ants import AntsPass, InitialTransform

_flags = {
    "no-HM": (
        {"AntsConfiguration": {"match_histogram": False}},
        "Disable histogram matching between input and output image"
    ),
    "one-modal": (
        {"AntsConfiguration": {"accross_modalities": False}},
        "Use if fixed and moving come from same modalities"
    ),
    "init-t": (
        {"AntsConfiguration": {"init_transform": InitialTransform(0, 0, 1)}},
        "Add basic initial transform aligning centers of "
        "mass of two images. The images for this transformation "
        "must be the first ones in the list of images supplied "
        "(for both fixed and moving)"
    )
}


class AntsConfiguration(MagicMonkeyConfigurable):
    passes = List(
        DictInstantiatingInstance(klass=AntsPass), [],
        minlen=1, allow_none=True,
        help="List of registration passes (Rigid, Affine or SyN)"
    ).tag(config=True)
    interpolation = Enum(
        ["Linear", "NearestNeighbor", "Gaussian",  "BSpline"], "Linear",
        help="Interpolation strategy. Choices : {}".format(
            ["Linear", "NearestNeighbor", "Gaussian",  "BSpline"]
        )
    ).tag(config=True)
    dimension = Integer(
        3, help="Number of dimensions of the input images"
    ).tag(config=True)
    inlier_range = List(
        Float, [5E-3, 0.995], 2, 2,
        help="Interval of values considered as part of the dataset"
    ).tag(config=True)
    use_float = Bool(
        False, help="Use single instead of double precision"
    ).tag(config=True)
    match_histogram = Bool(
        True, help="Match histogram between fixed and moving"
    ).tag(config=True)
    accross_modalities = Bool(
        True, help="Perform registration on different modalities "
                   "of imaging for fixed and moving images"
    ).tag(config=True)
    init_transform = InitialTransform(
        None, allow_none=True, help="Perform an initial fast registration "
                                    "between two images to align the dataset"
    ).tag(config=True)

    def _config_section(self):

        if self.init_transform is None:
            trait = self.traits()["init_transform"]
            trait.set(self, [0, 0, 1])
            trait.tag(bypass=True)

        return super()._config_section()

    @default('app_flags')
    def _app_flags_default(self):
        return _flags

    def _validate(self):
        if not 2 <= self.dimension <= 4:
            raise ConfigError(
                "Dimension of input images must be between 2 and 4"
            )

    def serialize(self):
        optionals, init_i = [''], 0

        if self.match_histogram:
            optionals.append("--use-histogram-matching {}".format(
                0 if self.accross_modalities else 1
            ))

        if self.init_transform:
            optionals.append(self.init_transform)

        for ants_pass in self.passes:
            optionals.append(ants_pass.serialize())

        return " ".join([
            "--dimensionality {} --float {}".format(
                self.dimension, 1 if self.use_float else 0
            ),
            "--interpolation {} --winsorize-image-intensities [{},{}]".format(
                self.interpolation, *self.inlier_range
            )
        ]) + " ".join(optionals)


_aliases = {
    "type": "AntsTransformConfiguration.input_type",
    "dim": "AntsTransformConfiguration.dimension",
    "interp": "AntsTransformConfiguration.interpolation",
    "fill": "AntsTransformConfiguration.fill_value"
}


class AntsTransformConfiguration(MagicMonkeyConfigurable):
    input_type = Integer(0).tag(config=True)
    dimension = Integer(3).tag(config=True)
    interpolation = Enum(
        ["Linear", "NearestNeighbor", "Gaussian", "BSpline"], "Linear"
    ).tag(config=True)
    fill_value = Integer(0).tag(config=True)

    @default('app_aliases')
    def _app_aliases_default(self):
        return _aliases

    def _validate(self):
        pass

    def serialize(self):
        return "-e {} -d {} -n {} -f {}".format(
            self.input_type, self.dimension,
            self.interpolation, self.fill_value
        )
