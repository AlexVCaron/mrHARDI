from enum import Enum as BaseEnum

from traitlets import Float
from traitlets.config import Bool, List, Unicode

from magic_monkey.base.application import (DictInstantiatingInstance,
                                           MagicMonkeyConfigurable,
                                           convert_enum)
from magic_monkey.base.fsl import serialize_fsl_args
from magic_monkey.traits.topup import TopupPass

_default_passes = [
    TopupPass(5, 2, 8, 5, 5E-3),
    TopupPass(4, 2, 6, 5, 1E-3),
    TopupPass(3.5, 2, 4, 5, 1E-4),
    TopupPass(3, 2, 3, 5, 15E-6),
    TopupPass(2.5, 2, 3, 5, 5E-7),
    TopupPass(
        1.5, 1, 2, 10, 5E-7, False,
        TopupPass.Minimizer.Scaled_Conjugate_Gradient
    ),
    TopupPass(
        1, 1, 1, 10, 5E-8, False,
        TopupPass.Minimizer.Scaled_Conjugate_Gradient
    ),
    TopupPass(
        1, 1, 0, 20, 5E-10, False,
        TopupPass.Minimizer.Scaled_Conjugate_Gradient
    ),
    TopupPass(
        1, 1, 0, 20, 5E-11, False,
        TopupPass.Minimizer.Scaled_Conjugate_Gradient
    )
]


class TopupConfiguration(MagicMonkeyConfigurable):
    def _validate(self):
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

    ceil_value = Float(
        0.9, help="Higher bound determining a valid b-value for a b0 volume"
    ).tag(config=True)

    strict = Bool(
        False, help="If True, test b0 b-values with "
                    "\"<\" comparator instead of \"<=\""
    ).tag(config=True)

    def serialize(self, voxel_size, *args, **kwargs):
        if len(self.passes) > 1:
            self.passes[0].merge(*self.passes[1:])
            self.passes = [self.passes[0]]

        return serialize_fsl_args(dict(
            ssqlambda=int(self.ssq_scale_lambda),
            regmod=TopupConfiguration.RegulModel[self.reg_model].value,
            splineorder=TopupConfiguration.SplineOrder[self.spl_order].value,
            numprec=self.precision,
            interp=TopupConfiguration.Interpolation[self.interpolation].value,
            scale=int(self.scale_intensities)
        )) + "\n" + self.passes[0].serialize(voxel_size)
