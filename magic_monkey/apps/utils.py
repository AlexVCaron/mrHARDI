import glob
import re

from copy import deepcopy
from os import getcwd
from os.path import basename, join, exists, dirname

import nibabel as nib
import numpy as np
from traitlets import Dict, Enum, Instance, Integer, Unicode, Bool
from traitlets.config import Config, ArgumentError, TraitError

from magic_monkey.base.application import (MagicMonkeyBaseApplication,
                                           MultipleArguments,
                                           output_file_argument,
                                           output_prefix_argument,
                                           required_arg,
                                           required_file, prefix_argument,
                                           required_number,
                                           output_suffix_argument,
                                           input_dwi_prefix)

from magic_monkey.base.dwi import (Direction,
                                   DwiMetadata,
                                   AcquisitionType,
                                   load_metadata,
                                   save_metadata, DwiMismatchError)

from magic_monkey.base.shell import launch_shell_process
from magic_monkey.compute.b0 import extract_b0, squash_b0
from magic_monkey.compute.utils import apply_mask_on_data, concatenate_dwi
from magic_monkey.config.utils import (B0UtilsConfiguration,
                                       DwiMetadataUtilsConfiguration)

_b0_aliases = {
    'in': 'B0Utils.image',
    'bvals': 'B0Utils.bvals',
    'bvecs': 'B0Utils.bvecs',
    'out': 'B0Utils.output_prefix'
}

_b0_description = """
Utility program used to either extract B0 from a diffusion-weighted image or 
squash those B0 and output the resulting image.
"""


class B0Utils(MagicMonkeyBaseApplication):
    name = u"B0 Utilities"
    description = _b0_description
    configuration = Instance(B0UtilsConfiguration).tag(config=True)

    image = required_file(description="Input dwi image")
    bvals = required_file(description="Input b-values")
    bvecs = Unicode(help="Input b-vectors").tag(config=True, ignore_write=True)

    output_prefix = output_prefix_argument()

    aliases = Dict(_b0_aliases)

    def initialize(self, argv=None):
        assert argv and len(argv) > 0
        if not (
            any("help" in a for a in argv) or
            any("out-config" in a for a in argv) or
            any("safe" in a for a in argv)
        ):
            command, argv = argv[0], argv[1:]
            assert re.match(r'^\w(-?\w)*$', command), \
                "First argument must be the sub-utility to use {}".format(
                    B0UtilsConfiguration.current_util.values
                )
            super().initialize(argv)

            config = deepcopy(self.config)
            config['B0UtilsConfiguration'] = Config(current_util=command)
            self.update_config(config)
        else:
            super().initialize(argv)

    def _example_command(self, sub_command=""):
        return "magic_monkey {} [extract|squash] <args> <flags>".format(
            sub_command
        )

    def execute(self):
        if self.configuration.current_util == "extract":
            self._extract_b0()
        elif self.configuration.current_util == "squash":
            self._squash_b0()
        else:
            self.print_help()

    def _extract_b0(self):
        in_dwi = nib.load(self.image)
        bvals = np.loadtxt(self.bvals)
        kwargs = dict(b0_comp=np.less) if self.configuration.strict else dict()
        metadata = load_metadata(self.image)
        kwargs["metadata"] = metadata

        data = extract_b0(
            in_dwi.get_fdata(), bvals,
            self.configuration.strides,
            self.configuration.get_mean_strategy_enum(),
            self.configuration.ceil_value,
            **kwargs
        )

        if metadata:
            save_metadata(self.output_prefix, metadata)

        img = nib.Nifti1Image(
            data.astype(self.configuration.dtype),
            in_dwi.affine, in_dwi.header
        )
        img.set_data_dtype(self.configuration.dtype)

        nib.save(img, "{}.nii.gz".format(self.output_prefix))

    def _squash_b0(self):
        in_dwi = nib.load(self.image)
        bvals = np.loadtxt(self.bvals)
        kwargs = dict(b0_comp=np.less) if self.configuration.strict else dict()
        metadata = load_metadata(self.image)
        kwargs["metadata"] = metadata

        bvecs = np.loadtxt(self.bvecs) if self.bvecs else None

        data, bvals, bvecs = squash_b0(
            in_dwi.get_fdata(), bvals, bvecs,
            self.configuration.get_mean_strategy_enum(),
            self.configuration.ceil_value,
            **kwargs
        )

        if metadata:
            save_metadata(self.output_prefix, metadata)

        img = nib.Nifti1Image(
            data.astype(self.configuration.dtype),
            in_dwi.affine, in_dwi.header
        )
        img.set_data_dtype(self.configuration.dtype)

        nib.save(img, "{}.nii.gz".format(self.output_prefix))

        np.savetxt("{}.bvals".format(self.output_prefix), bvals, fmt="%d")

        if self.bvecs:
            np.savetxt(
                "{}.bvecs".format(self.output_prefix), bvecs, fmt="%.6f"
            )


_apply_mask_aliases = {
    'in': 'ApplyMask.image',
    'out': 'ApplyMask.output',
    'mask': 'ApplyMask.mask',
    'fill': 'ApplyMask.fill_value',
    'type': 'ApplyMask.dtype'
}


class ApplyMask(MagicMonkeyBaseApplication):
    name = u"Apply Mask"
    description = "Applies a mask to an image an fill the outside."
    image = required_file(description="Input image to mask")
    mask = required_file(description="Mask to apply on image ")

    fill_value = Integer(
        0, help="Value used to fill the image outside the mask"
    ).tag(config=True, required=True)
    dtype = Enum(
        [np.int, np.long, np.float], np.int, help="Output type"
    ).tag(config=True, required=True)

    output = output_file_argument()

    aliases = Dict(_apply_mask_aliases)

    def execute(self):
        data = nib.load(self.image)
        mask = nib.load(self.mask).get_fdata().astype(bool)

        out_data = apply_mask_on_data(data.get_fdata(), mask, self.dtype)

        nib.save(nib.Nifti1Image(out_data, data.affine), self.output)


_cat_aliases = {
    'in': 'Concatenate.images',
    'out': 'Concatenate.prefix',
    'bvals': 'Concatenate.bvals',
    'bvecs': 'Concatenate.bvecs'
}


class Concatenate(MagicMonkeyBaseApplication):
    name = u"Concatenate"
    description = "Concatenates multiple images together"
    images = required_arg(
        MultipleArguments, traits_args=(Unicode,),
        description="Input images to concatenate"
    )

    bvals = MultipleArguments(
        Unicode, help="If provided, will be also concatenated"
    ).tag(config=True)
    bvecs = MultipleArguments(
        Unicode, help="If provided, will be also concatenated"
    ).tag(config=True)

    prefix = output_prefix_argument()

    aliases = Dict(_cat_aliases)

    def execute(self):
        dwi_list = [nib.load(dwi) for dwi in self.images]
        bvals_list = [
            np.loadtxt(bvals) for bvals in self.bvals
        ] if self.bvals else None
        bvecs_list = [
            np.loadtxt(bvecs) for bvecs in self.bvecs
        ] if self.bvecs else None

        reference_affine = dwi_list[0].affine

        out_dwi, out_bvals, out_bvecs = concatenate_dwi(
            [dwi.get_fdata() for dwi in dwi_list],
            bvals_list,
            bvecs_list
        )

        metadatas = list(load_metadata(img) for img in self.images)
        all_meta = all(m is not None for m in metadatas)
        if not all_meta and any(m is not None for m in metadatas):
            raise ArgumentError(
                "Either metadata is provided for all datasets or none of them"
            )

        if all_meta:
            for meta in metadatas[1:]:
                metadatas[0].extend(meta)

            save_metadata(self.prefix, metadatas[0])

        nib.save(
            nib.Nifti1Image(out_dwi, reference_affine),
            "{}.nii.gz".format(self.prefix)
        )

        if out_bvals is not None:
            np.savetxt("{}.bvals".format(self.prefix), out_bvals, fmt="%d")

        if out_bvecs is not None:
            np.savetxt("{}.bvecs".format(self.prefix), out_bvecs.T, fmt="%.6f")


_apply_topup_aliases = dict(
    dwi="ApplyTopup.dwi",
    rev="ApplyTopup.rev",
    acqp="ApplyTopup.acquisition_file",
    topup="ApplyTopup.topup_prefix",
    out="ApplyTopup.output_prefix"
)


class ApplyTopup(MagicMonkeyBaseApplication):
    name = u"Apply Topup"
    description = "Apply a Topup transformation to an image"

    topup_prefix = required_file(
        description="Path and file prefix of the files corresponding "
                    "to the transformation calculated by Topup"
    )

    acquisition_file = required_file(
        description="Acquisition file describing the "
                    "orientation and dwell of the volumes"
    )

    dwi = required_arg(
        MultipleArguments, traits_args=(Unicode,),
        description="Input image or list of images"
    )

    rev = MultipleArguments(
        Unicode, default_value=[],
        help="Input reverse encoded image or list of images"
    ).tag(config=True)

    output_prefix = output_prefix_argument()

    resampling = Enum(
        ["jac", "lsr"], "jac", help="Resampling method"
    ).tag(config=True)

    interpolation = Enum(
        ["trilinear", "spline"], "spline",
        help="Interpolation method, only used with jacobian resampling (jac)"
    ).tag(Config=True)

    dtype = Enum(
        ["char", "short", "int", "float", "double"], None, allow_none=True,
        help="Force output type. If none supplied, "
             "will be the same as the input type."
    ).tag(config=True)

    aliases = Dict(_apply_topup_aliases)

    def execute(self):
        working_dir = getcwd()

        args = "--topup={} --out={} --method={} --interp={}".format(
            self.topup_prefix, self.output_prefix,
            self.resampling, self.interpolation
        )

        args = "--imain={} {}".format(",".join(self.dwi + self.rev), args)

        indexes = np.concatenate(tuple(
            load_metadata(img).topup_indexes for img in self.dwi + self.rev
        ))
        args += " --inindex={}".format(
            ",".join(str(i) for i in indexes.tolist())
        )
        args += " --datain={}".format(self.acquisition_file)

        if self.dtype:
            args += " --datatype={}".format(self.dtype)

        metadata = load_metadata(self.dwi[0])
        for img in self.dwi[1:]:
            metadata.extend(load_metadata(img))

        save_metadata(self.output_prefix, metadata)

        launch_shell_process(
            'applytopup {}'.format(args), join(working_dir, "{}.log".format(
                basename(self.output_prefix)
            ))
        )


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

    update = Bool(
        False, help="If true, will update metadata files "
                    "based on given new parameters"
    ).tag(config=True)

    overwrite = Bool(
        False, help="If True, overwrites the output file when writing"
    ).tag(config=True)

    aliases = Dict(_mb_aliases)
    flags = Dict(_mb_flags)

    def _validate_configuration(self):
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

    def execute(self):
        images = self.preload_images()
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

        for img, d, mb, sd in zip(images, directions, multibands, slice_dirs):
            shape = img["data"].shape
            metadata = DwiMetadata()
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


_split_aliases = {
    'image': 'SplitImage.image',
    'prefix': 'SplitImage.prefix',
    'axis': 'SplitImage.axis'
}

_split_flags = dict(
    inverse=(
        {"SplitImage": {'inverse': True}},
        "reconstruct image from images found by the prefix argument"
    )
)


class SplitImage(MagicMonkeyBaseApplication):
    name = u"Split image given an axis"
    description = (
        "Given an axis into an image, split the image into it's sub-parts "
        "along it. Can also reverse the split to reconstruct the initial image."
    )

    image = required_file(
        description="Input file to split (or, if inverse flag "
                    "supplied, output file to create)"
    )

    prefix = prefix_argument(
        "Prefix for output image sub-parts (or, if inverse flag "
        "supplied, input sub-parts to stitch together)"
    )

    axis = required_number(Integer, description="Axis for the split")

    inverse = Bool(
        False, help="If True, tries to reconstruct image from images "
                    "found by the prefix argument"
    ).tag(config=True)

    _affine = None

    aliases = Dict(_split_aliases)
    flags = Dict(_split_flags)

    def _split_to_img(self):
        n_subs = len(glob.glob("{}*".format(self.prefix)))
        self._affine = nib.load(
            "{}_ax{}_0.nii.gz".format(self.prefix, self.axis)
        ).affine
        fn = np.frompyfunc(self._load_split, 1, 1)
        data = fn(np.arange(0, n_subs))
        nib.save(
            nib.Nifti1Image(np.stack(data, self.axis), self._affine),
            self.image
        )

    def _load_split(self, i):
        return nib.load(
            "{}_ax{}_{}.nii.gz".format(self.prefix, self.axis, i)
        ).get_fdata()

    def _img_to_split(self):
        img = nib.load(self.image)
        metadata = load_metadata(self.image)
        self._affine = img.affine
        for i, sub in enumerate(np.moveaxis(img.get_fdata(), self.axis, 0)):
            mt = metadata.copy()
            try:
                mt.topup_indexes = [metadata.topup_indexes[i]]
            except IndexError:
                print("What the hellllll {}".format(self.image))
                mt.topup_indexes = []
            mt.directions = [metadata.directions[i]]

            self._save_image(i, sub, mt)

    def _save_image(self, idx, data, meta):
        nib.save(
            nib.Nifti1Image(data, self._affine),
            "{}_ax{}_{}.nii.gz".format(self.prefix, self.axis, idx)
        )
        save_metadata("{}_ax{}_{}".format(self.prefix, self.axis, idx), meta)

    def execute(self):
        if self.inverse:
            self._split_to_img()
        else:
            self._img_to_split()


_convert_aliases = {
    'in': 'ConvertImage.image',
    'out': 'ConvertImage.output',
    'dt': 'ConvertImage.datatype'
}


class ConvertImage(MagicMonkeyBaseApplication):
    name = u"Apply conversion operations on image"

    image = required_file(
        description="Input image to convert"
    )

    output = output_file_argument()

    datatype = Unicode().tag(config=True, required=True)

    aliases = Dict(_convert_aliases)

    def execute(self):
        img = nib.load(self.image)
        arr = img.get_fdata()
        arr[~np.isclose(arr, 0)] = 1.
        nib.save(
            nib.Nifti1Image(
                arr.astype(np.dtype(self.datatype)),
                img.affine
            ),
            self.output
        )


_replicate_aliases = {
    'in': 'ReplicateImage.image',
    'out': 'ReplicateImage.output',
    'ref': 'ReplicateImage.reference',
    'idx': 'ReplicateImage.index'
}


class ReplicateImage(MagicMonkeyBaseApplication):
    image = required_file(
        description="Input image to replicate along the last dimension"
    )

    reference = required_file(
        description="Image with required output dimensions"
    )

    output = output_file_argument()

    index = Integer(
        help="Index in the input image where to pick the data to replicate"
    ).tag(config=True)

    aliases = Dict(_replicate_aliases)

    def execute(self):
        img = nib.load(self.image)
        ref = nib.load(self.reference)

        data = img.get_fdata()
        if self.index is not None:
            data = data[..., self.index]

        if len(data.shape) < len(ref.shape):
            data = data[..., None]

        data = np.repeat(data, ref.shape[-1], axis=-1)

        nib.save(nib.Nifti1Image(data, img.affine, img.header), self.output)


_assert_aliases = {
    "in": "AssertDwiDimensions.dwi",
    "bvals": "AssertDwiDimensions.bvals",
    "bvecs": "AssertDwiDimensions.bvecs",
    "strat": "AssertDwiDimensions.strategy"
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

    aliases = Dict(_assert_aliases)

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

            if bvecs.shape[-1] > len(bvals):
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

            np.savetxt(self.bvals, bvals)
            np.savetxt(self.bvecs, bvecs)
