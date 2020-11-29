from traitlets import Bool, Integer, List, Float, default

from magic_monkey.base.application import MagicMonkeyConfigurable, BoundedInt


_aliases = dict(
    spacing="N4BiasCorrectionConfiguration.spacing"
)

_flags = {
    "rescale": (
        {"N4BiasCorrectionConfiguration": {"rescale": False}},
        "Rescale images to initial magnitude intervals at each iteration"
    )
}


class N4BiasCorrectionConfiguration(MagicMonkeyConfigurable):
    rescale = Bool(False).tag(config=True)
    shrink = Integer(1).tag(config=True)
    iterations = List(
        Integer(), minlen=1, default_value=[50, 50, 50, 50]
    ).tag(config=True)
    threshold = Float(0.01).tag(config=True)
    spline_order = BoundedInt(None, 2, 3, allow_none=True).tag(config=True)
    spacing = List(Float()).tag(config=True, required=True)
    filter_width = Float(0.15).tag(config=True)
    noise = Float(0.01).tag(config=True)
    bins = Integer(200).tag(config=True)

    @default('app_aliases')
    def _app_aliases_default(self):
        return _aliases

    @default('app_flags')
    def _app_flags_default(self):
        return _flags

    def _validate(self):
        pass

    def serialize(self, *args, **kwargs):
        optionals = []
        if self.rescale:
            optionals.append('--rescale-intensities 1')

        if self.spline_order:
            if len(self.spacing) == 1:
                spacing = str(self.spacing[0])
            else:
                spacing = "x".join(
                    str(s * self.spline_order) for s in self.spacing)

            optionals.append(
                "--bspline-fitting [{},{}]".format(spacing, self.spline_order)
            )

        return " ".join([
            "--shrink-factor {}".format(self.shrink),
            "--convergence [{},{}]".format(
                "x".join(str(it) for it in self.iterations), self.threshold
            ),
            "--histogram-sharpening [{},{},{}]".format(
                self.filter_width, self.noise, self.bins
            ),
            "--verbose 1"
        ] + optionals)
