from traitlets import Float, Integer, default
from traitlets.config import List, Enum, Bool
from traitlets.config.loader import ConfigError

from magic_monkey.base.application import MagicMonkeyConfigurable
from magic_monkey.traits.ants import InitialTransform, AntsPass


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
        "mass os two images. The images for this transformation "
        "must be the first ones in the list of images supplied "
        "(for both fixed and moving)"
    )
}


class AntsConfiguration(MagicMonkeyConfigurable):
    # TODO : Untested, need to check how config behaves
    passes = List(AntsPass, [], minlen=1, allow_none=True).tag(config=True)
    interpolation = Enum(
        ["Linear", "NearestNeighbor", "Gaussian",  "BSpline"], "Linear"
    ).tag(config=True)
    dimension = Integer(3).tag(config=True)
    inlier_range = List(Float, [5E-3, 0.995], 2, 2).tag(config=True)
    use_float = Bool(False).tag(config=True)
    match_histogram = Bool(True).tag(config=True)
    accross_modalities = Bool(True).tag(config=True)
    # TODO : How does this behaves when we want to config ?
    init_transform = InitialTransform(None, allow_none=True).tag(config=True)

    @default('app_flags')
    def _app_flags_default(self):
        return _flags

    def validate(self):
        if not 2 <= self.dimension <= 4:
            raise ConfigError(
                "Dimension of input images must be between 2 and 4"
            )

    def serialize(self):
        optionals, init_i = [], 0

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


# TODO : Check if interesting to add aliases and flags to cmdline
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

    def validate(self):
        pass

    def serialize(self):
        return "-e {} -d {} -n {} -f {}".format(
            self.input_type, self.dimension,
            self.interpolation, self.fill_value
        )
