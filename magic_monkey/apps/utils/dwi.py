from os.path import exists, basename, join, dirname

import nibabel as nib
import numpy as np
from traitlets import (Instance,
                       Integer,
                       Unicode,
                       Bool,
                       Dict,
                       TraitError,
                       Enum,
                       Float)
from traitlets.config import Config

from magic_monkey.base.application import (MagicMonkeyBaseApplication,
                                           MultipleArguments,
                                           output_prefix_argument,
                                           required_arg,
                                           required_file)
from magic_monkey.base.dwi import (AcquisitionType,
                                   Direction,
                                   DwiMetadata,
                                   DwiMismatchError,
                                   load_metadata_file,
                                   load_metadata,
                                   save_metadata)
from magic_monkey.config.utils import DwiMetadataUtilsConfiguration

_mb_aliases = {
    'in': 'DwiMetadataUtils.dwis',
    'out': 'DwiMetadataUtils.output_folder',
    'suffix': 'DwiMetadataUtils.suffix',
    'json': 'DwiMetadataUtils.json_config'
}
_mb_flags = dict(
    overwrite=(
        {"DwiMetadataUtils": {'overwrite': True}},
        "Force overwriting of output images if present"
    ),
    update=(
        {"DwiMetadataUtils": {'update': True}},
        "Updates the already present metadata files"
    ),
    update_affine=(
        {"DwiMetadataUtils": {'update_affine': True}},
        "Only update affine file in metadata file"
    )
)


class DwiMetadataUtils(MagicMonkeyBaseApplication):
    name = u"DWI Metadata Utilities"
    description = (
        "Generates json metadata description files for the input datasets. "
        "This allow for easier management of multiband data, oscillating "
        "gradient and tensor-valued acquisitions, as well as other acquisition"
        "properties unavailable from the Nifti file alone."
    )

    configuration = Instance(DwiMetadataUtilsConfiguration).tag(config=True)

    dwis = required_arg(
        MultipleArguments, [],
        "Dwi volumes for which to create metadata files",
        traits_args=(Unicode(),)
    )

    suffix = Unicode(
        help="Suffix to append to metadata filenames"
    ).tag(config=True)

    output_folder = Unicode(
        help="Optional output folder for metadata files. Defaults to the same "
             "folder where the input dwis are."
    ).tag(config=True)

    json_config = Unicode(
        help="Json configuration file replacing the arguments"
    ).tag(config=True)

    metadata = Unicode(
        help="Force an update on a specific metadata file. Will "
             "output to a metadata file based on input image name."
    ).tag(config=True)

    update = Bool(
        False, help="If true, will update metadata files "
                    "based on given new parameters"
    ).tag(config=True)

    update_affine = Bool(
        False, help="If true, only update affine data"
    ).tag(config=True)

    overwrite = Bool(
        False, help="If True, overwrites the output file when writing"
    ).tag(config=True)

    aliases = Dict(default_value=_mb_aliases)
    flags = Dict(default_value=_mb_flags)

    def _validate_configuration(self):
        if self.update_affine:
            return

        if not self.update and self.configuration.acquisition is None:
            self.configuration.acquisition = AcquisitionType.Linear.name

        if self.json_config:
            assert exists(self.json_config)
            config = (
                self.json_config_loader_class(self.json_config).load_config()
            )
            self.update_config(self._split_config(dict(config)))

        if (
            self.configuration.multiband_factor and
            self.configuration.multiband_factor > 1
        ):
            self.configuration.traits()["slice_direction"].tag(
                required=True
            )

        super()._validate_configuration()

    def _split_config(self, config):
        traits = self.traits(config=True)
        conf_traits = self.configuration.traits(config=True)
        configuration = {
            self.__class__.__name__: {},
            self.configuration.__class__.__name__: {}
        }

        for k, v in config.items():
            if k in traits:
                configuration[self.__class__.__name__][k] = v
            elif k in conf_traits:
                configuration[self.configuration.__class__.__name__][k] = v
            else:
                raise TraitError(
                    "Trait {} not found in {} nor {}".format(
                        k, self.__class__.name,
                        self.configuration.__class__.name
                    )
                )

        return Config(configuration)

    def _get_slice_indexes(self, images):
        directions = self.get_slice_directions(images)
        idxs = np.array([
            np.pad(
                np.arange(img["data"].shape[np.absolute(d).argmax()]),
                (0, img["data"].shape[np.absolute(d).argmax()] %
                 self.configuration.multiband_factor
                 ),
                mode="constant",
                constant_values=-1
            ).reshape(
                (self.configuration.multiband_factor, -1)
            ).T.astype(int) for img, d in zip(images, directions)
        ])

        if self.configuration.interleaved:
            idxs = np.hstack((idxs[:, ::2, ...], idxs[:, 1::2, ...]))

        return [
            [list(filter(lambda i: not i == -1, k)) for k in ki]
            for ki in idxs
        ]

    def _shape_at_least_4D(self, image):
        return 1 if len(image.shape) < 4 else image.shape[-1]

    def _expand_to_slices(self, directions, images):
        return [
            np.repeat([direction], self._shape_at_least_4D(img["data"]), 0)
            for img, direction in zip(images, directions)
        ]

    def _unpack_directions(
        self, images, directions, val_extractor=lambda v: v.value
    ):
        if len(directions) == 1:
            d = directions[0]
            return self._expand_to_slices(
                np.repeat(
                    [val_extractor(Direction[d])],
                    len(images), 0
                ),
                images
            )
        elif len(directions) == len(images):
            return self._expand_to_slices(
                [
                    val_extractor(Direction[d])
                    for d in directions
                ],
                images
            )
        else:
            return []

    def get_phase_directions(self, images, val_extractor=lambda v: v.value):
        if len(self.configuration.direction) == 1:
            d = self.configuration.direction[0]
            return [{
                "dir": val_extractor(Direction[d]),
                "range": (0, self._shape_at_least_4D(i["data"]))
            } for i in images]
        elif len(self.configuration.direction) == len(images):
            return [{
                "dir": val_extractor(Direction[d]),
                "range": (0, self._shape_at_least_4D(i["data"]))
            } for d, i in zip(self.configuration.direction, images)]
        else:
            return []

    def get_slice_directions(self, images, val_extractor=lambda v: v.value):
        return self._unpack_directions(
            images, self.configuration.slice_direction, val_extractor
        )

    def preload_images(self):
        return [
            {"data": nib.load(name), "name": name} for name in self.dwis
        ]

    def _get_file_for(self, image_name):
        name = "{}_metadata".format(basename(image_name).split(".")[0])
        name = "{}_{}".format(name, self.suffix) if self.suffix else name
        return join(
            self.output_folder if self.output_folder else dirname(image_name),
            name
        )

    def _only_update_affine(self, images):
        base_meta = load_metadata_file(self.metadata) \
            if self.metadata else None

        for img in images:
            mt = base_meta.copy() if base_meta else load_metadata(img["name"])
            mt.affine = img["data"].affine.tolist()
            save_metadata(img["name"].split(".")[0], mt)

    def execute(self):
        images = self.preload_images()

        if self.update_affine:
            self._only_update_affine(images)

        directions = self.get_phase_directions(images)

        if self.configuration.multiband_factor in [None, 0]:
            self.configuration.multiband_factor = 1

        slice_indexes = self.configuration.slice_indexes
        if slice_indexes is None:
            slice_indexes = self._get_slice_indexes(images)
        else:
            slice_indexes = [slice_indexes for _ in range(len(images))]

        slice_dirs = self.configuration.slice_direction
        if len(self.configuration.slice_direction) == 1:
            slice_dirs = np.repeat(
                self.configuration.slice_direction, len(images)
            ).tolist()

        for name, img, d, ss, sd in zip(
            self.dwis, images, directions, slice_indexes, slice_dirs
        ):
            shape = img["data"].shape
            metadata = load_metadata(name) if self.metadata else DwiMetadata()
            metadata.n = shape[-1] if len(shape) > 3 else 1
            metadata.n_excitations = int(shape[
                np.argmax(np.absolute(Direction[sd].value))
            ] / self.configuration.multiband_factor)
            metadata.affine = img["data"].affine.tolist()
            metadata.directions = [d]
            metadata.readout = self.configuration.readout

            metadata.is_multiband = (
                self.configuration.multiband_factor and
                self.configuration.multiband_factor > 1
            )
            metadata.slice_order = ss if ss is not None else []
            metadata.multiband_corrected = \
                self.configuration.multiband_corrected or False

            metadata.is_tensor_valued = \
                self.configuration.tensor_valued or False
            metadata.acquisition_types = [
                AcquisitionType[self.configuration.acquisition].value
            ]
            metadata.acquisition_slices = [[0, None]]

            metadata.generate_config_file(self._get_file_for(img["name"]))


_assert_aliases = {
    "in": "AssertDwiDimensions.dwi",
    "bvals": "AssertDwiDimensions.bvals",
    "bvecs": "AssertDwiDimensions.bvecs",
    "strat": "AssertDwiDimensions.strategy",
    "out": "AssertDwiDimensions.output"
}


class AssertDwiDimensions(MagicMonkeyBaseApplication):
    dwi = required_arg(
        Unicode,
        description="Input dwi file to which to compare bvals and bvecs"
    )

    bvals = required_arg(Unicode, description="Input b-values file")
    bvecs = required_arg(Unicode, description="Input b-vectors file")

    strategy = Enum(
        ["error", "fix"], "error",
        help="Strategy to employ when discrepancies are found, either "
             "output an error message or try to fix the problem"
    ).tag(config=True)

    output = output_prefix_argument(
        description="Output prefix for checked files. If supplied, will also "
                    "copy the input dwi to the new name. If none supplied, "
                    "will overwrite the input files.",
        required=False
    )

    aliases = Dict(default_value=_assert_aliases)

    def execute(self):
        img = nib.load(self.dwi)
        bvals, bvecs = np.loadtxt(self.bvals), np.loadtxt(self.bvecs).T

        if self.strategy is "error":
            if img.shape[-1] != len(bvals) != len(bvecs):
                raise DwiMismatchError(img.shape[-1], len(bvals), len(bvecs))
        else:
            if len(bvals) > img.shape[-1]:
                bvals = bvals[:img.shape[-1]]
            elif img.shape[-1] != len(bvals):
                if img.shape[-1] % len(bvals) == 0:
                    bvals = np.repeat(bvals, int(img.shape[-1] / len(bvals)))
                else:
                    raise DwiMismatchError(
                        img.shape[-1], len(bvals), len(bvecs),
                        "Could not fix b-values of the supplied dataset"
                    )

            if bvecs.shape[0] > len(bvals):
                bvecs = bvecs[:len(bvals), :]
            elif bvecs.shape[0] != len(bvals):
                if len(bvals) % bvecs.shape[0] == 0:
                    bvecs = np.repeat(
                        bvecs, int(len(bvals) / bvecs.shape[0]), axis=0
                    )
                else:
                    b0_mask = np.isclose(bvals, 0)
                    zero_bvecs = np.isclose(np.linalg.norm(bvecs, axis=1), 0)
                    if np.sum(b0_mask) == (
                        len(bvals) - bvecs.shape[0] + np.sum(zero_bvecs)
                    ):
                        new_bvecs = np.zeros((len(bvals), 3))
                        new_bvecs[~b0_mask] = bvecs[~zero_bvecs]
                        bvecs = new_bvecs
                    else:
                        raise DwiMismatchError(
                            img.shape[-1], len(bvals), len(bvecs),
                            "Could not fix b-vectors the supplied dataset"
                        )

            np.savetxt(
                self.bvals if self.output is None else
                "{}.bval".format(self.output),
                bvals[None, :], fmt='%.2f'
            )
            np.savetxt(
                self.bvecs if self.output is None else
                "{}.bvec".format(self.output),
                bvecs.T, fmt='%.8f'
            )

            if self.output:
                nib.save(img, "{}.nii.gz".format(self.output))

                metadata = load_metadata(self.dwi)
                if metadata:
                    metadata.adapt_to_shape(len(bvals))
                    save_metadata(self.output, metadata)


_shells_aliases = {
    "in": "ExtractShells.dwi",
    "bvals": "ExtractShells.bvals",
    "bvecs": "ExtractShells.bvecs",
    "shells": "ExtractShells.shells",
    "count": "ExtractShells.count",
    "keep": "ExtractShells.keep",
    "out": "ExtractShells.output"
}

_shells_flags = dict(
    with_b0=(
        {"ExtractShells": {"keep_b0": True}},
        'Keeps b0 volumes in the output'
    )
)


class ExtractShells(MagicMonkeyBaseApplication):
    dwi = required_arg(
        Unicode,
        description="Dwi file to extract shells from"
    )

    bvals = required_arg(Unicode, description="Input b-values file")
    bvecs = required_arg(Unicode, description="Input b-vectors file")

    shells = MultipleArguments(
        Float(), help="Shells group of threshold to work from. If None, "
                      "will execute on all shells, excepts b0 volumes."
    ).tag(config=True)

    count = Integer(
        default_value=0, help="Keep only shells which have a number "
                              "of directions greater than this parameter"
    ).tag(config=True)

    keep = Enum(
        ["all", "geq", "leq", "bigset", "smallset"], "all",
        help="Selection strategy to subset the initial group of shells."
    ).tag(config=True)

    keep_b0 = Bool(
        False, help="When False, removes the b0 volumes from the output volume"
    ).tag(config=True)

    output = output_prefix_argument()

    aliases = Dict(default_value=_shells_aliases)
    flags = Dict(default_value=_shells_flags)

    def execute(self):
        bvals = np.loadtxt(self.bvals)
        bvecs = np.loadtxt(self.bvecs)
        dwi = nib.load(self.dwi)

        if not self.shells:
            shells, cnt = np.unique(
                bvals[~np.isclose(bvals, 0.)], return_counts=True
            )
        else:
            shells, cnt = np.unique(np.array(self.shells), return_counts=True)

        shells = shells[cnt > self.count]

        mask = np.zeros_like(bvals, bool)
        if self.keep == "leq":
            mask |= bvals <= shells.max()
        elif self.keep == "geq":
            mask |= bvals >= shells.min()
        elif self.keep == "bigset":
            counts = np.array([(bvals == s).sum() for s in shells])
            mask |= bvals == shells[counts.argmax()]
        elif self.keep == "smallset":
            counts = np.array([(bvals == s).sum() for s in shells])
            mask |= bvals == shells[counts.argmin()]
        elif self.keep == "all":
            for shell in shells:
                mask |= bvals == shell

        if self.keep_b0:
            mask |= np.isclose(bvals, 0.)
        else:
            mask &= ~np.isclose(bvals, 0.)

        np.savetxt("{}.bval".format(self.output), bvals[mask][None, :])
        np.savetxt("{}.bvec".format(self.output), bvecs[:, mask])
        nib.save(
            nib.Nifti1Image(
                dwi.get_fdata().astype(dwi.get_data_dtype())[..., mask],
                dwi.affine, dwi.header
            ),
            "{}.nii.gz".format(self.output)
        )

        metadata = load_metadata(self.dwi)
        if metadata:
            acq_types = np.array(metadata.acquisition_slices_to_list())[mask]
            directions = np.array(metadata.directions)[mask, :]
            metadata.update_acquisition_from_list(acq_types.tolist())
            metadata.directions = directions.tolist()
            metadata.n = int(mask.sum())
            save_metadata(self.output, metadata)


_flip_aliases = {
    "in": "FlipGradientsOnReference.dwi",
    "bvecs": "FlipGradientsOnReference.bvecs",
    "out": "FlipGradientsOnReference.output"
}


class FlipGradientsOnReference(MagicMonkeyBaseApplication):
    dwi = required_file(description="Input dwi file used as reference")
    bvecs = required_file(description="Input b-vectors to flip")

    output = output_prefix_argument()

    aliases = Dict(default_value=_flip_aliases)

    def execute(self):
        affine = nib.load(self.dwi).affine[:3, :3]
        flips = np.sign(np.linalg.inv(affine) @ [1, 1, 1]) < 0
        bvecs = np.loadtxt(self.bvecs)
        bvecs[flips, :] *= -1.

        np.savetxt("{}.bvec".format(self.output), bvecs)


_duplicates_aliases = {
    "in": "CheckDuplicatedBvecsInShell.dwi",
    "bvals": "CheckDuplicatedBvecsInShell.bvals",
    "bvecs": "CheckDuplicatedBvecsInShell.bvecs",
    "out": "CheckDuplicatedBvecsInShell.output",
    "merge": "CheckDuplicatedBvecsInShell.merging",
    "abs-thr": "CheckDuplicatedBvecsInShell.abs_threshold"
}


class CheckDuplicatedBvecsInShell(MagicMonkeyBaseApplication):
    dwi = required_file(description="Input dwi file")
    bvals = required_file(description="Input b-values file")
    bvecs = required_file(description="Input b-vectors file")

    merging = Enum(
        ["first", "mean", "median"], "median",
        help="Merge strategy of duplicates"
    ).tag(config=True)

    abs_threshold = Float(
        1E-5, help="Absolute threshold on distance between directions"
    ).tag(config=True)

    output = output_prefix_argument()

    aliases = Dict(default_value=_duplicates_aliases)

    _mergers = {
        "first": lambda dt: dt[..., 0],
        "mean": lambda dt: np.mean(dt, -1),
        "median": lambda dt: np.median(dt, -1)
    }

    def execute(self):
        bvals = np.loadtxt(self.bvals)
        bvecs = np.loadtxt(self.bvecs).T
        dwi = nib.load(self.dwi)
        data = dwi.get_fdata().astype(dwi.get_data_dtype())

        merge_fn = self._mergers[self.merging]

        odwi = []
        obvals = []
        obvecs = []
        processed_vols = np.array([False] * data.shape[-1])

        b0_mask = np.isclose(bvals, 0.)
        meta_mask = np.zeros((len(bvals),),  dtype=bool)

        for i in range(data.shape[-1]):
            if not processed_vols[i]:
                processed_vols[i] = True
                meta_mask[i] = True
                obvals.append(bvals[i])
                obvecs.append(bvecs[i])
                if b0_mask[i]:
                    odwi.append(data[..., i, None])
                else:
                    shell_mask = np.isclose(bvals, bvals[i])
                    shell_mask[processed_vols] = False
                    distances = 1. - bvecs[shell_mask] @ bvecs[i]
                    close_idxs = np.where(shell_mask)[0][np.isclose(distances, 0.)]
                    processed_vols[close_idxs] = True
                    if len(close_idxs) == 1:
                        odwi.append(data[..., i, None])
                    else:
                        close_idxs = np.concatenate((close_idxs, [i]))
                        odwi.append(merge_fn(data[..., close_idxs])[..., None])

        np.savetxt("{}.bval".format(self.output), obvals, fmt="%d", newline=" ")
        np.savetxt(
            "{}.bvec".format(self.output), np.array(obvecs).T, fmt="%.6f"
        )
        nib.save(
            nib.Nifti1Image(
                np.concatenate(odwi, axis=-1), dwi.affine, dwi.header
            ),
            "{}.nii.gz".format(self.output)
        )

        metadata = load_metadata(self.dwi)
        if metadata:
            acq_types = np.array(metadata.acquisition_slices_to_list())[meta_mask]
            directions = np.array(metadata.directions)[meta_mask, :]
            metadata.update_acquisition_from_list(acq_types.tolist())
            metadata.directions = directions.tolist()
            metadata.n = int(meta_mask.sum())
            save_metadata(self.output, metadata)
