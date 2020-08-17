from copy import deepcopy
from enum import Enum

from magic_monkey.base.ListValuedDict import MagicDict
from magic_monkey.base.fsl import serialize_fsl_args


class OutlierReplacement(MagicDict):
    class Method(Enum):
        slice = "sw"
        multi_band = "mb"
        both = "both"

    def __init__(
        self, n_std=4, n_vox=250, mb_factor=1, mb_offset=0,
        method=Method.slice, pos_neg=False, sum_squared=False
    ):
        super().__init__(
            dict(
                ol_nstd=n_std,
                ol_nvox=n_vox,
                ol_type=method if isinstance(method, str) else method.value,
                ol_pos=pos_neg,
                ol_sqr=sum_squared,
                mb=mb_factor,
                mb_offs=mb_offset
            ),
            dict(
                ol_nstd="n_std",
                ol_nvox="n_vox",
                ol_type="method",
                ol_pos="pos_neg",
                ol_sqr="sum_squared",
                mb="mb_factor",
                mb_offs="mb_offset"
            )
        )

    def serialize(self):
        args = deepcopy(self)
        args["repol"] = True
        return serialize_fsl_args(self, " ", True)


class IntraVolMotionCorrection(MagicDict):
    class Interpolation(Enum):
        trilinear = "trilinear"
        spline = "spline"

    def __init__(
        self, n_iter=5, w_reg=1,
        interpolation=Interpolation.trilinear,
        t_motion_order=0
    ):
        super().__init__(
            dict(
                mporder=t_motion_order,
                s2v_niter=n_iter,
                s2v_lambda=w_reg,
                s2v_interp=(
                    interpolation if isinstance(interpolation, str)
                    else interpolation.value
                )
            ),
            dict(
                mporder="t_motion_order",
                s2v_niter="n_iter",
                s2v_lambda="w_reg",
                s2v_interp="interpolation"
            )
        )

    def serialize(self):
        return serialize_fsl_args(self, " ", True)


class SusceptibilityCorrection(MagicDict):
    def __init__(self, n_iter=10, w_reg=10, knot_spacing=10):
        super().__init__(
            dict(
                mbs_niter=n_iter,
                mbs_lambda=w_reg,
                mbs_ksp=knot_spacing
            ),
            dict(
                mbs_niter="n_iter",
                mbs_lambda="w_reg",
                mbs_ksp="knot_spacing"
            )
        )

    def serialize(self):
        args = deepcopy(self)
        args["estimate_move_by_susceptibility"] = True
        return serialize_fsl_args(args, " ", True)
