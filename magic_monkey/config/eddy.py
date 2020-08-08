from enum import Enum

from traitlets import Integer
from traitlets.config import Bool, Instance, default
from traitlets.config.loader import ConfigError

from magic_monkey.base.ListValuedDict import ListValuedDict
from magic_monkey.base.application import convert_enum, BoundedInt, \
    MagicMonkeyConfigurable
from magic_monkey.config.utils import serialize_fsl


class OutlierReplacement(ListValuedDict):
    class Method(Enum):
        slice = "sw"
        multi_band = "mb"
        both = "both"

    def __init__(
        self, n_std=4, n_vox=250, mb_factor=1, mb_offset=0,
        method=Method.slice, pos_neg=False, sum_squared=False
    ):
        super().__init__(dict(
            repol=True,
            ol_nstd=n_std,
            ol_nvox=n_vox,
            ol_type=method.value,
            ol_pos=pos_neg,
            ol_sqr=sum_squared,
            mb=mb_factor,
            mb_offs=mb_offset
        ))

    def serialize(self):
        return serialize_fsl(self, " ", True)


class IntraVolMotionCorrection(ListValuedDict):
    class Interpolation(Enum):
        trilinear = "trilinear"
        spline = "spline"

    def __init__(
        self, n_iter=5, w_reg=1,
        interpolation=Interpolation.trilinear,
        t_motion_order=0
    ):
        super().__init__(dict(
            mporder=t_motion_order,
            s2v_niter=n_iter,
            s2v_lambda=w_reg,
            s2v_interp=interpolation.value
        ))

    def serialize(self):
        return serialize_fsl(self, " ", True)


class SusceptibilityCorrection(ListValuedDict):
    def __init__(self, n_iter=10, w_reg=10, knot_spacing=10):
        super().__init__(dict(
            estimate_move_by_susceptibility=True,
            mbs_niter=n_iter,
            mbs_lambda=w_reg,
            mbs_ksp=knot_spacing
        ))

    def serialize(self):
        return serialize_fsl(self, " ", True)


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
        {'EddyConfiguration': {'separate_subject_field', False}},
        "Link subject movement and field DC component"
    )
)


class EddyConfiguration(MagicMonkeyConfigurable):
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
    pre_filter_width = Integer(0).tag(config=True)
    n_iter = Integer(5).tag(config=True)
    fill_empty = Bool(False).tag(config=True)
    interpolation = convert_enum(
        Interpolation, Interpolation.spline
    ).tag(config=True)
    resampling = convert_enum(Resampling, Resampling.jacobian).tag(config=True)
    n_voxels_hp = Integer(1000).tag(config=True)
    qspace_smoothing = BoundedInt(10, 1, 10).tag(config=True)

    skip_end_alignment = Bool(False).tag(config=True)
    separate_subject_field = Bool(True).tag(config=True)
    check_if_shelled = Bool(True).tag(config=True)

    enable_cuda = Bool(False).tag(config=True)
    outlier_model = Instance(
        OutlierReplacement, allow_none=True
    ).tag(config=True, none_to_default=True, cuda_required=True)
    slice_to_vol = Instance(
        IntraVolMotionCorrection, allow_none=True
    ).tag(config=True, none_to_default=True, cuda_required=True)
    susceptibility = Instance(
        SusceptibilityCorrection, allow_none=True
    ).tag(config=True, none_to_default=True, cuda_required=True)

    def _config_section(self):
        if self.enable_cuda:
            for trait in self.traits(
                none_to_default=True, cuda_required=True
            ).values():
                if isinstance(trait, Instance):
                    trait.set(self, trait.klass())

        return super()._config_section()

    def validate(self):
        if not self.enable_cuda and (self.outlier_model or self.slice_to_vol):
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

    def serialize(self):
        base_arguments = serialize_fsl(dict(
            flm=self.field_model,
            slm=self.current_model,
            fwhm=self.pre_filter_width,
            niter=self.n_iter,
            nvoxhp=self.n_voxels_hp,
            fep=self.fill_empty,
            dont_sep_offs_move=not self.separate_subject_field,
            dont_peas=not self.skip_end_alignment,
            data_is_shelled=not self.check_if_shelled
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
                base_arguments, self.susceptibility.serialize()
            ])

        return base_arguments
