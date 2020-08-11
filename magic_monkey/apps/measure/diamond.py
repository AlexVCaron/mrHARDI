import time

from copy import copy
from os import mkdir
from pathlib import Path

import nibabel as nib

from os.path import exists, join

import numpy as np
from traitlets import Bool, Dict, Integer
from traitlets.config import ArgumentError

from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    ChoiceList, ChoiceEnum, required_file, output_prefix_argument, \
    affine_file, required_number

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
    haeberlen=(
        {'DiamondMetrics': {'output_haeberlen': True}},
        "output the haeberlen convention over output tensors"
    ),
    cache=(
        {'DiamondMetrics': {'save_cache': True}},
        "save metrics computing execution cache"
    )
)


class DiamondMetrics(MagicMonkeyBaseApplication):
    metrics = ChoiceList(
        copy(_DIAMOND_METRICS), DiamondMetricsEnum, copy(_DIAMOND_METRICS),
        help="Basic diamond metrics to run on the outputs"
    ).tag(config=True)
    mmetrics = ChoiceList(
        copy(_MAGIC_DIAMOND_METRICS) + ["all"], MagicDiamondMetricsEnum, [],
        help="Magic diamond metrics to run on the outputs "
             "(Requires tensor valued input, check your input "
             "prefix to assure it respects convection)"
    ).tag(config=True)
    opt_metrics = ChoiceList(
        copy(_OPTIONAL_METRICS) + ["all"], DiamondOptionalMetricsEnum, [],
        help="Optional diamond metrics to run on the outputs"
    ).tag(config=True)

    input_prefix = required_file(
        help="Prefix of diamond outputs (including mask)"
    )
    output_prefix = output_prefix_argument()
    n_fascicles = required_number(
        Integer, ignore_write=False,
        help="Maximum number of possible fascicles in a voxel"
    )
    affine = affine_file()

    output_colors = Bool(
        False, help="Output color metrics if available"
    ).tag(config=True)

    free_water = Bool(
        False, help="Acquisition has free water fraction computed"
    ).tag(config=True)
    restricted = Bool(
        False, help="Acquisition has restricted fraction computed"
    ).tag(config=True)
    hindered = Bool(
        False, help="Acquisition has hindered fraction computed"
    ).tag(config=True)

    output_haeberlen = Bool(
        False,
        help="Output iso, delta and eta decomposition of the diffusion tensor"
    ).tag(config=True)

    save_cache = Bool(
        False, help="Save the final data cache of the metrics computing"
    ).tag(config=True)

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
                    "Current path does not provides both \"lin\" and "
                    "\"sph\" directories : {}".format(self.input_prefix)
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

        if self.output_haeberlen:
            self._output_haeberlen()

        if self.save_cache:
            self._save_cache()

    def _output_haeberlen(self):
        from magic_monkey.config.metrics.diamond import HaeberlenConvention

        mask = None
        if exists("{}_mask.nii.gz".format(self.input_prefix)):
            mask = nib.load("{}_mask.nii.gz".format(self.input_prefix))

        affine = np.loadtxt(self.affine)

        HaeberlenConvention(
            self.n_fascicles, self.input_prefix, self.output_prefix,
            self.cache, affine, mask.get_fdata().astype(bool), mask.shape,
            self.output_colors, self.free_water, self.restricted, self.hindered
        ).measure()

    def _save_cache(self):
        fname = "diamond_cache_{}".format(time.strftime("%c"))

        try:
            Path(
                "{}_{}.npy".format(self.output_prefix, fname)
            ).touch(exist_ok=True)
        except BaseException:
            for char in [" ", ":", ",", ".", "-", "\\", "/", ";"]:
                fname = fname.replace(char, "_")

            Path(
                "{}_{}.npy".format(self.output_prefix, fname)
            ).touch(exist_ok=True)

        np.save("{}_{}.npy".format(self.output_prefix, fname), self.cache)
