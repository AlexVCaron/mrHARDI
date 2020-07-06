
from os.path import exists, isfile, isdir

from traitlets import Unicode, TCPAddress, TraitType, Instance
from traitlets.config import Configurable


class SelfInstantiatingInstance(Instance):
    def validate(self, obj, value):
        if isinstance(value, dict):
            return self.klass(**value)
        elif value is None:
            try:
                return self.klass()
            except BaseException:
                self.error(obj, value)
        return super().validate(obj, value)


class ExistingFile(TraitType):
    def _validate(self, obj, value):
        try:
            if isfile(value) and exists(value):
                return value
            self.error(obj, value)
        except BaseException:
            if value is None:
                return value
            self.error(obj, value)


class ExistingDirectory(TraitType):
    def _validate(self, obj, value):
        try:
            if isdir(value) and exists(value):
                return value
            self.error(obj, value)
        except BaseException:
            if value is None:
                return value
            self.error(obj, value)


class BoltConnection(Configurable):
    username = Unicode().tag(config=True)
    password = Unicode().tag(config=True)
    address = TCPAddress().tag(config=True)

    def __init__(self, **kwargs):
        if 'address' in kwargs and not isinstance('address', tuple):
            kwargs['address'] = tuple(kwargs['address'])
        super().__init__(**kwargs)

    def __str__(self):
        return "bolt://{}:{}@{}:{}".format(
            self.username, self.password, *self.address
        )
