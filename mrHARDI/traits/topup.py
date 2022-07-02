from enum import Enum as BaseEnum

from mrHARDI.base.ListValuedDict import Mergeable
from mrHARDI.base.fsl import serialize_fsl_args

_topup_pass_key_trans = {
    "warpres": "warp_resolution",
    "subsamp": "subsampling",
    "fwhm": "blur_fwhm",
    "miter": "n_iter",
    "estmov": "estimate_motion",
    "minmet": "minimizer",
    "lambda": "w_reg"
}


class TopupPass(Mergeable):
    class Minimizer(BaseEnum):
        Levenberg_Marquardt = 0
        Scaled_Conjugate_Gradient = 1

    def __init__(
        self, warp_resolution, subsampling, blur_fwhm, n_iter,
        w_reg, estimate_motion=True, minimizer=Minimizer.Levenberg_Marquardt
    ):
        if isinstance(minimizer, TopupPass.Minimizer):
            minimizer = minimizer.value

        if isinstance(estimate_motion, bool):
            estimate_motion = int(estimate_motion)
        elif (
            isinstance(estimate_motion, list) and
            any(isinstance(e, bool) for e in estimate_motion)
        ):
            estimate_motion = [int(e) for e in estimate_motion]

        super().__init__(dict(
            warpres=warp_resolution,
            subsamp=subsampling,
            fwhm=blur_fwhm,
            miter=n_iter,
            estmov=estimate_motion,
            minmet=minimizer
        ), _topup_pass_key_trans)

        self["lambda"] = w_reg

    def serialize(self, voxel_size):
        attributes = self.copy_attributes()
        attributes["warpres"] = [voxel_size * w for w in attributes["warpres"]]
        attributes["fwhm"] = [voxel_size * f for f in attributes["fwhm"]]
        return serialize_fsl_args(attributes)
