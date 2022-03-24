from traitlets import Bool, Integer, default

from magic_monkey.base.application import MagicMonkeyConfigurable

_flags = dict(
    lsqr=(
        {'DTIConfiguration': {'use_lsqr': True}}, "Use least-square error"
    ),
    prediction=(
        {'DTIConfiguration': {'predicted_signal': True}},
        "Output the reconstructed diffusion volume refined by the optimizer"
    )
)


class DTIConfiguration(MagicMonkeyConfigurable):
    use_lsqr = Bool(False).tag(config=True)
    reweight_iter = Integer(2).tag(config=True)
    predicted_signal = Bool(False).tag(config=True)

    @default("app_flags")
    def _app_flags_default(self):
        return _flags

    def _validate(self):
        pass

    def serialize(self, *args, **kwargs):
        optionals = []

        if self.use_lsqr:
            optionals.append("-ols")

        optionals.append("-iter {}".format(self.reweight_iter))

        return " ".join(optionals)
