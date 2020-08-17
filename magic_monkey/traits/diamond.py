from traitlets import TraitType


class BoundingBox(TraitType):
    default_value = None

    def get(self, obj, cls=None):
        value = super().get(obj, cls)

        if value is not None:
            return ",".join(str(v) for v in value)

        return value

    def validate(self, obj, value):
        if isinstance(value, tuple):
            if len(value) == 6:
                if all(isinstance(v, int) for v in value):
                    return value

        if isinstance(value, str):
            if len(value.split(",")) == 6:
                return value.split(",")

        if value is not None:
            self.error(obj, value)


class Stick(TraitType):
    default_value = None

    def get(self, obj, cls=None):
        value = super().get(obj, cls)

        if value is not None:
            return ",".join(str(v) for v in value)

        return value

    def validate(self, obj, value):
        if isinstance(value, tuple):
            if len(value) == 3:
                if all(isinstance(v, float) for v in value):
                    return value

        if isinstance(value, str):
            if len(value.split(",")) == 3:
                return value.split(",")

        if value is not None:
            self.error(obj, value)
