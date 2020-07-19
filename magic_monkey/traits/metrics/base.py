from abc import abstractmethod
from typing import Generator

import nibabel as nib
from numpy import loadtxt, ones, ubyte, absolute, zeros


def load_from_cache(cache, keys, alternative=None):
    keys = keys if isinstance(keys, (list, tuple, Generator)) else [keys]
    sub_cache = cache
    try:
        for key in keys:
            sub_cache = sub_cache[key]
        return sub_cache
    except KeyError as e:
        if alternative:
            sub_cache[e.args[0]] = alternative(e.args[0])
            sub_cache = sub_cache[e.args[0]]
        else:
            return None

    return sub_cache


def get_from_metric_cache(keys, metric):
    metric.measure()
    cache = metric.cache
    for key in keys:
        cache = cache[key]
    return cache


def _load_mask(path, shape):
    try:
        return nib.load(path).get_fdata().astype(bool)
    except FileNotFoundError:
        return ones(shape)


class BaseMetric:
    def __init__(
        self, prefix, output, cache, affine, mask=None,
        shape=None, colors=False, **kwargs
    ):
        self.prefix = prefix
        self.output = output
        self.cache = cache
        self.affine = affine
        self.mask = mask
        self.shape = shape
        self.colors = colors

    def load_from_cache(self, key, alternative=None):
        return load_from_cache(self.cache, key, alternative)

    def _get_shape(self):
        return self.shape

    def get_mask(self, add_keys=()):
        if self.mask is not None:
            return self.mask

        return self.load_from_cache(
            add_keys + ("mask",),
            lambda _: _load_mask(
                "{}_mask.nii.gz".format(self.prefix), self._get_shape()
            )
        )

    def _get_bvecs(self, add_keys=()):
        return load_from_cache(
            self.cache,
            add_keys + ("bvecs",),
            lambda f: loadtxt("{}.bvecs".format(self.prefix))
        )

    def _get_bvals(self, add_keys=()):
        return load_from_cache(
            self.cache,
            add_keys + ("bvals",),
            lambda f: loadtxt("{}.bvals".format(self.prefix))
        )

    def _color(self, name, evecs, add_keys=()):
        if self.colors:
            self._color_metric(name, evecs, add_keys)

    def _color_metric(self, name, evecs, add_keys=(), prefix=""):
        cname = "color_{}".format(name)
        if prefix:
            cname = "_".join([prefix, cname])
            name = "_".join([prefix, name])

        mask = self.get_mask()
        metric = self.load_from_cache(add_keys + (name,))
        cmetric = zeros(self._get_shape() + (3,))

        cmetric[mask] = absolute(metric[mask, None] * evecs[mask, 0, :])
        self.cache[cname] = cmetric

        nib.save(
            nib.Nifti1Image(
                (cmetric * 255.).astype(ubyte),
                self.affine
            ),
            "{}_{}.nii.gz".format(self.output, cname)
        )

    @abstractmethod
    def measure(self):
        pass