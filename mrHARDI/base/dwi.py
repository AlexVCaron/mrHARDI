from copy import deepcopy
from enum import Enum
from mrHARDI.base.image import ImageMetadata


import numpy as np
from traitlets import Dict, List, Bool, Integer, Unicode

from mrHARDI.base.application import ChoiceList


class AcquisitionType(Enum):
    Linear = "Linear"
    Planar = "Planar"
    Spherical = "Spherical"


def non_zero_bvecs(prefix):
    bvecs = np.loadtxt("{}.bvec".format(prefix))
    bvecs[:, np.linalg.norm(bvecs, axis=0) < 1E-6] += 1E-6
    np.savetxt("{}_non_zero.bvec".format(prefix), bvecs, fmt="%.6f")


class DwiMetadata(ImageMetadata):
    directions = List(Dict(), allow_none=True).tag(config=True)
    is_tensor_valued = Bool(False, allow_none=True).tag(config=True)

    acquisition_types = ChoiceList(
        [d.name for d in AcquisitionType], Unicode(),
        help="List of acquisition types of the parts of the input dataset. "
             "A list can be supplied and a series of slices into the dataset "
             "to describe a multi-tensor-valued image."
    ).tag(config=True)

    topup_indexes = List(Integer(), allow_none=True).tag(config=True)

    def acquisition_slices_to_list(self):
        slices = [
            [s[0], s[1] if s[1] else self.n] for s in self.acquisition_slices
        ]

        return np.concatenate(tuple(
            np.repeat(acq, sl[1] - sl[0])
            for acq, sl in zip(self.acquisition_types, slices)
        )).tolist()

    def update_acquisition_from_list(self, acqs):
        super().update_acquisition_from_list(acqs)

        grad = [
            acqs[i] != acqs[i + 1] for i in np.indices((len(acqs),))[0, :-1]
        ]
        grad.extend([True])
        transitions = np.where(grad)[0]

        acquisition_types = [acqs[transitions[0]]]
        for idx in np.indices(transitions.shape)[0, 1:]:
            acquisition_types.append(acqs[transitions[idx]])

        self.acquisition_types = acquisition_types

    def becomes(self, oth):
        super().becomes(oth)
        self.acquisition_types = oth.acquisition_types
        self.directions = oth.directions
        self.is_tensor_valued = oth.is_tensor_valued
        self.topup_indexes = oth.topup_indexes

    def extend(self, oth):
        super().extend(oth)

        d1 = self.directions if self.directions is not None else []
        d2 = oth.directions if oth.directions is not None else []

        for d in d2:
            d["range"] = (
                d["range"][0] + d1[-1]["range"][1],
                d["range"][1] + d1[-1]["range"][1]
            )

        self.directions = d1 + d2

        directions = [self.directions[0]]
        for d in self.directions[1:]:
            if directions[-1]["dir"] == d["dir"]:
                directions[-1]["range"] = (
                    directions[-1]["range"][0],
                    d["range"][1]
                )
            else:
                directions.append(d)

        self.directions = directions

        self.topup_indexes += oth.topup_indexes

    def copy(self):
        metadata = super().copy()
        metadata.directions = deepcopy(self.directions)

        metadata.is_tensor_valued = self.is_tensor_valued
        metadata.acquisition_types = deepcopy(self.acquisition_types)
        metadata.topup_indexes = deepcopy(self.topup_indexes)

        return metadata

    def adapt_to_shape(self, n):
        super().adapt_to_shape()
        if self.n < n:
            reps = int(n / self.n)
            self.directions = np.repeat(self.directions, reps).tolist()
            if self.topup_indexes:
                self.topup_indexes = np.repeat(
                    self.topup_indexes, reps
                ).tolist()
        elif self.n > n:
            self.directions = self.directions[:n]
            if self.topup_indexes:
                self.topup_indexes = self.topup_indexes[:n]

    def _validate(self):
        pass

    def serialize(self, *args, **kwargs):
        pass


class DwiMismatchError(Exception):
    def __init__(self, n_vols, n_bvals, n_bvecs, add_message=None):
        self.shapes = [n_vols, n_bvals, n_bvecs]
        self.message = (
            "The dwi dataset supplied is invalid\n"
            "  -> Number of volumes in image {}\n"
            "  -> Number of b-values {}\n"
            "  -> Number of b-vectors {}\n".format(n_vols, n_bvals, n_bvecs)
        )

        if add_message:
            self.message = "{}\n{}".format(add_message, self.message)

        super().__init__(self.message)
