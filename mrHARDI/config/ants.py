from enum import Enum as PyEnum
from traitlets import Float, Integer, default
from traitlets.config import Bool, Enum, List
from traitlets.config.loader import ConfigError

from mrHARDI.base.application import (DictInstantiatingInstance,
                                           mrHARDIConfigurable,
                                           convert_enum)
from mrHARDI.traits.ants import AntsPass, InitialTransform

_a_aliases = {
    "seed": "AntsConfiguration.seed",
    "ca-split": "AntsConfiguration.coarse_angular_split",
    "cl-split": "AntsConfiguration.coarse_linear_split",
    "fa-split": "AntsConfiguration.fine_angular_split",
    "fl-split": "AntsConfiguration.fine_linear_split"
}

_a_flags = {
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


class AntsConfiguration(mrHARDIConfigurable):
    passes = List(
        DictInstantiatingInstance(
            klass=AntsPass, add_init=dict(name_dict={
                "smooth": "smoothing-sigmas",
                "shrink": "shrink-factors"
            })), [], allow_none=True,
        help="List of registration passes (Rigid, Affine or SyN)"
    ).tag(config=True)
    interpolation = Enum(
        ["Linear", "NearestNeighbor", "Gaussian",  "BSpline", "MultiLabel"],
        "Linear",
        help="Interpolation strategy. Choices : {}".format(
            ["Linear", "NearestNeighbor", "Gaussian",  "BSpline", "MultiLabel"]
        )
    ).tag(config=True)
    dimension = Integer(
        3, help="Number of dimensions of the input images"
    ).tag(config=True)
    inlier_range = List(
        Float(), [5E-3, 0.995], 2, 2,
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
    init_moving_transform = List(
        InitialTransform(),
        help="Perform an initial fast registration from moving "
             "to fixed between two images to align the dataset"
    ).tag(config=True)
    init_fixed_transform = List(
        InitialTransform(),
        help="Perform an initial fast registration from fixed "
             "to moving between two images to align the dataset"
    ).tag(config=True)
    register_last_dimension = Bool(True).tag(config=True)
    seed = Integer(None, allow_none=True).tag(config=True)

    coarse_angular_split = Integer(4).tag(config=True)
    fine_angular_split = Integer(9).tag(config=True)
    coarse_linear_split = Integer(3).tag(config=True)
    fine_linear_split = Integer(0).tag(config=True)

    def _config_section(self):
        return super()._config_section()

    @default('app_flags')
    def _app_flags_default(self):
        return _a_flags

    @default('app_aliases')
    def _app_aliases_default(self):
        return _a_aliases

    def _validate(self):
        if not 2 <= self.dimension <= 4:
            raise ConfigError(
                "Dimension of input images must be between 2 and 4"
            )

    def set_initial_transform_from_ants_ai(self, transform_mat):
        self.init_moving_transform = transform_mat

    def is_initializable(self):
        return any(p.name in ["Rigid", "Affine"] for p in self.passes)

    def get_ants_ai_parameters(self, voxel_size):
        options = ["-d {}".format(self.dimension)]
        transform = []
        for ants_pass in self.passes:
            if (
                ants_pass.name in ["Rigid", "Affine"] and
                len(transform) == 0
            ):
                transform.append(
                    ants_pass.serialize(voxel_size, for_ants_ai=True)
                )

        return " ".join(options + transform)

    def serialize(self, voxel_size, *args, masks=None, **kwargs):
        optionals, init_i = [''], 0

        if self.match_histogram:
            optionals.append("--use-histogram-matching {}".format(
                0 if self.accross_modalities else 1
            ))

        if masks:
            optionals.append(masks)

        if self.init_moving_transform and len(self.init_moving_transform) > 0:
            for transform in self.init_moving_transform:
                optionals.append(transform)
                if not self.register_last_dimension:
                    optionals.append("--restrict-deformation {}x0".format(
                        "x".join(str(1) for _ in range(self.dimension - 1))
                    ))

        if self.init_fixed_transform and len(self.init_fixed_transform) > 0:
            for transform in self.init_fixed_transform:
                optionals.append(transform)
                if not self.register_last_dimension:
                    optionals.append("--restrict-deformation {}x0".format(
                        "x".join(str(1) for _ in range(self.dimension - 1))
                    ))

        if self.seed:
            optionals.append("--random-seed {}".format(self.seed))

        for ants_pass in self.passes:
            optionals.append(ants_pass.serialize(voxel_size))
            if not self.register_last_dimension:
                optionals.append("--restrict-deformation {}".format(
                    ants_pass.get_time_restriction(self.dimension)
                ))

        return " ".join([
            "--dimensionality {} --float {}".format(
                self.dimension, 1 if self.use_float else 0
            ),
            "--interpolation {} --winsorize-image-intensities [{},{}]".format(
                self.interpolation, *self.inlier_range
            )
        ]) + " ".join(optionals)


_at_aliases = {
    "dim": "AntsTransformConfiguration.dimensionality",
    "interp": "AntsTransformConfiguration.interpolation",
    "fill": "AntsTransformConfiguration.fill_value",
    "type": "AntsTransformConfiguration.image_type"
}


class ImageType(PyEnum):
    SCALAR = 0
    VECTOR = 1
    TENSOR = 2
    TIMESERIES = 3
    RGB = 4


class AntsTransformConfiguration(mrHARDIConfigurable):
    interpolation = Enum(
        ["Linear", "NearestNeighbor", "Gaussian", "BSpline", "MultiLabel"],
        "Linear"
    ).tag(config=True)
    fill_value = Integer(0).tag(config=True)
    dimensionality = Integer(None, allow_none=True).tag(config=True)
    image_type = convert_enum(ImageType, None, True).tag(config=True)

    @default('app_aliases')
    def _app_aliases_default(self):
        return _at_aliases

    def _validate(self):
        pass

    def serialize(self, *args, **kwargs):
        serialization = "-n {} -f {}".format(
            self.interpolation, self.fill_value
        )
        if self.dimensionality:
            serialization += " -d {}".format(self.dimensionality)
        return serialization


class AntsMotionCorrectionConfiguration(mrHARDIConfigurable):
    passes = List(
        DictInstantiatingInstance(
            klass=AntsPass, add_init=dict(
                is_motion_correction=True,
                name_dict={
                    "smooth": "smoothingSigmas",
                    "shrink": "shrinkFactors"
                }
            )
        ),
        [], allow_none=True,
        help="List of registration passes (Rigid, Affine or SyN)"
    ).tag(config=True)
    dimension = Integer(
        3, min=2, max=3, help="Number of dimensions of the input images"
    ).tag(config=True)
    scale_estimator = Bool(
        False, help="Use scale estimator to control optimization"
    ).tag(config=True)
    register_to_prior = Bool(
        True, help="Register to prior volume instead of registering "
                   "all time points to template image"
    ).tag(config=True)
    n_template_points = Integer(
        10, help="Number of time points to use "
                 "to construct the moving template"
    ).tag(config=True)
    learn_once = Bool(
        False, help="If true, the learning step size will only be "
                    "evaluated at the beginning of each stage"
    ).tag(config=True)
    average = Bool(
        False, help="If True, the timeseries is averaged before "
                    "motion correction is applied"
    ).tag(config=True)
    to_field = Bool(
        False, help="If True, writes the transform as a displacement "
                    "field over the timeseries"
    ).tag(config=True)

    def _validate(self):
        if not 2 <= self.dimension <= 3:
            raise ConfigError(
                "Dimension of input images must be between 2 and 4"
            )

    def serialize(self, voxel_size, *args, **kwargs):
        optionals, init_i = [''], 0

        for ants_pass in self.passes:
            optionals.append(ants_pass.serialize(voxel_size))

        if self.scale_estimator:
            optionals.append("--useScalesEstimator")

        if not self.register_to_prior:
            optionals.append("--useFixedReferenceImage 1")

        if self.learn_once:
            optionals.append("--use-estimate-learning-rate-once")

        if self.average:
            optionals.append("--average-image")

        if self.to_field:
            optionals.append("--write-displacement")

        return " ".join([
            "--dimensionality {}".format(self.dimension),
            "--n-images {}".format(self.n_template_points),
        ]) + " ".join(optionals)
