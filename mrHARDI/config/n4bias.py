from traitlets import Bool, Integer, List, Float, default

from mrHARDI.base.application import mrHARDIConfigurable, BoundedInt


_aliases = dict(
    seed="N4BiasCorrectionConfiguration.seed"
)

_flags = {
    "rescale": (
        {"N4BiasCorrectionConfiguration": {"rescale": False}},
        "Rescale images to initial magnitude intervals at each iteration"
    )
}


class N4BiasCorrectionConfiguration(mrHARDIConfigurable):
    rescale = Bool(False).tag(config=True)
    shrink = Integer(1).tag(config=True)
    iterations = List(
        Integer(), minlen=1, default_value=[50, 50, 50, 50]
    ).tag(config=True)
    threshold = Float(0.01).tag(config=True)
    spline_order = BoundedInt(None, 2, 3, allow_none=True).tag(config=True)
    knot_distance = Float(8.).tag(config=True, required=True)
    filter_width = Float(0.15).tag(config=True)
    noise = Float(0.01).tag(config=True)
    bins = Integer(200).tag(config=True)
    seed = Integer(None, allow_none=True).tag(config=True)

    @default('app_aliases')
    def _app_aliases_default(self):
        return _aliases

    @default('app_flags')
    def _app_flags_default(self):
        return _flags

    def _validate(self):
        pass

    def serialize(self, voxel_size, *args, **kwargs):
        optionals = []
        if self.rescale:
            optionals.append('--rescale-intensities 1')

        if self.spline_order:
            optionals.append(
                "--bspline-fitting [{},{}]".format(
                    self.knot_distance * voxel_size, self.spline_order
                )
            )

        return " ".join([
            "--shrink-factor {}".format(self.shrink),
            "--convergence [{},{}]".format(
                "x".join(str(it) for it in self.iterations), self.threshold
            ),
            "--histogram-sharpening [{},{},{}]".format(
                self.filter_width * voxel_size, self.noise, self.bins
            ),
            "--verbose 1"
        ] + optionals)
