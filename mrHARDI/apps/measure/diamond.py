import time
from copy import copy
from os.path import exists, join
from pathlib import Path

import nibabel as nib
import numpy as np
from traitlets import Bool, Dict, Integer, Unicode
from traitlets.config import ArgumentError
from traitlets.config.loader import ConfigError

from mrHARDI.base.application import (ChoiceEnum,
                                           ChoiceList,
                                           mrHARDIBaseApplication,
                                           output_prefix_argument,
                                           required_file,
                                           required_number)
from mrHARDI.base.config import DiamondConfigLoader

# fmd = fascicle md --check
# fad = fascicle ad --check
# frd = fascicle rd --check
# ffa = fascicle fa --check
# ff = fascicle fractions --check
# peaks = main eigenvectors of each fascicle
from mrHARDI.base.dwi import load_metadata

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
    'mose': 'DiamondMetrics.model_selection',
    'mask': 'DiamondMetrics.mask',
    'in': 'DiamondMetrics.input_prefix',
    'out': 'DiamondMetrics.output_prefix',
    'n': 'DiamondMetrics.n_fascicles',
    'xml-config': 'DiamondMetrics.from_xml'
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

_description = """
Compute metrics over the extracted fascicles from diamond, as well as on the
tensor distribution computed over diamond parameters. The program takes a data 
prefix corresponding to an output from the execution of diamond and produces 
the various metrics found in [1]. A subsample of those metrics can be selected 
via the metrics, magic-metrics and opt-metrics command-line arguments.

References :
------------
[1] Alexis Reymbaut and Maxime Descoteaux. Advanced encoding methods in 
    diffusion MRI. Arxiv, 1908.04177, 2019, https://arxiv.org/abs/1908.04177v3.
"""


class DiamondMetrics(mrHARDIBaseApplication):
    name = u"Diamond Metrics"
    description = _description
    metrics = ChoiceList(
        copy(_DIAMOND_METRICS), DiamondMetricsEnum(), [],
        True, help="Basic diamond metrics to run on the outputs"
    ).tag(config=True)
    mmetrics = ChoiceList(
        copy(_MAGIC_DIAMOND_METRICS), MagicDiamondMetricsEnum(), [], True,
        help="Magic diamond metrics to run on the outputs "
             "(Requires tensor valued input, check your input "
             "prefix to assure it respects convection)"
    ).tag(config=True)
    opt_metrics = ChoiceList(
        copy(_OPTIONAL_METRICS), DiamondOptionalMetricsEnum(), [], True,
        help="Optional diamond metrics to run on the outputs"
    ).tag(config=True)

    input_prefix = required_file(
        description="Prefix of diamond outputs (including mask)"
    )
    output_prefix = output_prefix_argument()
    n_fascicles = required_number(
        Integer, ignore_write=False,
        description="Maximum number of possible fascicles in a voxel"
    )

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

    model_selection = Unicode(
        None, allow_none=True, help="Model selection outputed by Diamond"
    ).tag(config=True)

    mask = Unicode(
        help="Mask image inside of which to compute the metrics. "
             "If not provided, the app will try to find one using "
             "the input prefix provided for the other data."
    ).tag(config=True)

    from_xml = Unicode(
        help="Diamond outputed .xml file from which to "
             "load the metrics generation parameters"
    ).tag(config=True)

    cache = Dict(default_value={})

    aliases = Dict(default_value=_aliases)
    flags = Dict(default_value=_flags)

    def _validate_required(self):
        if self.from_xml:
            DiamondConfigLoader(self).read_config(self.from_xml)

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

    def execute(self):
        import mrHARDI.traits.metrics.diamond as metrics_module

        mask, affine = None, None
        if exists("{}_mask.nii.gz".format(self.input_prefix)):
            mask = nib.load("{}_mask.nii.gz".format(self.input_prefix))
            affine = mask.affine
        elif self.mask and exists(self.mask):
            mask = nib.load(self.mask)
            affine = mask.affine

        metadata = load_metadata(self.input_prefix)
        if metadata is None:
            if affine is None:
                try:
                    img = nib.load("{}_t0.nii.gz".format(self.input_prefix))
                    affine = img.affine
                except Exception:
                    raise ConfigError(
                        "Could not load a file with an affine. Check the "
                        "names of the files in your diamond output path "
                        "and/or provide a metadata file for {}".format(
                            self.input_prefix
                        )
                    )
        else:
            affine = metadata.affine

        if mask is None:
            try:
                img = nib.load("{}_t0.nii.gz".format(self.input_prefix))
                mask = np.ones(img.shape[:3], dtype=bool)
            except Exception:
                raise ConfigError(
                    "Could not load a valid mask to fit data. Either provide "
                    "one using --mask or make one available at : "
                    "{}_mask.nii.gz".format(self.input_prefix)
                )
        else:
            mask = mask.get_fdata().astype(bool)


        for metric in self.metrics + self.mmetrics + self.opt_metrics:
            klass = getattr(
                metrics_module, "{}Metric".format(metric.capitalize())
            )

            klass(
                self.n_fascicles, self.input_prefix,
                self.output_prefix, self.cache, affine,
                mask=mask, shape=mask.shape,
                colors=self.output_colors, with_fw=self.free_water,
                with_res=self.restricted, with_hind=self.hindered,
                mosemap=self.model_selection
            ).measure()

        if self.output_haeberlen:
            self._output_haeberlen(affine)

        if self.save_cache:
            self._save_cache()

    def _output_haeberlen(self, affine):
        from mrHARDI.traits.metrics.diamond import HaeberlenConvention

        mask = None
        if exists("{}_mask.nii.gz".format(self.input_prefix)):
            mask = nib.load("{}_mask.nii.gz".format(self.input_prefix))

        affine = np.loadtxt(affine)

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
        except OSError:
            for char in [" ", ":", ",", ".", "-", "\\", "/", ";"]:
                fname = fname.replace(char, "_")

            Path(
                "{}_{}.npy".format(self.output_prefix, fname)
            ).touch(exist_ok=True)

        np.save("{}_{}.npy".format(self.output_prefix, fname), self.cache)
