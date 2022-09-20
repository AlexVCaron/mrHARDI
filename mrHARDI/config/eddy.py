from enum import Enum

from traitlets import Integer, Float
from traitlets.config import Bool, Instance, default, List
from traitlets.config.loader import ConfigError

from mrHARDI.base.application import (BoundedInt,
                                           DictInstantiatingInstance,
                                           mrHARDIConfigurable,
                                           convert_enum)
from mrHARDI.base.fsl import serialize_fsl_args
from mrHARDI.traits.eddy import (IntraVolMotionCorrection,
                                      OutlierReplacement,
                                      SusceptibilityCorrection)

_flags = dict(
    cuda=(
        {'EddyConfiguration': {'enable_cuda': True}},
        "Enables computing using a cuda compatible gpu"
    ),
    shelled=(
        {'EddyConfiguration': {'check_if_shelled': False}},
        "Disable sanity check on multishell data"
    ),
    skip_end=(
        {'EddyConfiguration': {'skip_end_alignment': True}},
        "Disable last gradient shell alignment"
    ),
    link_move=(
        {'EddyConfiguration': {'separate_subject_field': False}},
        "Link subject movement and field DC component"
    ),
    umask=(
        {'EddyConfiguration': {'mask_output': True}},
        "Outputs unmasked eddy corrected images"
    ),
    seed=(
        {'EddyConfiguration': {'set_seed': True}},
        "Set the RNG seed for reproducibility"
    )
)


class EddyConfiguration(mrHARDIConfigurable):
    class FieldModel(Enum):
        linear = "linear"
        quadratic = "quadratic"
        cubic = "cubic"

    class CurrentModel(Enum):
        none = "none"
        linear = "linear"
        quadratic = "quadratic"

    class Interpolation(Enum):
        spline = "spline"
        trilinear = "trilinear"

    class Resampling(Enum):
        jacobian = "jac"
        lsquare = "lsr"

    @default('app_flags')
    def _app_flags_default(self):
        return _flags

    field_model = convert_enum(
        FieldModel, FieldModel.quadratic
    ).tag(config=True)
    current_model = convert_enum(
        CurrentModel, CurrentModel.none
    ).tag(config=True)
    pre_filter_width = List(Float(), [0]).tag(config=True)
    n_iter = Integer(5).tag(config=True)
    fill_empty = Bool(False).tag(config=True)
    interpolation = convert_enum(
        Interpolation, Interpolation.spline
    ).tag(config=True)
    resampling = convert_enum(Resampling, Resampling.jacobian).tag(config=True)
    n_voxels_hp = Integer(1000).tag(config=True)
    qspace_smoothing = BoundedInt(10, 1, 10).tag(config=True)

    skip_end_alignment = Bool(False).tag(config=True)
    use_b0_peas = Bool(False).tag(config=True)
    separate_subject_field = Bool(True).tag(config=True)
    check_if_shelled = Bool(True).tag(config=True)

    mask_output = Bool(True).tag(config=True)

    enable_cuda = Bool(False).tag(config=True)
    outlier_model = DictInstantiatingInstance(
        OutlierReplacement, allow_none=True
    ).tag(config=True, none_to_default=True, cuda_required=True)
    slice_to_vol = DictInstantiatingInstance(
        IntraVolMotionCorrection, allow_none=True
    ).tag(config=True, none_to_default=True, cuda_required=True)
    susceptibility = DictInstantiatingInstance(
        SusceptibilityCorrection, allow_none=True
    ).tag(config=True, none_to_default=True, cuda_required=True)

    ceil_value = Float(
        0.9, help="Higher bound determining a valid b-value for a b0 volume"
    ).tag(config=True)

    strict = Bool(
        False, help="If True, test b0 b-values with "
                    "\"<\" comparator instead of \"<=\""
    ).tag(config=True)

    set_seed = Bool(
        False, help="Set the RNG seed for reproducibility"
    ).tag(config=True)

    def _config_section(self):
        if self.enable_cuda:
            print("cuda enabled")
            for trait in self.traits(
                none_to_default=True, cuda_required=True
            ).values():
                if isinstance(trait, Instance):
                    trait.set(self, trait.klass())

        return super()._config_section()

    def _validate(self):
        print(self.outlier_model)
        if not self.enable_cuda and (
            self.outlier_model or self.slice_to_vol or self.susceptibility
        ):
            raise ConfigError(
                "{} needs Cuda to be enabled to use :\n{}".format(
                    self.__class__.__name__, "\n".join([
                        "outliers detection : {}".format(
                            self.outlier_model is not None
                        ),
                        "slice to volume : {}".format(
                            self.slice_to_vol is not None
                        )
                    ])
                )
            )

    def serialize(self, voxel_size, *args, **kwargs):
        base_arguments = serialize_fsl_args(dict(
            flm=self.field_model,
            slm=self.current_model,
            fwhm=",".join(str(pf * voxel_size) for pf in self.pre_filter_width),
            niter=self.n_iter,
            nvoxhp=self.n_voxels_hp,
            fep=self.fill_empty,
            resamp=EddyConfiguration.Resampling[self.resampling].value,
            interp=self.interpolation,
            ff=self.qspace_smoothing,
            dont_sep_offs_move=(not self.separate_subject_field),
            dont_peas=self.skip_end_alignment,
            b0_peas=self.use_b0_peas,
            data_is_shelled=(not self.check_if_shelled),
            dont_mask_output=(not self.mask_output),
            initrand=int(self.set_seed)
        ), " ", True)

        if self.outlier_model is not None:
            base_arguments = " ".join([
                base_arguments, self.outlier_model.serialize()
            ])

        if self.slice_to_vol is not None:
            base_arguments = " ".join([
                base_arguments, self.slice_to_vol.serialize()
            ])

        if self.susceptibility is not None:
            base_arguments = " ".join([
                base_arguments, self.susceptibility.serialize(voxel_size)
            ])

        return base_arguments
