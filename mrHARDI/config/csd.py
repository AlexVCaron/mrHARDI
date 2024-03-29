from traitlets import Float, Integer, List, default

from mrHARDI.base.application import (DictInstantiatingInstance,
                                           mrHARDIConfigurable)
from mrHARDI.traits.csd import (ResponseAlgorithm,
                                     SphericalDeconvAlgorithm)

_deconv_aliases = dict(
    shells="CSDConfiguration.shells",
    lmax="CSDConfiguration.lmax",
    strides="CSDConfiguration.strides"
)


class CSDConfiguration(mrHARDIConfigurable):
    algorithm = DictInstantiatingInstance(
        klass=SphericalDeconvAlgorithm
    ).tag(config=True)

    shells = List(Float()).tag(config=True)
    lmax = Integer().tag(config=True)
    strides = List(Integer()).tag(config=True)

    @default("app_aliases")
    def _app_aliases_default(self):
        return _deconv_aliases

    def _validate(self):
        pass

    def serialize(self, *args, **kwargs):
        optionals = []

        if self.shells:
            optionals.append(
                "-shells {}".format(",".join(str(s) for s in self.shells))
            )

        if self.lmax:
            optionals.append(
                "-lmax {}".format(",".join([
                    str(self.lmax) for _ in range(len(self.algorithm.responses))
                ]))
            )

        if self.strides:
            optionals.append(
                "-strides {}".format(",".format(self.strides))
            )

        return " ".join([self.algorithm.serialize()] + optionals)


_response_aliases = dict(
    shells="CSDConfiguration.shells",
    lmax="CSDConfiguration.lmax"
)


class FiberResponseConfiguration(mrHARDIConfigurable):
    algorithm = DictInstantiatingInstance(
        klass=ResponseAlgorithm
    ).tag(config=True)

    shells = List(Float()).tag(config=True)
    lmax = Integer().tag(config=True)

    @default("app_aliases")
    def _app_aliases_default(self):
        return _response_aliases

    def _validate(self):
        pass

    def serialize(self, *args, **kwargs):
        optionals = []

        if self.shells:
            optionals.append(
                "-shells {}".format(",".join(str(s) for s in self.shells))
            )

        if self.lmax:
            optionals.append(
                "-lmax {}".format(self.lmax)
            )

        return " ".join(self.algorithm.serialize() + optionals)
