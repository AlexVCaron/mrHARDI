from copy import deepcopy
from enum import Enum

from mrHARDI.base.ListValuedDict import MagicDict
from mrHARDI.base.fsl import serialize_fsl_args


class OutlierReplacement(MagicDict):
    class Method(Enum):
        slice = "sw"
        multi_band = "gw"
        both = "both"

    def __init__(
        self, n_std=4, n_vox=250, method=Method.slice,
        pos_neg=False, sum_squared=False
    ):
        super().__init__(
            dict(
                ol_nstd=n_std,
                ol_nvox=n_vox,
                ol_type=method if isinstance(method, str) else method.value,
                ol_pos=pos_neg,
                ol_sqr=sum_squared
            ),
            dict(
                ol_nstd="n_std",
                ol_nvox="n_vox",
                ol_type="method",
                ol_pos="pos_neg",
                ol_sqr="sum_squared",
                repol="repol"
            )
        )

    def serialize(self):
        args = deepcopy(self)
        args["repol"] = True
        return serialize_fsl_args(args, " ", True)


class IntraVolMotionCorrection(MagicDict):
    class Interpolation(Enum):
        trilinear = "trilinear"
        spline = "spline"

    def __init__(
        self, n_iter=5, w_reg=1,
        interpolation=Interpolation.trilinear,
        t_motion_fraction=1
    ):
        self.motion_fraction = t_motion_fraction
        super().__init__(
            dict(
                mporder=0,
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

    def set_mporder(self, n_excitations):
        self["mporder"] = int(n_excitations / self.motion_fraction)

    def serialize(self):
        return serialize_fsl_args(self, " ", True)


class SusceptibilityCorrection(MagicDict):
    def __init__(self, n_iter=10, w_reg=10, knot_spacing=5.):
        super().__init__(
            dict(
                mbs_niter=n_iter,
                mbs_lambda=w_reg,
                mbs_ksp=knot_spacing
            ),
            dict(
                mbs_niter="n_iter",
                mbs_lambda="w_reg",
                mbs_ksp="knot_spacing",
                estimate_move_by_susceptibility="est_suscep"
            )
        )

    def serialize(self, voxel_size):
        args = deepcopy(self)
        args["mbs_ksp"] *= voxel_size
        args["estimate_move_by_susceptibility"] = True
        return serialize_fsl_args(args, " ", True)
