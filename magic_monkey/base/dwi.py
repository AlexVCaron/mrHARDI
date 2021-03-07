from copy import deepcopy
from aenum import Enum, NoAlias
from os.path import join, dirname, basename, exists

import numpy as np
from traitlets import List, Bool, Integer, Float, Unicode
from traitlets.config.loader import ConfigError

from magic_monkey.base.application import (MagicMonkeyConfigurable,
                                           Vector3D,
                                           ChoiceList,
                                           AnyInt)

from magic_monkey.base.config import ConfigurationLoader


class Direction(Enum):
    AP = [0., 1., 0.]
    PA = [0., -1., 0.]
    RL = [-1., 0., 0.]
    LR = [1., 0., 0.]
    SI = [0., 0., -1.]
    IS = [0., 0., 1.]
    NONE = None


class AcquisitionType(Enum):
    Linear = "Linear"
    Planar = "Planar"
    Spherical = "Spherical"


def metadata_filename_from(img_name):
    dn = dirname(img_name)
    return join(
        dn,
        "{}_metadata.py".format(basename(img_name).split(".")[0])
    ) if dn else "{}_metadata.py".format(basename(img_name).split(".")[0])


def load_metadata_file(metadata_file):
    metadata = DwiMetadata()
    ConfigurationLoader(metadata).load_configuration(metadata_file)

    return metadata


def load_metadata(img_name):
    metadata_file = metadata_filename_from(img_name)

    if not exists(metadata_file):
        print("No metadata file found : {}".format(img_name))
        return None

    return load_metadata_file(metadata_file)


def save_metadata(prefix, metadata):
    metadata.generate_config_file("{}_metadata".format(prefix))


def non_zero_bvecs(prefix):
    bvecs = np.loadtxt("{}.bvec".format(prefix))
    bvecs[:, np.linalg.norm(bvecs, axis=0) < 1E-6] += 1E-6
    np.savetxt("{}_non_zero.bvec".format(prefix), bvecs, fmt="%.6f")


class Normalization(Enum):
    _settings_ = NoAlias

    UNITY = "unity"
    MAXIMUM = "maximum"
    NONE = "none"
    CUSP = "none"
    NORM = "none"


def _r_unity_norm(b_nominal, bvecs):
    norm = np.linalg.norm(bvecs, axis=0)
    bvecs[:, ~np.isclose(norm, 0)] /= norm[~np.isclose(norm, 0)]

    return np.array([b_nominal for _ in range(bvecs.shape[1])]), bvecs


def _r_max_norm(b_nominal, bvecs):
    bvals, bvecs = _r_unity_norm(b_nominal, bvecs)
    max_vals = np.max(np.absolute(bvecs), 0)
    bvecs[:, ~np.isclose(max_vals, 0)] /= max_vals[~np.isclose(max_vals, 0)]
    norms = np.linalg.norm(bvecs, axis=0)
    return bvals * norms, bvecs


def _r_none_norm(b_nominal, bvecs):
    norms = np.linalg.norm(bvecs, axis=0)
    bvecs[:, ~np.isclose(norms, 0)] /= norms[~np.isclose(norms, 0)]
    return b_nominal * (norms ** 2.) / (np.max(norms) ** 2.), bvecs


def _r_norm_norm(b_nominal, bvecs):
    norms = np.linalg.norm(bvecs, axis=0)
    bvecs[:, ~np.isclose(norms, 0)] /= norms[~np.isclose(norms, 0)]
    return b_nominal * norms / np.max(norms), bvecs


_r_norm_fn = {
    Normalization.UNITY: _r_unity_norm,
    Normalization.MAXIMUM: _r_max_norm,
    Normalization.NONE: _r_none_norm,
    Normalization.NORM: _r_norm_norm
}


class SiemensGradientsReader:
    @classmethod
    def read(cls, filename, b_nominal, cusp=False, norm=False):
        with open(filename) as cusp_file:
            line = cusp_file.readline()
            while line[0] == "#":
                line = cusp_file.readline()

            cusp_file.readline()
            norm_mode = cusp_file.readline().split("=")[1]

            if norm:
                norm_mode = Normalization.NORM
            else:
                norm_mode = Normalization[norm_mode.strip(" ").strip("\n")]

            bvecs = []
            for grad_line in cusp_file:
                grad_line = grad_line.split("=")[1].strip()
                grad_line = grad_line.lstrip("(").rstrip(")").split(",")
                bvecs.append([float(g.strip()) for g in grad_line])

            bvecs = np.array(bvecs).T
            bvals, bvecs = _r_norm_fn[norm_mode](
                b_nominal * 3. if cusp else b_nominal, bvecs
            )

            return bvals, bvecs


def _w_unity_norm(_, bvecs):
    return bvecs


def _w_max_norm(bvals, bvecs):
    return bvecs * bvals / np.max(bvals)


def _w_none_norm(bvals, bvecs):
    print("Performing bvec * sqrt(bval) / sqrt(max_bval)")
    return bvecs * np.sqrt(bvals / np.max(bvals))


def _w_norm_norm(bvals, bvecs):
    print("Performing bvec * bval / max_bval")
    return bvecs * bvals / np.max(bvals)


def _w_cusp_norm(bvals, bvecs):
    print("Performing bvec * sqrt(3. * bval) / sqrt(max_bval)")
    return bvecs * np.sqrt(3. * bvals / np.max(bvals))


_w_norm_fn = {
    Normalization.UNITY: _w_unity_norm,
    Normalization.MAXIMUM: _w_max_norm,
    Normalization.NONE: _w_none_norm,
    Normalization.CUSP: _w_cusp_norm,
    Normalization.NORM: _w_norm_norm
}


class SiemensGradientsWriter:
    @classmethod
    def write(
        cls, bvals, bvecs, filename, coords="xyz",
        normalization=Normalization.NONE
    ):
        with open("{}.dvs".format(filename), 'w+') as f:
            f.write("[directions={}]\n".format(len(bvals)))
            f.write("CoordinateSystem = {}\n".format(coords))
            f.write("Normalization = {}\n".format(normalization.value))

            if (
                normalization == Normalization.UNITY and
                not np.all(np.isclose(bvals, bvals[0]))
            ):
                raise SiemensWriterError(
                    "Normalization is unity, but not all "
                    "directions have the same b-value"
                )

            bvecs = _w_norm_fn[normalization](bvals, bvecs)

            for i, bvec in enumerate(bvecs.T):
                f.write("Vector[{}] = ({:.5}, {:.5}, {:.5})\n".format(
                    i, *bvec
                ))


class DwiMetadata(MagicMonkeyConfigurable):
    n = Integer().tag(config=True)
    n_excitations = Integer().tag(config=True)
    directions = List(Vector3D(), allow_none=True).tag(config=True)

    is_tensor_valued = Bool(False, allow_none=True).tag(config=True)

    acquisition_types = ChoiceList(
        [d.name for d in AcquisitionType], Unicode(),
        help="List of acquisition types of the parts of the input dataset. "
             "A list can be supplied and a series of slices into the dataset "
             "to describe a multi-tensor-valued image."
    ).tag(config=True)
    acquisition_slices = List(
        List(default_value=[0, None], minlen=2, maxlen=2), allow_none=True
    ).tag(config=True)

    is_multiband = Bool(False, allow_none=True).tag(config=True)
    multiband = List(List(AnyInt()), allow_none=True).tag(config=True)
    multiband_corrected = Bool(False, allow_none=True).tag(config=True)

    affine = List(
        List(Float(), minlen=4, maxlen=4), minlen=4, maxlen=4
    ).tag(config=True)

    dwell = Float().tag(config=True)

    topup_indexes = List(Integer(), allow_none=True).tag(config=True)
    dataset_indexes = List(Integer(), default_value=[0]).tag(config=True)

    def get_spacing(self):
        return np.absolute(np.linalg.eigvalsh(np.array(self.affine)[:3, :3])).tolist()

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
        self.n_excitations = oth.n_excitations
        self.acquisition_types = oth.acquisition_types
        self.acquisition_slices = oth.acquisition_slices
        self.directions = oth.directions
        self.is_tensor_valued = oth.is_tensor_valued

        multiband = self.multiband if self.is_multiband else oth.multiband

        self.is_multiband = oth.is_multiband or self.is_multiband
        self.multiband = multiband
        self.multiband_corrected = oth.multiband_corrected
        self.affine = oth.affine
        self.dwell = oth.dwell
        self.topup_indexes = oth.topup_indexes
        self.dataset_indexes = oth.dataset_indexes

    def extend(self, oth):
        assert np.all(np.isclose(self.affine, oth.affine))

        d1 = self.directions if self.directions is not None else [[]]
        d2 = oth.directions if oth.directions is not None else [[]]
        self.directions = np.concatenate((d1, d2)).tolist()

        acqs = (
            list(self.acquisition_slices_to_list()) +
            list(oth.acquisition_slices_to_list())
        )
        self.update_acquisition_from_list(acqs)

        self.dataset_indexes += [self.n + idx for idx in oth.dataset_indexes]
        self.n += oth.n

        self.topup_indexes += oth.topup_indexes

        if self.is_multiband or oth.is_multiband:
            multiband = self.multiband if self.is_multiband else oth.multiband
            self.multiband = multiband
            self.is_multiband = True

    def copy(self):
        metadata = DwiMetadata()
        metadata.n = self.n
        metadata.n_excitations = self.n_excitations
        metadata.directions = deepcopy(self.directions)
        metadata.affine = deepcopy(self.affine)
        metadata.dwell = self.dwell

        metadata.is_multiband = self.is_multiband
        if self.is_multiband:
            metadata.multiband = deepcopy(self.multiband)

        metadata.is_tensor_valued = self.is_tensor_valued
        metadata.acquisition_types = deepcopy(self.acquisition_types)
        metadata.acquisition_slices = deepcopy(self.acquisition_slices)
        metadata.topup_indexes = deepcopy(self.topup_indexes)
        metadata.dataset_indexes = deepcopy(self.dataset_indexes)

        return metadata

    def adapt_to_shape(self, n):
        if self.n < n:
            if n % self.n == 0:
                reps = int(n / self.n)
                acq = self.acquisition_slices_to_list()
                self.update_acquisition_from_list(
                    np.repeat(acq, reps).tolist()
                )
                self.directions = np.repeat(self.directions, reps).tolist()
                if self.topup_indexes:
                    self.topup_indexes = np.repeat(
                        self.topup_indexes, reps
                    ).tolist()
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
            self.directions = self.directions[:n]
            if self.topup_indexes:
                self.topup_indexes = self.topup_indexes[:n]
            self.n = n

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


class SiemensWriterError(Exception):
    def __init__(self, message):
        super().__init__(message)
