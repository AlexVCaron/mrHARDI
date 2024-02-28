from abc import abstractmethod
from copy import deepcopy

import numpy as np
from traitlets import Float, Integer, List, TraitType, Unicode, default
from traitlets.config.loader import ConfigError

from mrHARDI.base.ListValuedDict import MagicDict
from mrHARDI.base.application import (DictInstantiatingInstance,
                                      mrHARDIConfigurable)


class InitialTransform(TraitType):
    default_value = None
    transform_type = "moving"

    def get(self, obj, cls=None):
        value = super().get(obj, cls)

        if self.get_metadata("bypass", False):
            return value

        if value is None:
            return None

        if isinstance(value, str):
            return "--initial-{}-transform {}".format(self.transform_type, value)

        target_index, moving_index, strat = value
        return "--initial-{}-transform [$t{}%,$m{}%,{}]".format(
            self.transform_type, target_index, moving_index, strat
        ).replace("$", "{").replace("%", "}")

    def invert(self):
        if self.transform_type == "moving":
            self.transform_type = "fixed"
        else:
            self.transform_type = "moving"

        return self

    def validate(self, obj, value):
        if isinstance(value, str):
            if "--initial-{}-transform".format(self.transform_type) in value:
                return value

            return "--initial-{}-transform {}".format(self.transform_type, value)
        if isinstance(value, (tuple, list)):
            if len(value) == 3:
                t, m, strat = value
                if isinstance(t, int) and isinstance(m, int):
                    if isinstance(strat, int) and (0 <= strat <= 2):
                        return "--initial-{}-transform [$t{}%,$m{}%,{}]".format(
                            self.transform_type, t, m, strat
                        ).replace("$", "{").replace("%", "}")

        if value is not None:
            self.error(obj, value)


class AntsMetric(MagicDict):
    def __init__(self, target_index, moving_index, args=(), **_):
        super().__init__(dict(
            target_index=target_index,
            moving_index=moving_index,
            args=args, klass=".".join(
                [self.__module__, self.__class__.__name__]
            )
        ))

        self._name = ""

    def serialize(self):
        values = deepcopy(self._dict)
        args = values.pop("args")
        return self._name + "[$t{target_index}%,$m{moving_index}%,".format(
            **values
        ).replace("$", "{").replace("%", "}") + ",".join(
            str(v) for v in args
        ) + "]"

    def __repr__(self):
        return self.serialize()

    def __str__(self):
        return repr(self)


class MetricMattes(AntsMetric):
    def __init__(
        self, target_index, moving_index, weight=1.,
        bins=32, sampling="Regular", sampling_p=0.25,
        grad_filtering=False, args=None, **_
    ):
        if args and len(args) == 3:
            bins, sampling, sampling_p = args
            values = (bins, sampling, sampling_p)
        elif args and len(args) == 4:
            weight, bins, sampling, sampling_p = args
            values = (weight, bins, sampling, sampling_p)
        elif args and len(args) == 5:
            weight, bins, sampling, sampling_p, grad_filtering = args
            values = (weight, bins, sampling, sampling_p, int(grad_filtering))

        super().__init__(
            target_index, moving_index, values
        )

        self._name = "Mattes"

    def for_ants_ai(self):
        attrs = self.copy_attributes()
        target, moving = attrs.pop("target_index"), attrs.pop("moving_index")
        args = attrs.pop("args")

        if len(args) == 3:
            bins, sampling, sampling_p = args
        elif len(args) == 4:
            _, bins, sampling, sampling_p = args
        elif len(args) == 5:
            _, bins, sampling, sampling_p, _ = args

        return MetricMI(
            target, moving, args=(bins // 2, sampling, sampling_p / 2), **attrs)


class MetricMI(AntsMetric):
    def __init__(
        self, target_index, moving_index, weight=1.,
        bins=32, sampling="Regular", sampling_p=0.25,
        grad_filtering=False, args=None, **_
    ):
        if args and len(args) == 3:
            bins, sampling, sampling_p = args
            values = (bins, sampling, sampling_p)
        elif args and len(args) == 4:
            weight, bins, sampling, sampling_p = args
            values = (weight, bins, sampling, sampling_p)
        elif args and len(args) == 5:
            weight, bins, sampling, sampling_p, grad_filtering = args
            values = (weight, bins, sampling, sampling_p, int(grad_filtering))

        super().__init__(
            target_index, moving_index, values
        )

        self._name = "MI"

    def for_ants_ai(self):
        attrs = self.copy_attributes()
        target, moving = attrs.pop("target_index"), attrs.pop("moving_index")
        args = attrs.pop("args")

        if len(args) == 3:
            bins, sampling, sampling_p = args
        elif len(args) == 4:
            _, bins, sampling, sampling_p = args
        elif len(args) == 5:
            _, bins, sampling, sampling_p, _ = args

        return MetricMI(
            target, moving, args=(bins // 2, sampling, sampling_p / 2), **attrs)

class MetricCC(AntsMetric):
    def __init__(
        self, target_index, moving_index, weight=1., radius=4, 
        sampling="Regular", sampling_p=0.25, args=None, **_
    ):
        if args and len(args) == 3:
            radius, sampling, sampling_p = args
            values = (radius, sampling, sampling_p)
        if args and len(args) == 4:
            weight, radius, sampling, sampling_p = args
            values = (weight, radius, sampling, sampling_p)

        super().__init__(
            target_index, moving_index, values
        )

        self._name = "CC"

    def for_ants_ai(self):
        attrs = self.copy_attributes()
        target, moving = attrs.pop("target_index"), attrs.pop("moving_index")
        args = attrs.pop("args")

        if len(args) == 3:
            radius, sampling, sampling_p = args
        elif len(args) == 4:
            _, radius, sampling, sampling_p = args

        return MetricMI(
            target, moving, args=(radius, sampling, sampling_p), **attrs)

class AntsPass(mrHARDIConfigurable):
    def __init__(self, is_motion_correction=False, name_dict=None, **kwargs):
        super().__init__(**kwargs)
        self._metrics_opts_names = name_dict
        self._is_motion_corr = is_motion_correction
        self._conv_fmt = self.ants_registration_conv_formatter
        if is_motion_correction:
            classes = (self.__class__,) + self.__class__.__bases__
            for klass in classes:
                try:
                    delattr(klass, "conv_eps")
                    delattr(klass, "conv_win")
                except AttributeError:
                    pass

            self._conv_fmt = self.ants_motion_corr_iter_formatter

    def _validate(self):
        if not (
            len(self.shrinks) == len(self.smoothing) == len(self.conv_max_iter)
        ):
            raise ConfigError(
                "For an ants pass to be valid, shrink factors, smoothing "
                "factors and maximum of iterations must all be lists of same "
                "length. Received :\n"
                "   {} shrinks  {} smoothings  {} max iter".format(
                    len(self.shrinks),
                    len(self.smoothing),
                    len(self.conv_max_iter)
                )
            )

    grad_step = Float(0.1).tag(config=True)
    metrics = List(
        DictInstantiatingInstance(klass=AntsMetric)
    ).tag(config=True)
    conv_eps = Float(1E-6).tag(config=True)
    conv_win = Integer(10).tag(config=True)
    conv_max_iter = List(Integer()).tag(config=True)
    shrinks = List(Integer(), [8, 4, 2, 1]).tag(config=True)
    smoothing = List(Float(), [3, 2, 1, 0]).tag(config=True)

    @abstractmethod
    def get_time_restriction(self, ndim):
        pass

    def ants_registration_conv_formatter(self, for_ants_ai=False):
        max_iters = "x".join(str(i) for i in self.conv_max_iter)
        if for_ants_ai:
            max_iters = "{}".format(
                max(self.conv_max_iter[0] // 4, self.conv_win)
            ) 
        return "--convergence [{},{},{}]".format(
            max_iters,
            self.conv_eps,
            self.conv_win
        )

    def ants_motion_corr_iter_formatter(self):
        return "--iterations {}".format(
            "x".join(str(i) for i in self.conv_max_iter)
        )

    def serialize(self, voxel_size, with_convergence=True, for_ants_ai=False):
        if for_ants_ai:
            return " ".join([
                " ".join(
                    "--metric {}".format(metric.for_ants_ai())
                    for i, metric in enumerate(self.metrics)
                ),
                self._conv_fmt(for_ants_ai)
            ]).replace("MI", "Mattes")

        return " ".join([
            " ".join(
                "--metric {}".format(metric)
                for i, metric in enumerate(self.metrics)
            ),
            self._conv_fmt(),
            "--{} {}".format(
                self._metrics_opts_names["shrink"],
                "x".join(str(s) for s in self.shrinks)
            ),
            "--{} {}{}".format(
                self._metrics_opts_names["smooth"],
                "x".join(str(voxel_size * s) for s in self.smoothing),
                "" if self._is_motion_corr else "mm"
            )
        ])


class AntsRigid(AntsPass):
    def get_time_restriction(self, ndim):
        return "x".join(
            ["1" for _ in range(ndim - 1)] + ["0"] +
            ["1" for _ in range(ndim - 1)] + ["0"]
        )

    name = "Rigid"

    @default("metrics")
    def _metrics_default(self):
        return [MetricMI(0, 0)]

    def serialize(self, voxel_size, with_convergence=True, for_ants_ai=False):
        return " ".join([
            "--transform Rigid[{}]".format(self.grad_step),
            super().serialize(voxel_size, with_convergence, for_ants_ai)
        ])


class AntsAffine(AntsPass):
    def get_time_restriction(self, ndim):
        mat = np.ones((ndim, ndim), dtype=int)
        mat[:, ndim - 1] = 0
        mat[-1, :] = 0
        trans = list("1" for _ in range(ndim - 1)) + ["0"]
        return "x".join(list(mat.astype(str).flatten().tolist()) + trans)

    name = "Affine"

    @default("metrics")
    def _metrics_default(self):
        return [MetricMI(0, 0)]

    def serialize(self, voxel_size, with_convergence=True, for_ants_ai=False):
        return " ".join([
            "--transform Affine[{}]".format(self.grad_step),
            super().serialize(voxel_size, with_convergence, for_ants_ai)
        ])


class AntsSyN(AntsPass):
    def get_time_restriction(self, ndim):
        return "x".join(["1" for _ in range(ndim - 1)] + ["0"])

    type = Unicode(u'SyN').tag(config=True)
    var_penality = Integer(3).tag(config=True)
    var_total = Integer(0).tag(config=True)
    name = "SyN"

    @default("metrics")
    def _metrics_default(self):
        return [MetricCC(0, 0)]

    def serialize(self, voxel_size, with_convergence=True, for_ants_ai=False):
        return " ".join([
            "--transform {}[{},{},{}]".format(
                self.type, self.grad_step, self.var_penality, self.var_total
            ),
            super().serialize(voxel_size, with_convergence, for_ants_ai)
        ])
