from traitlets import TraitType, Float, List, Integer, default, Unicode

from magic_monkey.base.application import SelfInstantiatingInstance


class InitialTransform(TraitType):
    def get(self, obj, cls=None):
        value = super().get(obj, cls)

        if value is None:
            return ""

        target_index, moving_index, strat = value
        return "--initial-moving-transform [$t{}%,$m{}%,{}]".format(
            target_index, moving_index, strat
        ).replace("$", "{").replace("%", "}")

    def validate(self, obj, value):
        if isinstance(value, tuple):
            if len(value) == 3:
                t, m, strat = value
                if isinstance(t, int) and isinstance(m, int):
                    if isinstance(strat, int) and (0 <= strat <= 2):
                        return value

        if value is not None:
            self.error(obj, value)


class AntsMetric(TraitType):
    name = ""

    def get(self, obj, cls=None):
        value = super().get(obj, cls)
        target_index, moving_index = value[:2]
        return self.name + "[$t{}%,$m{}%".format(
            target_index, moving_index
        ).replace("$", "{").replace("%", "}") + ",".join(
            str(v) for v in value[2:]
        ) + "]"


class MetricMI(AntsMetric):
    name = "MI"
    default_value = (0, 0, 1, 32, "Regular", 0.25)

    def validate(self, obj, value):
        if isinstance(value, tuple):
            if len(value) == 6:
                t, m, weight, bins, sampling, sampling_percentage = value
                if isinstance(t, int) and isinstance(m, int):
                    if isinstance(weight, int) and isinstance(bins, int):
                        if isinstance(sampling, str):
                            if isinstance(sampling_percentage, float):
                                return value

        self.error(obj, value)


class MetricCC(AntsMetric):
    name = "CC"
    default_value = (0, 0, 1, 4)

    def validate(self, obj, value):
        if isinstance(value, tuple):
            if len(value) == 4:
                t, m, weight, radius = value
                if isinstance(weight, int) and isinstance(radius, int):
                    return value

        self.error(obj, value)


class AntsPass(SelfInstantiatingInstance):
    grad_step = Float(0.1).tag(config=True)
    metrics = List(AntsMetric).tag(config=True)
    conv_eps = Float(1E-6).tag(config=True)
    conv_win = Integer(10).tag(config=True)
    conv_max_iter = List(Integer).tag(config=True)
    shrinks = List(Integer, [8, 4, 2, 1]).tag(config=True)
    smoothing = List(Integer, [3, 2, 1, 0]).tag(config=True)

    def serialize(self):
        return " ".join([
            " ".join(
                "--metric {}".format(metric)
                for i, metric in enumerate(self.metrics)
            ),
            "--convergence [{},{},{}] ".format(
                "x".join(str(i) for i in self.conv_max_iter),
                self.conv_eps,
                self.conv_win
            ),
            "--shrink-factors {} ".format(
                "x".join(str(s) for s in self.shrinks)
            ),
            "--smoothing-sigmas {}vox".format(
                "x".join(str(s) for s in self.smoothing)
            )
        ])


class AntsRigid(AntsPass):
    @default("metrics")
    def _metrics_default(self):
        return [MetricMI()]

    def serialize(self):
        return " ".join([
            "--transform Rigid[{}] ".format(self.grad_step),
            super().serialize()
        ])


class AntsAffine(AntsPass):
    @default("metrics")
    def _metrics_default(self):
        return [MetricMI()]

    def serialize(self):
        return " ".join([
            "--transform Affine[{}] ".format(self.grad_step),
            super().serialize()
        ])


class AntsSyN(AntsPass):
    type = Unicode(u'SyN').tag(config=True)
    var_penality = Integer(3).tag(config=True)
    var_total = Integer(0).tag(config=True)

    @default("metrics")
    def _metrics_default(self):
        return [MetricCC()]

    def serialize(self):
        return " ".join([
            "--transform {}[{},{},{}] ".format(
                self.type, self.grad_step, self.var_penality, self.var_total
            ),
            super().serialize()
        ])
