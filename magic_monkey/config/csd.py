from traitlets import List, Integer, Instance, Float

from magic_monkey.base.application import MagicMonkeyConfigurable
from magic_monkey.config.algorithms.csd import SphericalDeconvAlgorithm, \
    ResponseAlgorithm


class SphericalDeconvConfiguration(MagicMonkeyConfigurable):
    algorithm = Instance(SphericalDeconvAlgorithm).tag(config=True)

    shells = List(Float).tag(config=True)
    lmax = Integer().tag(config=True)
    strides = List(Integer).tag(config=True)

    def validate(self):
        pass

    def serialize(self):
        optionals = []

        if self.shells:
            optionals.append(
                "-shells {}".format(",".join(str(s) for s in self.shells))
            )

        if self.lmax:
            optionals.append(
                "-lmax {}".format(self.lmax)
            )

        if self.strides:
            optionals.append(
                "-strides {}".format(",".format(self.strides))
            )

        return " ".join([self.algorithm.serialize()] + optionals)


class FiberResponseConfiguration(MagicMonkeyConfigurable):
    algorithm = Instance(ResponseAlgorithm).tag(config=True)

    shells = List(Float).tag(config=True)
    lmax = Integer().tag(config=True)

    def validate(self):
        pass

    def serialize(self):
        optionals = []

        if self.shells:
            optionals.append(
                "-shells {}".format(",".join(str(s) for s in self.shells))
            )

        if self.lmax:
            optionals.append(
                "-lmax {}".format(self.lmax)
            )

        return " ".join([self.algorithm.serialize()] + optionals)
