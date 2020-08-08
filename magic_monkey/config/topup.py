from abc import ABC, abstractmethod
from enum import Enum as BaseEnum

from traitlets.config import Instance, List, Bool, Unicode

from magic_monkey.base.ListValuedDict import ListValuedDict
from magic_monkey.base.application import convert_enum, \
    MagicMonkeyConfigurable, SelfInstantiatingInstance, \
    DictInstantiatingInstance
from magic_monkey.config.utils import serialize_fsl


class Serializable(ABC):
    @property
    @abstractmethod
    def serialize(self):
        pass


class Mergeable(ListValuedDict):
    def merge(self, *mergeables):
        try:
            self.update(mergeables[0])
            self.merge(*mergeables[1:])
        except StopIteration:
            pass
        except IndexError:
            pass


def _key_trans(dictionary, key_trans):
    return dict(map(lambda k, v: (key_trans[k], v), *dictionary.items()))


_topup_pass_key_trans = {
    "warpres=": "warp_resolution",
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
        ))

        self["lambda"] = w_reg

    def serialize(self):
        return serialize_fsl(self)

    def __repr__(self):
        return str(_key_trans(self._dict, _topup_pass_key_trans))


_default_passes = [
    TopupPass(20, 2, 8, 5, 5E-3),
    TopupPass(16, 2, 6, 5, 1E-3),
    TopupPass(14, 2, 4, 5, 1E-4),
    TopupPass(12, 2, 3, 5, 15E-6),
    TopupPass(10, 2, 3, 5, 5E-7),
    TopupPass(
        6, 1, 2, 10, 5E-7, False, TopupPass.Minimizer.Scaled_Conjugate_Gradient
    ),
    TopupPass(
        4, 1, 1, 10, 5E-8, False, TopupPass.Minimizer.Scaled_Conjugate_Gradient
    ),
    TopupPass(
        4, 1, 0, 20, 5E-10, False,
        TopupPass.Minimizer.Scaled_Conjugate_Gradient
    ),
    TopupPass(
        4, 1, 0, 20, 5E-11, False,
        TopupPass.Minimizer.Scaled_Conjugate_Gradient
    )
]


class TopupConfiguration(MagicMonkeyConfigurable):
    def validate(self):
        pass

    class RegulModel(BaseEnum):
        bending_energy = "bending_energy"
        membrane_energy = "membrane_energy"

    class SplineOrder(BaseEnum):
        quadratic = 2
        cubic = 3

    class Interpolation(BaseEnum):
        linear = "linear"
        spline = "spline"

    passes = List(
        DictInstantiatingInstance(klass=TopupPass),
        default_value=_default_passes
    ).tag(config=True)

    ssq_scale_lambda = Bool(default_value=True).tag(config=True)
    scale_intensities = Bool(default_value=True).tag(config=True)
    reg_model = convert_enum(
        RegulModel, RegulModel.bending_energy
    ).tag(config=True)
    spl_order = convert_enum(
        SplineOrder, SplineOrder.quadratic
    ).tag(config=True)
    interpolation = convert_enum(
        Interpolation, Interpolation.linear
    ).tag(config=True)
    precision = Unicode(u'double').tag(config=True)

    def serialize(self):
        if len(self.passes) > 1:
            self.passes[0].merge(*self.passes[1:])
            self.passes = self.passes[:1]

        return serialize_fsl(dict(
            ssqlambda=int(self.ssq_scale_lambda),
            regmod=TopupConfiguration.RegulModel[self.reg_model].value,
            splineorder=TopupConfiguration.SplineOrder[self.spl_order].value,
            numprec=self.precision,
            interp=TopupConfiguration.Interpolation[self.interpolation].value,
            scale=int(self.scale_intensities)
        )) + "\n" + self.passes[0].serialize()
