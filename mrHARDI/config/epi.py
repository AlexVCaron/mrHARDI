from enum import Enum as BaseEnum

from traitlets import Float, Integer
from traitlets.config import Bool, List, Unicode, default

from mrHARDI.base.application import (BoundedInt,
                                      DictInstantiatingInstance,
                                      mrHARDIConfigurable,
                                      convert_enum)
from mrHARDI.base.fsl import serialize_fsl_args
from mrHARDI.traits.topup import TopupPass


class EpiCorrectionConfiguration(mrHARDIConfigurable):
    ceil_value = Float(
        0.9, help="Higher bound determining a valid b-value for a b0 volume"
    ).tag(config=True)

    strict = Bool(
        False, help="If True, test b0 b-values with "
                    "\"<\" comparator instead of \"<=\""
    ).tag(config=True)

    def _validate(self):
        pass

    def serialize(self, *args, **kwargs):
        pass


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


_aliases = {
    "reg": "TopupConfiguration.reg_model",
    "spl": "TopupConfiguration.spl_order",
    "interp": "TopupConfiguration.interpolation",
    "b0-thr": "TopupConfiguration.ceil_value"
}


_flags = {
    "no-ssql": (
        {"TopupConfiguration": {"ssq_scale_lambda": False}},
        "Disable scaling lambda with SSQ value at current iteration."
    ),
    "static-internsity": (
        {"TopupConfiguration": {"scale_intensities": False}},
        "Disable image intensity rescaling between each iteration."
    ),
    "strict-eq": (
        {"TopupConfiguration": {"strict": True}},
        "If True, test b0 b-values with \"<\" comparator instead of \"<=\""
    )
}


class TopupConfiguration(EpiCorrectionConfiguration):
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

    @default('app_aliases')
    def _app_aliases_default(self):
        return _aliases

    @default('app_flags')
    def _app_flags_default(self):
        return _flags

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


_bm_aliases = {
    "b0-thr": "BlockMatchingEPIConfiguration.ceil_value"
}


_bm_flags = {
    "no-w-agg": (
        {"BlockMatchingEPIConfiguration": {"weight_agregation": False}},
        "Disable weight agregation."
    ),
    "no-init": (
        {"BlockMatchingEPIConfiguration": {"initialize_bm": False}},
        "Disable BM initialization with Voss et al."
    ),
    "strict-eq": (
        {"BlockMatchingEPIConfiguration": {"strict": True}},
        "If True, test b0 b-values with \"<\" comparator instead of \"<=\""
    )
}


class BlockMatchingEPIConfiguration(EpiCorrectionConfiguration):
    class SimilarityMetric(BaseEnum):
        MSSE = 0
        CC = 1
        SCC = 2

    class AgregatorType(BaseEnum):
        Baloo = 0
        MSmoother = 1

    class BetweenBlocksModel(BaseEnum):
        direction = 0
        direction_scale = 1
        direction_scale_skew = 2

    depth = Integer(
        default_value=3, help="Depth of the decomposition pyramid"
    ).tag(config=True)
    optimizer_niter = BoundedInt(
        100, 1, help="Local optimizer maximum number of iterations"
    ).tag(config=True)
    block_match_niter = BoundedInt(
        10, 1, help="Block matching maximum number of iterations"
    ).tag(config=True)
    convergence_thr = Float(
        0.01, help="M-estimator convergence threshold"
    ).tag(config=True)

    similarity_metric = convert_enum(
        SimilarityMetric, SimilarityMetric.SCC
    ).tag(config=True)
    agregator = convert_enum(
        AgregatorType, AgregatorType.Baloo
    ).tag(config=True)
    between_blocks = convert_enum(
        BetweenBlocksModel, BetweenBlocksModel.direction_scale_skew
    ).tag(config=True)

    exponential_order = BoundedInt(
        0, 0, 1, help="Field exponentiation approximation order"
    ).tag(config=True)

    outlier_sigma = Float(
        3., help="Local pairings outlier rejection sigma"
    ).tag(config=True)
    elastic_sigma = Float(
        2., help="Elastic regularization sigma"
    ).tag(config=True)
    extrapolation_sigma = Float(
        3., help="Local pairings extrapolation sigma"
    ).tag(config=True)
    smoothing_sigma = Float(
        2., help="Smooting sigma for the distortion field. Only used if "
                 "initializing the BM algorithm with Voss et al. method"
    )

    bobyqa_skew_ub = Float(
        45., help="Bobyqa skew upper bound (in degree)"
    ).tag(config=True)
    bobyqa_scale_ub = Float(
        5., help="Bobyqa scale upper bound"
    ).tag(config=True)
    bobyqa_translation_ub = Float(
        3., help="Bobyqa translation upper bound"
    ).tag(config=True)

    block_fraction = Float(
        0.8, help="Percentage of blocks of highest "
                  "variance kept at each iteration"
    ).tag(config=True)
    block_stdev_thr = Float(
        15., help="Block standard deviation lower threshold"
    ).tag(config=True)
    block_spacing = Integer(
        2, help="Block spacing"
    ).tag(config=True)
    block_size = Integer(
        3, help="Block size"
    ).tag(config=True)

    weight_agregation = Bool(default_value=True).tag(config=True)
    initialize_bm = Bool(default_value=True).tag(config=True)

    @default('app_flags')
    def _app_flags_default(self):
        return _bm_flags

    @default('app_aliases')
    def _app_aliases_default(self):
        return _bm_aliases

    def _validate(self):
        pass

    def serialize(self, *args, **kwargs):
        base_opts = "-p {} --oi{} --mi {} --met {}".format(
            self.depth,
            self.optimizer_niter,
            self.block_match_niter,
            self.convergence_thr
        )

        klass = BlockMatchingEPIConfiguration
        model_opts = "--metric {} --agregator {} -t {} -e {}".format(
            klass.SimilarityMetric[self.similarity_metric].value,
            klass.AgregatorType[self.agregator].value,
            klass.BetweenBlocksModel[self.between_blocks].value,
            self.exponential_order
        )

        sigma_opts = "--os {} --es {} --fs {}".format(
            self.outlier_sigma, self.elastic_sigma, self.extrapolation_sigma
        )

        bobyqa_opts = "--sku {} --scu {} --tub {}".format(
            self.bobyqa_skew_ub,
            self.bobyqa_scale_ub,
            self.bobyqa_translation_ub
        )

        block_opts = "-k {} -s {} --sp {} --bs {}".format(
            self.block_fraction,
            self.block_stdev_thr,
            self.block_spacing,
            self.block_size
        )

        optional_opts = []
        if not self.weight_agregation:
            optional_opts.append("--no-weighted-agregation")

        opts = [base_opts, model_opts, sigma_opts, bobyqa_opts, block_opts]
        opts += optional_opts
        return opts.join(" ")
