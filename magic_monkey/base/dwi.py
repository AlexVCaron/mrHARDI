from copy import deepcopy
from enum import Enum
from os.path import join, dirname, basename, exists

import numpy as np
from traitlets import List, Bool, Integer, Float, Unicode

from magic_monkey.base.application import (MagicMonkeyConfigurable,
                                           Vector3D,
                                           ChoiceList,
                                           AnyInt)

from magic_monkey.base.config import ConfigurationLoader


class AcquisitionDirection(Enum):
    AP = [0., 1., 0.]
    PA = [0., -1., 0.]
    RL = [1., 0., 0.]
    LR = [-1., 0., 0.]
    SI = [0., 0., 1.]
    IS = [0., 0., -1.]
    NONE = None


class AcquisitionType(Enum):
    Linear = "Linear"
    Planar = "Planar"
    Spherical = "Spherical"


def metadata_filename_from(img_name):
    return join(
        dirname(img_name),
        "{}_metadata.py".format(basename(img_name).split(".")[0])
    )


def load_metadata(img_name):
    metadata_file = metadata_filename_from(img_name)

    if not exists(metadata_file):
        return None

    metadata = DwiMetadata()
    ConfigurationLoader(metadata).load_configuration(metadata_file)

    return metadata


def save_metadata(prefix, metadata):
    metadata.generate_config_file("{}_metadata".format(prefix))


class DwiMetadata(MagicMonkeyConfigurable):
    n = Integer().tag(config=True)
    directions = List(Vector3D, allow_none=True).tag(config=True)

    is_tensor_valued = Bool(False, allow_none=True).tag(config=True)

    acquisition_types = ChoiceList(
        [d.name for d in AcquisitionType], Unicode,
        help="List of acquisition types of the parts of the input dataset. "
             "A list can be supplied and a series of slices into the dataset "
             "to describe a multi-tensor-valued image."
    ).tag(config=True)
    acquisition_slices = List(
        List(default_value=[0, None], minlen=2, maxlen=2), allow_none=True
    ).tag(config=True)

    is_multiband = Bool(False, allow_none=True).tag(config=True)
    multiband = List(List(AnyInt), allow_none=True).tag(config=True)
    multiband_corrected = Bool(False, allow_none=True).tag(config=True)

    affine = List(
        List(Float, minlen=4, maxlen=4), minlen=4, maxlen=4
    ).tag(config=True)

    dwell = Float().tag(config=True)

    def acquisition_slices_to_list(self):
        slices = [
            [s[0], s[1] if s[1] else self.n] for s in self.acquisition_slices
        ]

        return np.concatenate(tuple(
            np.repeat(acq, sl[1] - sl[0])
            for acq, sl in zip(self.acquisition_types, slices)
        )).tolist()

    def update_acquisition_from_list(self, acqs):
        grad = [
            acqs[i] != acqs[i + 1] for i in np.indices((len(acqs),))[0, :-1]
        ]
        grad.extend([True])
        transitions = np.where(grad)[0]

        acquisition_slices = [[0, transitions[0] + 1]]
        acquisition_types = [acqs[transitions[0]]]
        for idx in np.indices(transitions.shape)[0, 1:]:
            acquisition_slices.append(
                [transitions[idx - 1] + 1, transitions[idx] + 1]
            )
            acquisition_types.append(acqs[transitions[idx]])

        self.acquisition_slices = acquisition_slices
        self.acquisition_types = acquisition_types

    def becomes(self, oth):
        self.n = oth.n
        self.acquisition_types = oth.acquisition_types
        self.acquisition_slices = oth.acquisition_slices
        self.directions = oth.directions
        self.is_tensor_valued = oth.is_tensor_valued
        self.is_multiband = oth.is_multiband
        self.multiband = oth.multiband
        self.multiband_corrected = oth.multiband_corrected
        self.affine = oth.affine
        self.dwell = oth.dwell

    def extend(self, oth):
        assert np.all(np.isclose(self.affine, oth.affine))

        d1 = self.directions if self.directions is not None else [[]]
        d2 = oth.directions if oth.directions is not None else [[]]
        self.directions = np.concatenate((d1, d2)).tolist()

        if self.is_multiband:
            m1 = self.multiband if self.multiband is not None else [[]]
            m2 = oth.multiband if oth.multiband is not None else [[]]

            try:
                m1_max = np.max([np.max(m) if m else -1 for m in m1]) + 1
            except ValueError:
                m1_max = 0

            self.multiband = list(filter(
                lambda l: len(l),
                m1 + list(
                    (np.array(m) + m1_max).tolist() if m else [] for m in m2
                )
            ))

        if self.is_tensor_valued:
            self.acquisition_types = np.concatenate((
                self.acquisition_types, oth.acquisition_types
            ))
            self.acquisition_slices = np.concatenate((
                [
                    [i[0], i[1] if i[1] else self.n + 1]
                    for i in self.acquisition_slices
                ],
                [
                    [self.n + i[0], self.n + i[1] if i[1] else i[1]]
                    for i in oth.acquisition_slices
                ]
            ))

        self.n += oth.n

    def copy(self):
        metadata = DwiMetadata()
        metadata.n = self.n
        metadata.directions = deepcopy(self.directions)
        metadata.affine = deepcopy(self.affine)
        metadata.dwell = self.dwell

        metadata.is_multiband = self.is_multiband
        if self.is_multiband:
            metadata.multiband = deepcopy(self.multiband)

        metadata.is_tensor_valued = self.is_tensor_valued
        metadata.acquisition_types = deepcopy(self.acquisition_types)
        metadata.acquisition_slices = deepcopy(self.acquisition_slices)

        return metadata

    def _validate(self):
        pass

    def serialize(self):
        pass
