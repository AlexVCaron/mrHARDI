from copy import copy

import nibabel as nib

from os.path import exists, join

import numpy as np
from traitlets import Unicode, Bool, Dict, Integer
from traitlets.config import ArgumentError

from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    ChoiceList, ChoiceEnum

# fmd = fascicle md --check
# fad = fascicle ad --check
# frd = fascicle rd --check
# ffa = fascicle fa --check
# ff = fascicle fractions --check
# peaks = main eigenvectors of each fascicle

_DIAMOND_METRICS = [
    "fmd", "fad", "frd", "ffa", "ff", "peaks"
]

# rf = restricted fraction --check
# wf = free water fraction --check
# hf = hindered fraction of each fascicle --check
# diso = isotropic diffusion of fiber tensors p-28 --check
# daniso = anisotropic diffusion of fiber tensors p-28 --check
# mdiso = mean isotropic diffusion of fiber tensors p-28 --check
# mdaniso = mean anisotropic diffusion of fiber tensors p-28 --check
# sra = diffusion scaled relative anisotropy p-30 --check
# vf = volume fraction p-30 --check
# ua = diffusion ultimate anisotropy indices p-30 --check
# viso = variance of isotropic diffusivities p-46 --check
# veig = average variance of eigenvalues p-46 --check
# vdelta = variance of variances of eigenvalues p-46 --check

_OPTIONAL_METRICS = [
    "rf", "wf", "hf", "diso", "daniso", "mdiso", "mdaniso",
    "sra", "vf", "ua", "viso", "veig", "vdelta"
]

# ufa = micro fa p-54 --check
# op = orientational order p-55 --check
# mkiso = isotropic mean kurtosis --check
# mkaniso = anisotropic mean kurtosis --check

_MAGIC_DIAMOND_METRICS = [
    "ufa", "op"
]


class DiamondMetricsEnum(ChoiceEnum):
    def __init__(self, **kwargs):
        super().__init__(copy(_DIAMOND_METRICS), **kwargs)


class MagicDiamondMetricsEnum(ChoiceEnum):
    def __init__(self, **kwargs):
        super().__init__(copy(_MAGIC_DIAMOND_METRICS), **kwargs)


class DiamondOptionalMetricsEnum(ChoiceEnum):
    def __init__(self, **kwargs):
        super().__init__(copy(_OPTIONAL_METRICS), **kwargs)


_aliases = {
    'metrics': 'DiamondMetrics.metrics',
    'magic-metrics': 'DiamondMetrics.mmetrics',
    'opt-metrics': 'DiamondMetrics.opt_metrics',
    'in': 'DiamondMetrics.input_prefix',
    'out': 'DiamondMetrics.output_prefix',
    'n': 'DiamondMetrics.n_fascicles',
    'affine': 'DiamondMetrics.affine'
}


_flags = dict(
    colors=(
        {'DiamondMetrics': {'output_colors': True}},
        "create color map for compatible metrics based on eigenvectors"
    ),
    fFW=(
        {'DiamondMetrics': {'free_water': True}},
        "dataset has a free water fraction computed"
    ),
    fRS=(
        {'DiamondMetrics': {'restricted': True}},
        "dataset has a restricted fraction computed"
    ),
    fHD=(
        {'DiamondMetrics': {'hindered': True}},
        "dataset has a hindered fraction computed"
    ),
    reymbaut=(
        {'DiamondMetrics': {'output_reymbaut_convention', True}},
        "output the reymbaut convention over diffusion tensors"
    ),
    cache=(
        {'DiamondMetrics': {'save_cache', True}},
        "save metrics computing execution cache"
    )
)


class DiamondMetrics(MagicMonkeyBaseApplication):
    metrics = ChoiceList(
        copy(_DIAMOND_METRICS), DiamondMetricsEnum, copy(_DIAMOND_METRICS)
    ).tag(config=True)
    mmetrics = ChoiceList(
        copy(_MAGIC_DIAMOND_METRICS) + ["all"], MagicDiamondMetricsEnum, []
    ).tag(config=True)
    opt_metrics = ChoiceList(
        copy(_OPTIONAL_METRICS) + ["all"], DiamondOptionalMetricsEnum, []
    ).tag(config=True)

    input_prefix = Unicode().tag(config=True, required=True)
    output_prefix = Unicode().tag(config=True, required=True)
    n_fascicles = Integer().tag(config=True, required=True)
    affine = Unicode().tag(config=True, required=True)

    output_colors = Bool(False).tag(config=True)

    free_water = Bool(False).tag(config=True)
    restricted = Bool(False).tag(config=True)
    hindered = Bool(False).tag(config=True)

    output_reymbaut_convention = Bool(False).tag(config=True)

    save_cache = Bool(False).tag(config=True)

    cache = Dict({})

    aliases = Dict(_aliases)
    flags = Dict(_flags)

    def _validate(self):
        if "all" in self.mmetrics:
            self.traits()["mmetrics"].set(self, _MAGIC_DIAMOND_METRICS)
        if "all" in self.opt_metrics:
            self.traits()["opt_metrics"].set(self, _OPTIONAL_METRICS)

        super()._validate()

    def _validate_required(self):
        super()._validate_required()

        if len(self.mmetrics) > 0:
            if not sum(
                exists(join(self.input_prefix, enc))
                for enc in ["lin", "sph"]
            ) == 2:
                raise ArgumentError(
                    "Magic diamond requires both linear and "
                    "spherical acquisitions to output metrics.\n"
                    "Current path does not provides \"lin\" and \"sph\" "
                    "directories : {}".format(self.input_prefix)
                )

    def _start(self):
        import magic_monkey.config.metrics.diamond as metrics_module

        mask = None
        if exists("{}_mask.nii.gz".format(self.input_prefix)):
            mask = nib.load("{}_mask.nii.gz".format(self.input_prefix))

        affine = np.loadtxt(self.affine)

        for metric in self.metrics + self.mmetrics + self.opt_metrics:
            klass = getattr(
                metrics_module, "{}Metric".format(metric.capitalize())
            )

            klass(
                self.n_fascicles, self.input_prefix,
                self.output_prefix, self.cache,
                affine, mask=mask.get_fdata().astype(bool), shape=mask.shape,
                colors=self.output_colors, with_fw=self.free_water,
                with_res=self.restricted, with_hind=self.hindered
            ).measure()

        if self.output_reymbaut_convention:
            self._output_r_conv()

        if self.output_colors:
            self._output_colors()

        if self.save_cache:
            self._save_cache()

    def _output_colors(self):
        pass

    def _output_r_conv(self):
        pass

    def _save_cache(self):
        pass
