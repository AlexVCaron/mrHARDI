from copy import deepcopy
import numpy as np
from traitlets import Integer, List, Bool, Float
from traitlets.config.loader import ConfigError

from mrHARDI.base.application import mrHARDIConfigurable, AnyInt
from mrHARDI.compute.utils import validate_affine

class ImageMetadata(mrHARDIConfigurable):
    n = Integer().tag(config=True)
    n_excitations = Integer().tag(config=True)

    acquisition_slices = List(
        List(default_value=[0, None], minlen=2, maxlen=2), allow_none=True
    ).tag(config=True)

    is_multiband = Bool(False, allow_none=True).tag(config=True)
    slice_order = List(List(AnyInt()), allow_none=True).tag(config=True)
    multiband_corrected = Bool(False, allow_none=True).tag(config=True)

    affine = List(
        List(Float(), minlen=4, maxlen=4), minlen=4, maxlen=4
    ).tag(config=True)

    readout = Float().tag(config=True)

    dataset_indexes = List(Integer(), default_value=[0]).tag(config=True)

    number_of_coils = Integer(0).tag(config=True)

    def get_spacing(self):
        return np.absolute(
            np.linalg.eigvalsh(np.array(self.affine)[:3, :3])
        ).tolist()

    def acquisition_slices_to_list(self):
        slices = [
            [s[0], s[1] if s[1] else self.n] for s in self.acquisition_slices
        ]

        return np.concatenate(tuple(
            np.repeat(acq, sl[1] - sl[0])
            for acq, sl in zip("NONE", slices)
        )).tolist()

    def update_acquisition_from_list(self, acqs):
        grad = [
            acqs[i] != acqs[i + 1] for i in np.indices((len(acqs),))[0, :-1]
        ]
        grad.extend([True])
        transitions = np.where(grad)[0]

        acquisition_slices = [[0, transitions[0] + 1]]
        for idx in np.indices(transitions.shape)[0, 1:]:
            acquisition_slices.append(
                [transitions[idx - 1] + 1, transitions[idx] + 1]
            )

        self.acquisition_slices = acquisition_slices

    def becomes(self, oth):
        self.n = oth.n
        self.n_excitations = oth.n_excitations
        self.acquisition_slices = oth.acquisition_slices

        self.is_multiband = oth.is_multiband
        self.slice_order = oth.slice_order
        self.multiband_corrected = oth.multiband_corrected
        self.affine = oth.affine
        self.readout = oth.readout
        self.dataset_indexes = oth.dataset_indexes
        self.number_of_coils = oth.number_of_coils

    def extend(self, oth):
        is_same, _ = validate_affine(
            np.array(self.affine), np.array(oth.affine), True
        )
        assert is_same, "Affine transform for input images are not the same"

        acqs = (
            list(self.acquisition_slices_to_list()) +
            list(oth.acquisition_slices_to_list())
        )
        self.update_acquisition_from_list(acqs)

        self.dataset_indexes += [self.n + idx for idx in oth.dataset_indexes]
        self.n += oth.n

        # TODO: Add logic to check slice ordering
        if self.is_multiband or oth.is_multiband:
            self.is_multiband = True

    def copy(self):
        metadata = ImageMetadata()
        metadata.n = self.n
        metadata.n_excitations = self.n_excitations
        metadata.affine = deepcopy(self.affine)
        metadata.readout = self.readout

        metadata.is_multiband = self.is_multiband
        metadata.slice_order = deepcopy(self.slice_order)

        metadata.acquisition_slices = deepcopy(self.acquisition_slices)
        metadata.dataset_indexes = deepcopy(self.dataset_indexes)
        metadata.number_of_coils = self.number_of_coils

        return metadata

    def adapt_to_shape(self, n):
        if self.n < n:
            if n % self.n == 0:
                reps = int(n / self.n)
                acq = self.acquisition_slices_to_list()
                self.update_acquisition_from_list(
                    np.repeat(acq, reps).tolist()
                )
                self.n = n
            else:
                raise ConfigError(
                    "Could not adapt from {} to {} data points".format(
                        self.n, n
                    )
                )
        elif self.n > n:
            acq = self.acquisition_slices_to_list()
            self.update_acquisition_from_list(acq[:n])
            self.n = n

    def _validate(self):
        pass

    def serialize(self, *args, **kwargs):
        pass
