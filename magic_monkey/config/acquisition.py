from traitlets import Bool, Float, Integer

from magic_monkey.base.application import MagicMonkeyConfigurable


class TriangulationConfiguration(MagicMonkeyConfigurable):
    regroup_radii = Bool(True).tag(config=True)
    regroup_threshold = Float(0.5).tag(config=True)
    radii_precision = Float(1E-6).tag(config=True)

    def __init__(self, default_overrides=None, **kwargs):
        super().__init__(**kwargs)
        if default_overrides is not None:
            for name, trait in self.traits().items():
                if name in default_overrides:
                    trait.default_value = default_overrides[name]
                    trait.set(self, default_overrides[name])

    def _validate(self):
        pass

    def serialize(self):
        pass
