from traitlets import Bool, Integer

from magic_monkey.base.application import MagicMonkeyConfigurable


# TODO : Check if interesting to add aliases and flags to cmdline
class DTIConfiguration(MagicMonkeyConfigurable):
    use_lsqr = Bool(False).tag(config=True)
    reweight_iter = Integer(2).tag(config=True)
    predicted_signal = Bool(False).tag(config=True)

    def validate(self):
        pass

    def serialize(self):
        optionals = []

        if self.use_lsqr:
            optionals.append("-ols")

        optionals.append("-iter {}".format(self.reweight_iter))

        return " ".join(optionals)
