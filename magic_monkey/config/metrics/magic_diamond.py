from abc import ABCMeta
from os.path import join

import nibabel as nib
from numpy import isclose, mean, zeros, sqrt, array, ones

from magic_monkey.base.application import get_from_metric_cache
from magic_monkey.config.metrics.diamond import DiamondMetric, \
                                                haeberlen_loader, \
                                                MdisoMetric, \
                                                VisoMetric


class MagicDiamondMetric(DiamondMetric, metaclass=ABCMeta):
    def __init__(
        self, n, in_prefix, out_prefix, cache, affine, linear_path,
        spherical_path, planar_path=None, mask=None, shape=None,
        colors=False, with_fw=False, with_res=False, with_hind=False,
        **kwargs
    ):
        super().__init__(
            n, in_prefix, out_prefix, cache, affine, mask,
            shape, colors, with_fw, with_res, with_hind, **kwargs
        )

        self.paths = {
            "lin": linear_path, "sph": spherical_path, "pla": planar_path
        }
        self.cache["lin"] = {}
        self.cache["sph"] = {}
        self.cache["pla"] = {}

    def get_compound_mask(self):
        if self.mask is not None:
            return self.mask

        prefix = self.prefix
        mask = ones(self._get_shape())
        for enc, path in filter(lambda it: it[1], self.paths.items()):
            self.prefix = join(path, prefix)
            try:
                mask &= self.get_mask((enc,))
            except BaseException:
                pass

        self.prefix = prefix
        return mask

    def _get_eigs(self, add_keys=()):
        prefix = self.prefix
        eigs = []
        for enc, path in filter(
            lambda it: it[1], self.paths.values()
        ):
            self.prefix = join(path, prefix)
            eigs.append(super()._get_eigs((enc,)))

        self.prefix = prefix
        return eigs

    def _get_bvecs(self, add_keys=()):
        prefix = self.prefix
        bvecs = []
        for enc, path in filter(
            lambda it: it[1], self.paths.values()
        ):
            self.prefix = join(path, prefix)
            bvecs.append(super()._get_bvecs((enc,)))

        self.prefix = prefix
        return bvecs

    def _get_tensors(self, add_keys=()):
        prefix = self.prefix
        tensors = []
        for enc, path in filter(
            lambda it: it[1], self.paths.values()
        ):
            self.prefix = join(path, prefix)
            tensors.append(super()._get_tensors((enc,)))

        self.prefix = prefix
        return tensors

    def _haeberlen(self, enc, metric):
        prefix = self.prefix
        self.prefix = join(self.paths[enc], prefix)
        lin_daniso = self.load_from_cache(
            (enc, metric), lambda _: haeberlen_loader(
                self, metric, enc
            )
        )

        self.prefix = prefix
        return lin_daniso

    def _sph_2nd_moment(self):
        prefix = self.prefix
        self.prefix = join(self.paths["sph"], prefix)
        sph_2nd_moment = self.load_from_cache(
            ("sph", "viso"), lambda _: get_from_metric_cache(
                ("sph", "viso"), VisoMetric(
                    self.n, self.prefix, self.output,
                    self.cache["sph"], self.get_mask(("sph",)),
                    self.affine
                )
            )
        )

        self.prefix = prefix
        return sph_2nd_moment

    def _lin_2nd_moment(self):
        lin_daniso = self._haeberlen("lin", "daniso")
        sph_2nd_moment = self._sph_2nd_moment()

        return self.load_from_cache(
            ("lin", "2nd_mom"),
            lambda _: 4. / 5. * mean(lin_daniso ** 2., -1) + sph_2nd_moment
        )

    def _build_lin_2nd_moment(self, *_):
        lin_daniso = self._haeberlen("lin", "daniso")
        sph_2nd_moment = self._sph_2nd_moment()
        mask = self._get_fascicles_mask()
        lin_daniso[mask] = lin_daniso[mask] ** 2.
        return 4. / 5. * self._masked_fascicle_mean_metric(
            lin_daniso, axis=-1
        ) + sph_2nd_moment


class UfaMetric(MagicDiamondMetric):
    def measure(self):
        sph_2nd_moment = self._sph_2nd_moment()
        lin_2nd_moment = self._lin_2nd_moment()
        mask = self.get_compound_mask()

        lin_md = self.load_from_cache(
            ("lin", "mdiso"), lambda _: get_from_metric_cache(
                ("lin", "mdiso"), MdisoMetric(
                    self.n, self.prefix, self.output,
                    self.cache["lin"], mask, self.affine
                )
            )
        )

        denom, ufa = zeros(mask.shape), zeros(mask.shape)
        denom[mask] = lin_2nd_moment[mask] - sph_2nd_moment[mask]

        mask &= ~isclose(denom, 0)

        ufa[mask] = sqrt(3. / 2.) * 1. / sqrt(1. + 2. / 5. * (
                lin_md[mask] ** 2. + sph_2nd_moment[mask]
        ) / denom[mask])

        nib.save(
            nib.Nifti1Image(ufa, self.affine),
            "{}_ufa.nii.gz".format(self.output)
        )


class OpMetric(MagicDiamondMetric):
    def measure(self):
        sph_2nd_moment = self._sph_2nd_moment()
        lin_2nd_moment = self._lin_2nd_moment()
        mask = self.get_compound_mask()

        eigs = array(self._get_eigs())
        md_par, md_per = zeros(mask.shape), zeros(mask.shape)
        md_par[mask] = mean(eigs[:, mask, 0, 0], axis=-1)
        md_per[mask] = mean(eigs[:, mask, 0, 1:], axis=-1)

        fa_2nd_moment, denom = zeros(mask.shape), zeros(mask.shape)
        op = zeros(mask.shape)

        denom[mask] = lin_2nd_moment[mask] - sph_2nd_moment[mask]

        mask = mask & ~isclose(denom, 0)

        fa_2nd_moment[mask] = 4. / 45. * (md_par[mask] - md_per[mask]) ** 2.

        op[mask] = sqrt(fa_2nd_moment[mask] / denom[mask])

        nib.save(
            nib.Nifti1Image(op, self.affine),
            "{}_op.nii.gz".format(self.output)
        )


class Mkiso(MagicDiamondMetric):
    def measure(self):
        sph_2nd_moment = self._sph_2nd_moment()
        mask = self.get_compound_mask()

        disos = [
            self._haeberlen(enc, "diso")
            for enc, _ in filter(lambda it: it[1], self.paths)
        ]

        md, mkiso = zeros(mask.shape), zeros(mask.shape)
        md[mask] = self._masked_fascicle_mean_metric(array(disos))[mask]

        mask = mask & ~isclose(md, 0.)
        mkiso[mask] = 2. * sph_2nd_moment[mask] / (md[mask] ** 2.)

        nib.save(
            nib.Nifti1Image(mkiso, self.affine),
            "{}_mkiso.nii.gz".format(self.output)
        )


class Mkaniso(MagicDiamondMetric):
    def measure(self):
        sph_2nd_moment = self._sph_2nd_moment()
        lin_2nd_moment = self._lin_2nd_moment()
        mask = self.get_compound_mask()

        disos = [
            self._haeberlen(enc, "diso")
            for enc, _ in filter(lambda it: it[1], self.paths)
        ]

        md, mkaniso = zeros(mask.shape), zeros(mask.shape)
        md[mask] = self._masked_fascicle_mean_metric(array(disos))[mask]

        mask = mask & ~isclose(md, 0.)
        mkaniso[mask] = 3. * (
                lin_2nd_moment[mask] - sph_2nd_moment[mask]
        ) / (md[mask] ** 2.)

        nib.save(
            nib.Nifti1Image(mkaniso, self.affine),
            "{}_mkaniso.nii.gz".format(self.output)
        )