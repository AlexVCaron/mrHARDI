from traitlets import Float

from mrHARDI.base.application import mrHARDIConfigurable


class BTEddyConfiguration(mrHARDIConfigurable):

    low_b_threshold = Float()

    smoothing_sigma = Float()

    def _validate(self):
        return super()._validate()

    def serialize(self, *args, **kwargs):
        return super().serialize(*args, **kwargs)

