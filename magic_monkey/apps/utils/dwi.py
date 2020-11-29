from os.path import exists, basename, join, dirname

import nibabel as nib
import numpy as np
from traitlets import Instance, Unicode, Bool, Dict, TraitError, Enum

from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    required_arg, MultipleArguments, output_prefix_argument
from magic_monkey.base.dwi import AcquisitionType, Direction, \
    load_metadata_file, load_metadata, save_metadata, DwiMetadata, \
    DwiMismatchError
from magic_monkey.config.utils import DwiMetadataUtilsConfiguration

_mb_aliases = {
    'in': 'DwiMetadataUtils.dwis',
    'out': 'DwiMetadataUtils.output_folder',
    'suffix': 'DwiMetadataUtils.suffix'
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
        traits_args=(Unicode,)
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
            self.__class__.name: {},
            self.configuration.__class__.name: {}
        }

        for k, v in config.values():
            if k in traits:
                configuration[self.__class__.name][k] = v
            elif k in conf_traits:
                configuration[self.configuration.__class__.name][k] = v
            else:
                raise TraitError(
                    "Trait {} not found in {} nor {}".format(
                        k, self.__class__.name,
                        self.configuration.__class__.name
                    )
                )

        return configuration

    def _get_multiband_indexes(self, images):
        directions = self.get_multiband_directions(images)
        idxs = np.array([
            np.pad(
                np.arange(img["data"].shape[np.absolute(d).argmax()]),
                (0, img["data"].shape[np.absolute(d).argmax()] %
                 self.configuration.multiband_factor
                 ),
                constant_values=-1
            ).reshape(
                (self.configuration.multiband_factor, -1)
            ).T.astype(int) for img, d in zip(images, directions)
        ])

        if self.configuration.interleaved:
            idxs = np.vstack((idxs[:, :2, ...], idxs[:, 1::2, ...])).reshape(
                (-1, self.configuration.multiband_factor)
            )

        # if self.configuration.gslider_factor:
        #     idxs = np.pad(
        #         idxs,
        #         (
        #             (0, 0),
        #             (0, idxs.shape[1] % self.configuration.gslider_factor),
        #             (0, 0)
        #         ),
        #         constant_values=(
        #             (None, None),
        #             (None, np.repeat(-1, self.configuration.multiband_factor)),
        #             (None, None)
        #         )
        #     ).reshape((
        #         idxs.shape[0],
        #         -1,
        #         self.configuration.multiband_factor *
        #         self.configuration.gslider_factor
        #     ))

        return [
            [list(filter(lambda i: not i == -1, k)) for k in ki]
            for ki in idxs
        ]

    def _expand_to_slices(self, directions, images):
        return [
            np.repeat([direction], img["data"].shape[-1], 0)
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
                    for d in self.configuration.direction
                ],
                images
            )
        else:
            return []

    def get_phase_directions(self, images, val_extractor=lambda v: v.value):
        return self._unpack_directions(
            images, self.configuration.direction, val_extractor
        )

    def get_multiband_directions(self, images, val_extractor=lambda v: v.value):
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
        base_meta = load_metadata_file(self.metadata) if self.metadata else None
        for img in images:
            mt = base_meta.copy() if base_meta else load_metadata(img["name"])
            mt.affine = img["data"].affine.tolist()
            save_metadata(img["name"].split(".")[0], mt)

    def execute(self):
        images = self.preload_images()

        if self.update_affine:
            self._only_update_affine(images)

        directions = self.get_phase_directions(images)
        multibands = None

        if (
            self.configuration.multiband_factor and
            self.configuration.multiband_factor > 1
        ):
            multibands = self._get_multiband_indexes(images)

        if multibands is None:
            multibands = [None for _ in range(len(directions))]

        slice_dirs = self.configuration.slice_direction
        if len(self.configuration.slice_direction) == 1:
            slice_dirs = np.repeat(
                self.configuration.slice_direction, len(images)
            ).tolist()

        for name, img, d, mb, sd in zip(
            self.dwis, images, directions, multibands, slice_dirs
        ):
            shape = img["data"].shape
            metadata = load_metadata(name) if self.metadata else DwiMetadata()
            metadata.n = shape[-1] if len(shape) > 3 else 1
            metadata.n_excitations = int(shape[
                np.argmax(np.absolute(Direction[sd].value))
            ] / self.configuration.multiband_factor)
            metadata.affine = img["data"].affine.tolist()
            metadata.directions = d.tolist()
            metadata.dwell = self.configuration.dwell

            metadata.is_multiband = mb is not None
            metadata.multiband = mb if mb is not None else []
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
            if img.shape[-1] != len(bvals) != bvecs.shape[-1]:
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
                bvecs = bvecs[:, :len(bvals)]
            elif bvecs.shape[-1] != len(bvals):
                if len(bvals) % bvecs.shape[-1] == 0:
                    bvecs = np.repeat(
                        bvecs, int(len(bvals) / bvecs.shape[-1]), axis=1
                    )
                else:
                    b0_mask = np.isclose(bvals, 0)
                    if np.sum(b0_mask) == (len(bvals) - bvecs.shape[-1]):
                        new_bvecs = np.zeros((3, len(bvals)))
                        new_bvecs[~b0_mask] = bvecs
                        bvecs = new_bvecs
                    else:
                        raise DwiMismatchError(
                            img.shape[-1], len(bvals), len(bvecs),
                            "Could not fix b-vectors the supplied dataset"
                        )

            np.savetxt(
                self.bvals if self.output is None else
                "{}.bval".format(self.output),
                bvals
            )
            np.savetxt(
                self.bvecs if self.output is None else
                "{}.bvec".format(self.output),
                bvecs
            )

            if self.output:
                nib.save(img, "{}.nii.gz".format(self.output))

                metadata = load_metadata(self.dwi)
                if metadata:
                    metadata.adapt_to_shape(len(bvals))
                    save_metadata(self.output, metadata)