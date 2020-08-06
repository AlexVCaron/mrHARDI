from os.path import join
from shutil import copyfile

import nibabel as nib

from abc import ABCMeta

from numpy import moveaxis, mean, trace, diag, eye, isclose, \
    sqrt, sum, prod, roll, cbrt, ones, einsum, array, \
    apply_along_axis, absolute, count_nonzero, float32, repeat, ubyte
from numpy.core._multiarray_umath import zeros

from numpy.ma import array as masked

from magic_monkey.base.application import load_from_cache, \
                                          get_from_metric_cache, \
                                          BaseMetric

from magic_monkey.config.metrics.dti import compute_md, \
    compute_ad, \
    compute_rd, \
    compute_fa, \
    vec_to_tens, compute_eigenvalues


class DiamondMetric(BaseMetric, metaclass=ABCMeta):
    def __init__(
        self, n, in_prefix, out_prefix, cache, affine,
        mask=None, shape=None, colors=False, with_fw=False,
        with_res=False, with_hind=False, **kwargs
    ):
        super().__init__(
            in_prefix, out_prefix, cache, affine, mask, shape, colors
        )
        self.n = n
        self.fw = with_fw
        self.res = with_res
        self.hin = with_hind

    def _fascicles_fraction_chunk(self):
        back_idx = 1 if self.fw else 0
        return slice(0, -back_idx)

    def _color(self, name, evecs=None, add_keys=()):
        super()._color(name, evecs, add_keys)

    def _get_eigs(self, add_keys=()):
        return get_eigs(
            ["t{}".format(i) for i in range(self.n)],
            [self._get_fascicle_mask(i, add_keys) for i in range(self.n)],
            self.cache,
            lambda f: nib.load(
                "{}_{}.nii.gz".format(self.prefix, f)
            ).get_fdata().squeeze(),
            add_keys
        )

    def _get_tensors(self, add_keys=()):
        return [load_from_cache(
            self.cache,
            add_keys + ("t{}".format(i),),
            lambda f: nib.load(
                "{}_{}.nii.gz".format(self.prefix, f)
            ).get_fdata().squeeze()
        ) for i in range(self.n)]

    def _weighted(self, volumes, alt_w=None, add_keys=(), mask=None, axis=0):
        if alt_w is None:
            alt_w = self._get_fascicle_fractions(add_keys)

        if axis == 0:
            idx = 'l...'
        elif axis == -1 or axis == len(volumes.shape) - 1:
            idx = '...l'
        else:
            raise RuntimeError(
                "Weighted means must be done on first or last axis for now"
            )

        if mask is not None:
            mask = moveaxis(mask, axis, -1)
            alt_w *= mask

        if not len(alt_w.shape) == len(volumes.shape):
            rep_axis = 0 if axis else -1
            alt_w = alt_w[..., None, :] if rep_axis else alt_w[None, ...]
            alt_w = repeat(
                alt_w, volumes.shape[rep_axis], -2 if rep_axis else 0
            )
        elif any(
            not ash == vsh for ash, vsh in zip(
                roll(alt_w.shape, 1), volumes.shape
            )
        ):
            rep_axis = -1 if not alt_w.shape[0] == volumes.shape[-1] else 0
            alt_w = repeat(alt_w, volumes.shape[rep_axis], rep_axis)

        return einsum('...l,{}'.format(idx), alt_w, volumes)

    def _weight_over_tensors(self, metric, prepare=lambda wm: wm):
        if self.n == 1:
            copyfile(
                "{}_t0_{}.nii.gz".format(self.output, metric),
                "{}_{}.nii.gz".format(self.output, metric)
            )

        elif self.n > 0:
            w_metric = self._weighted(array([
                self.cache["t{}_{}".format(i, metric)] for i in range(self.n)
            ]))
            nib.save(
                nib.Nifti1Image(prepare(w_metric), self.affine),
                "{}_{}.nii.gz".format(self.output, metric)
            )

    def _get_model_selection(self, add_keys=()):
        return self.load_from_cache(
            add_keys + ("mosemap",),
            lambda _: nib.load(
                "{}_mosemap.nii.gz".format(self.prefix)
            ).get_fdata()
        )

    def _get_fascicle_mask(self, i, add_keys=()):
        mosemap = self._get_model_selection(add_keys)
        return self.load_from_cache(
            add_keys + ("t{}_f_mask".format(i),),
            lambda _: self.get_mask(add_keys) & (mosemap > i)
        )

    def _get_fascicle_fractions(self, add_keys=()):
        fractions = self._get_fractions(add_keys)

        return fractions[..., :-1 if self.fw else 0]

    def _get_fractions(self, add_keys=()):
        fractions = self.load_from_cache(
            add_keys + ("fractions",), lambda _: nib.load(
                "{}_fractions.nii.gz".format(self.prefix)
            ).get_fdata().squeeze()
        )
        return fractions

    def _get_fascicles_mask(self):
        return array([self._get_fascicle_mask(i) for i in range(self.n)])

    def _masked_fascicle_mean_metric(self, metrics, last_dims=(), axis=0):
        mask = self.get_mask()
        f_mask = self._get_fascicles_mask()
        if not axis == 0:
            f_mask = moveaxis(f_mask, 0, axis)
        metric = zeros(self._get_shape() + last_dims)
        metric[mask] = self._weighted(metrics, mask=f_mask, axis=axis)[mask]
        return metric

    def _masked_fascicle_mean_functional(self, metrics, fn, last_dims=()):
        mask = self.get_mask()
        f_mask = self._get_fascicles_mask()
        metric = zeros(self._get_shape() + last_dims)
        metric[mask] = fn(masked(metrics, mask=~f_mask), mask)
        return metric

    def _color_metric(self, name, evecs=None, add_keys=(), **kwargs):
        evecs = [e[1] for e in self._get_eigs()] if evecs is None else evecs
        for i, evec in enumerate(evecs):
            super()._color_metric(name, evec, add_keys, "t{}".format(i))

        self._weight_over_tensors(
            "color_{}".format(name),
            lambda wm: (absolute(wm) * 255.).astype(ubyte)
        )


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


class FmdMetric(DiamondMetric):
    def measure(self):
        for i, eig_set in enumerate(self._get_eigs()):
            img = compute_md(eig_set, self._get_fascicle_mask(i))
            self.cache["t{}_md".format(i)] = img

            nib.save(
                nib.Nifti1Image(img, self.affine),
                "{}_t{}_md.nii.gz".format(self.output, i)
            )

        self._weight_over_tensors("md")


class FadMetric(DiamondMetric):
    def measure(self):
        for i, eig_set in enumerate(self._get_eigs()):
            img = compute_ad(eig_set, self._get_fascicle_mask(i))
            self.cache["t{}_ad".format(i)] = img

            nib.save(
                nib.Nifti1Image(img, self.affine),
                "{}_t{}_ad.nii.gz".format(self.output, i)
            )

        self._weight_over_tensors("ad")


class FrdMetric(DiamondMetric):
    def measure(self):
        for i, eig_set in enumerate(self._get_eigs()):
            img = compute_rd(eig_set, self._get_fascicle_mask(i))
            self.cache["t{}_rd".format(i)] = img

            nib.save(
                nib.Nifti1Image(img, self.affine),
                "{}_t{}_rd.nii.gz".format(self.output, i)
            )

        self._weight_over_tensors("rd")


class FfaMetric(DiamondMetric):
    def measure(self):
        for i, eig_set in enumerate(self._get_eigs()):
            img = compute_fa(eig_set, self._get_fascicle_mask(i))
            self.cache["t{}_fa".format(i)] = img

            nib.save(
                nib.Nifti1Image(img, self.affine),
                "{}_t{}_fa.nii.gz".format(self.output, i)
            )

        self._weight_over_tensors("fa")
        self._color("fa")


class FfMetric(DiamondMetric):
    def measure(self):
        fractions = self._get_fascicle_fractions()

        for i, fraction in enumerate(moveaxis(fractions, -1, 0)):
            nib.save(
                nib.Nifti1Image(fraction, self.affine),
                "{}_t{}_fraction.nii.gz".format(self.output, i)
            )

        img = nib.load("{}_fractions.nii.gz".format(self.prefix))
        nib.save(
            nib.Nifti1Image(img.get_fdata(), self.affine),
            "{}_fractions.nii.gz".format(self.output)
        )


class RfMetric(DiamondMetric):
    def measure(self):
        if self.res:
            fraction = self.load_from_cache(
                "rf", lambda _: nib.load(
                    "{}_isotropic2Fraction.nii.gz".format(self.prefix)
                ).get_fdata()
            )

            nib.save(
                nib.Nifti1Image(fraction, self.affine),
                "{}_restricted_fraction.nii.gz".format(self.output)
            )


class HfMetric(DiamondMetric):
    def measure(self):
        if self.hin:
            if any(
                "t{}_hf".format(i) not in self.cache for i in range(self.n)
            ):
                fractions = nib.load("{}_icvf.nii.gz".format(self.prefix))
                for i, fraction in enumerate(
                    moveaxis(fractions.get_fdata(), -1, 0)
                ):
                    self.cache["t{}_hf".format(i)] = fraction.squeeze()
                    nib.save(
                        nib.Nifti1Image(fraction.squeeze(), self.affine),
                        "{}_t{}_hindered_fraction.nii.gz".format(
                            self.output, i
                        )
                    )


class WfMetric(DiamondMetric):
    def measure(self):
        if self.fw:
            fractions = self._get_fractions()

            nib.save(
                nib.Nifti1Image(fractions[..., -1], self.affine),
                "{}_fFW.nii.gz".format(self.output)
            )


class PeaksMetric(DiamondMetric):
    def measure(self):
        if "peaks" in self.cache:
            peaks = self.cache["peaks"]
        else:
            eigs = array([e[1] for e in self._get_eigs()])

            n = self.n if self.n <= 5 else 5

            peaks = zeros((5,) + self._get_shape() + (3,))
            f_mask = self._get_fascicles_mask()
            in_mask_vox = count_nonzero(f_mask[:n])

            peaks[:n][f_mask] = eigs[f_mask[:n], 0, :].swapaxes(
                0, 1
            ).reshape((in_mask_vox, -1))

            weights = self._get_fascicle_fractions()
            peaks[:n] = moveaxis(weights, -1, 0)[..., None] * peaks[:n]

            peaks = moveaxis(peaks, 0, -2).reshape(
                self._get_shape() + (-1,)
            ).astype(float32)

            self.cache["peaks"] = peaks

        nib.save(
            nib.Nifti1Image(peaks, self.affine),
            "{}_peaks.nii.gz".format(self.output)
        )


def compute_haeberlen(tensors, mask):
    diso, daniso = zeros(mask.shape), zeros(mask.shape)
    ddelta, deta = zeros(mask.shape), zeros(mask.shape)

    tensors = apply_along_axis(
        vec_to_tens, 1, tensors.reshape((-1, 6))
    ).reshape(mask.shape + (3, 3))

    diso[mask] = trace(tensors[mask], axis1=-2, axis2=-1) / 3.
    daniso[mask] = trace(
        (tensors - diso[..., None, None])[mask] @ diag([-1., -1., 0.5]),
        axis1=-2, axis2=-1
    ) / 3.

    mask &= ~isclose(diso, 0.)

    ddelta[mask] = daniso[mask] / diso[mask]

    mask &= ~isclose(ddelta, 0.)

    deta[mask] = trace(
        (
            (
                tensors[mask] / diso[mask, None, None] - eye(3)
            ) / ddelta[mask, None, None] - diag([-1, -1, 2])
        )[..., :-1, :-1] @ diag([-1, 1]),
        axis1=-2, axis2=-1
    ) / 2.

    return diso, daniso, ddelta, deta


class HaeberlenConvention(DiamondMetric):
    def measure(self):
        tensors = self._get_tensors()

        for i, tensor_set in enumerate(tensors):
            if not "t{}_diso".format(i) in self.cache:
                diso, daniso, ddelta, deta = compute_haeberlen(
                    tensor_set, self._get_fascicle_mask(i)
                )

                self.cache["t{}_diso".format(i)] = diso
                self.cache["t{}_daniso".format(i)] = daniso
                self.cache["t{}_ddelta".format(i)] = ddelta
                self.cache["t{}_deta".format(i)] = deta


def haeberlen_loader(base_obj, metric, sub_cache=None):
    def _load_data(keys):
        return get_from_metric_cache(keys, HaeberlenConvention(
            base_obj.n, base_obj.prefix, base_obj.output, base_obj.cache,
            base_obj.affine, base_obj.mask, base_obj.shape,
            base_obj.fw, base_obj.res
        ))

    sub_cache = base_obj.cache[sub_cache] if sub_cache else base_obj.cache
    return array([load_from_cache(
        sub_cache, "t{}_{}".format(i, metric), lambda keys: _load_data([keys])
    ) for i in range(base_obj.n)])


class DisoMetric(DiamondMetric):
    def measure(self):
        for i, diso in enumerate(haeberlen_loader(self, "diso")):
            nib.save(
                nib.Nifti1Image(diso, self.affine),
                "{}_t{}_diso.nii.gz".format(self.output, i)
            )


class DanisoMetric(DiamondMetric):
    def measure(self):
        for i, diso in enumerate(haeberlen_loader(self, "daniso")):
            nib.save(
                nib.Nifti1Image(diso, self.affine),
                "{}_t{}_daniso.nii.gz".format(self.output, i)
            )


class MdisoMetric(DiamondMetric):
    def measure(self):
        disos = haeberlen_loader(self, "diso")

        mdiso = self._masked_fascicle_mean_metric(disos)
        self.cache["mdiso"] = mdiso

        nib.save(
            nib.Nifti1Image(mdiso, self.affine),
            "{}_mdiso.nii.gz".format(self.output)
        )


class MdanisoMetric(DiamondMetric):
    def measure(self):
        danisos = haeberlen_loader(self, "daniso")

        mda = self._masked_fascicle_mean_metric(danisos)

        nib.save(
            nib.Nifti1Image(mda, self.affine),
            "{}_mdaniso.nii.gz".format(self.output)
        )


class SraMetric(DiamondMetric):
    def measure(self):
        eigs = self._get_eigs()
        disos = haeberlen_loader(self, "diso")
        for i, (eig, diso) in enumerate(zip(eigs, disos)):
            evals, evecs = eig
            mask = self._get_fascicle_mask(i) & ~isclose(diso, 0.)
            sra = zeros(mask.shape)

            sra[mask] = 1. / diso[mask] * sqrt(
                sum((evals - diso[..., None]) ** 2.) / 6.
            )

            nib.save(
                nib.Nifti1Image(sra, self.affine),
                "{}_t{}_sra.nii.gz".format(self.output, i)
            )


class VfMetric(DiamondMetric):
    def measure(self):
        eigs = self._get_eigs()
        disos = haeberlen_loader(self, "diso")
        for i, (eig, diso) in enumerate(zip(eigs, disos)):
            evals, evecs = eig
            mask = self._get_fascicle_mask(i) & ~isclose(diso, 0.)
            vf = zeros(mask.shape)

            vf[mask] = 1. - prod(evals[mask], 1) / (diso[mask] ** 3.)

            nib.save(
                nib.Nifti1Image(vf, self.affine),
                "{}_t{}_vf.nii.gz".format(self.output, i)
            )


class UaMetric(DiamondMetric):
    def measure(self):
        eigs = self._get_eigs()
        disos = haeberlen_loader(self, "diso")
        for i, (eig, diso) in enumerate(zip(eigs, disos)):
            evals, evecs = eig
            mask = self._get_fascicle_mask(i) & ~isclose(diso, 0.)

            uas, uav = zeros(mask.shape), zeros(mask.shape)
            uavs = zeros(mask.shape)

            sq3_evals = sqrt(absolute(einsum(
                "...l,...l", evals[mask], roll(evals[mask], -1, 1)
            ) / 3.))
            cbp_evals = cbrt(prod(evals[mask], 1))

            uas[mask] = 1. - 1. / (diso[mask] ** 2.) * sq3_evals
            uav[mask] = 1. - cbp_evals / diso[mask]

            mask2 = ~isclose(sq3_evals, 0.)
            mask[mask] &= mask2
            uavs[mask] = 1. - cbp_evals[mask2] / sq3_evals[mask2]

            nib.save(
                nib.Nifti1Image(uas, self.affine),
                "{}_t{}_uas.nii.gz".format(self.output, i)
            )

            nib.save(
                nib.Nifti1Image(uav, self.affine),
                "{}_t{}_uav.nii.gz".format(self.output, i)
            )

            nib.save(
                nib.Nifti1Image(uavs, self.affine),
                "{}_t{}_uavs.nii.gz".format(self.output, i)
            )


class VisoMetric(DiamondMetric):
    def measure(self):
        disos = haeberlen_loader(self, "diso")
        mdiso = self.load_from_cache("mdiso", lambda _: get_from_metric_cache(
            ("mdiso",), MdisoMetric(
                self.n, self.prefix, self.output, self.cache,
                self.affine, self.mask, self.shape, self.fw, self.res
            )
        ))

        viso = self._masked_fascicle_mean_functional(
            disos,
            lambda a, mask: self._weighted(a ** 2.)[mask] - mdiso[mask] ** 2.
        )

        nib.save(
            nib.Nifti1Image(viso, self.affine),
            "{}_viso.nii.gz".format(self.output)
        )


class VeigMetric(DiamondMetric):
    def measure(self):
        danisos = haeberlen_loader(self, "daniso")

        veig = self._masked_fascicle_mean_functional(
            danisos, lambda arr, mask: 2. * self._weighted(arr ** 2.)[mask]
        )

        nib.save(
            nib.Nifti1Image(veig, self.affine),
            "{}_veig.nii.gz".format(self.output)
        )


class VdeltaMetric(DiamondMetric):
    def measure(self):
        danisos = haeberlen_loader(self, "daniso")
        mask = self._get_fascicles_mask()

        danisos[mask] = danisos[mask] ** 2.

        vdelta = self._masked_fascicle_mean_functional(
            danisos, lambda arr, m: 4. * (
                self._weighted(arr ** 2.)[m] - self._weighted(arr)[m] ** 2.
            )
        )

        nib.save(
            nib.Nifti1Image(vdelta, self.affine),
            "{}_vdelta.nii.gz".format(self.output)
        )


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


def get_eigs(fascicles, mask, cache, alternative=None, add_keys=()):
    f_eigs = []
    for i, fascicle in enumerate(fascicles):
        eigs = load_from_cache(
            cache, add_keys + ("eigs_{}".format(fascicle),)
        )
        if eigs:
            f_eigs.append(eigs)
            continue

        f = load_from_cache(cache, add_keys + (fascicle,), alternative)
        if isinstance(mask, list):
            f_mask = mask[i]
        else:
            f_mask = mask

        eigs = compute_eigenvalues(f, f_mask)
        sub_cache = cache
        for key in add_keys:
            sub_cache = sub_cache[key]

        sub_cache["eigs_{}".format(fascicle)] = eigs
        f_eigs.append(eigs)

    return f_eigs
