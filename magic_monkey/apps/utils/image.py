import glob

import nibabel as nib
import numpy as np
import re
from os.path import isfile, basename, join
from os import listdir, remove, walk
from traitlets import Integer, Enum, Dict, Unicode, Bool
from traitlets.config import ArgumentError

from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    required_file, output_file_argument, required_arg, MultipleArguments, \
    output_prefix_argument, prefix_argument, required_number, convert_enum
from magic_monkey.base.dwi import load_metadata, save_metadata
from magic_monkey.base.image import (image_reader,
                                     image_writer,
                                     valid_extensions)
from magic_monkey.compute.utils import apply_mask_on_data, concatenate_dwi

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
    ).tag(config=True)
    dtype = Enum(
        [np.int, np.long, np.float, np.float64, None], help="Output type"
    ).tag(config=True)

    output = output_file_argument()

    aliases = Dict(default_value=_apply_mask_aliases)

    def execute(self):
        data = nib.load(self.image)
        mask = nib.load(self.mask).get_fdata().astype(bool)

        dtype = self.dtype
        if dtype is None:
            dtype = data.get_data_dtype()

        out_data = apply_mask_on_data(
            data.get_fdata().astype(dtype), mask, self.fill_value, dtype
        )

        nib.save(nib.Nifti1Image(out_data, data.affine), self.output)


_cat_aliases = {
    'in': 'Concatenate.images',
    'out': 'Concatenate.prefix',
    'bvals': 'Concatenate.bvals',
    'bvecs': 'Concatenate.bvecs'
}

_cat_flags = dict(
    ts=(
        {"Concatenate": {'time_series': True}},
        "Concatenate the images along a new axis in last "
        "dimension, to form a time-series of images"
    )
)

class Concatenate(MagicMonkeyBaseApplication):
    name = u"Concatenate"
    description = "Concatenates multiple images together"
    images = required_arg(
        MultipleArguments, traits_args=(Unicode(),),
        description="Input images to concatenate"
    )

    bvals = MultipleArguments(
        Unicode(), help="If provided, will be also concatenated"
    ).tag(config=True)
    bvecs = MultipleArguments(
        Unicode(), help="If provided, will be also concatenated"
    ).tag(config=True)

    prefix = output_prefix_argument()

    time_series = Bool(False).tag(config=True)

    aliases = Dict(default_value=_cat_aliases)
    flags = Dict(default_value=_cat_flags)

    def execute(self):
        dwi_list = [nib.load(dwi) for dwi in self.images]
        bvals_list = [
            np.loadtxt(bvals) for bvals in self.bvals
        ] if self.bvals else None
        bvecs_list = [
            np.loadtxt(bvecs) for bvecs in self.bvecs
        ] if self.bvecs else None

        reference_affine = dwi_list[0].affine
        reference_header = dwi_list[0].header

        data = [
            dwi.get_fdata().astype(dtype=dwi.get_data_dtype())
            for dwi in dwi_list
        ]

        if len(data) == 1:
            out_dwi, out_bvals, out_bvecs = (
                data[0],
                bvals_list[0][None, :] if bvals_list else None,
                bvecs_list[0].T if bvecs_list else None
            )
        else:
            out_dwi, out_bvals, out_bvecs = concatenate_dwi(
                [d[..., None] for d in data] if self.time_series else data,
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
            nib.Nifti1Image(out_dwi, reference_affine, reference_header),
            "{}.nii.gz".format(self.prefix)
        )

        if out_bvals is not None:
            np.savetxt("{}.bval".format(self.prefix), out_bvals, fmt="%d")

        if out_bvecs is not None:
            np.savetxt("{}.bvec".format(self.prefix), out_bvecs.T, fmt="%.6f")


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

    aliases = Dict(default_value=_split_aliases)
    flags = Dict(default_value=_split_flags)

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
        img = nib.load(
            "{}_ax{}_{}.nii.gz".format(self.prefix, self.axis, i)
        )
        return img.get_fdata().astype(img.get_data_dtype())

    def _img_to_split(self):
        img = nib.load(self.image)
        metadata = load_metadata(self.image)
        self._affine = img.affine
        for i, sub in enumerate(np.moveaxis(
            img.get_fdata().astype(img.get_data_dtype()), self.axis, 0
        )):
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

    aliases = Dict(default_value=_convert_aliases)

    def execute(self):
        img = nib.load(self.image)
        arr = img.get_fdata().astype(img.get_data_dtype())
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

    aliases = Dict(default_value=_replicate_aliases)

    def execute(self):
        img = nib.load(self.image)
        ref = nib.load(self.reference)

        data = img.get_fdata().astype(img.get_data_dtype())
        if self.index is not None:
            data = data[..., self.index]

        if len(data.shape) < len(ref.shape):
            data = data[..., None]

        data = np.repeat(data, ref.shape[-1], axis=-1)

        nib.save(nib.Nifti1Image(data, img.affine, img.header), self.output)


_ext_aliases = {
    'in': 'ChangeExtension.image_or_path',
    'ext': 'ChangeExtension.output_extension',
}

_ext_flags = dict(
    current=(
        {"ChangeExtension": {'traversal': False}},
        "Disable sub-folders traversal"
    ),
    remove=(
        {"ChangeExtension": {'remove_source': True}},
        "Remove the source files"
    )
)


class ChangeExtension(MagicMonkeyBaseApplication):
    image_or_path = required_arg(
        Unicode, description="Input image (.nii/.nii.gz/.nrrd) "
                             "or path to convert"
    )

    output_extension = Enum(
        valid_extensions, "nii.gz"
    ).tag(config=True)

    remove_source = Bool(
        False, help="If True, will remove the source file"
    ).tag(config=True)

    traversal = Bool(
        True, help="If True, will traverse folder and all "
                   "sub-folders to check for files to convert"
    ).tag(config=True)

    aliases = Dict(default_value=_ext_aliases)
    flags = Dict(default_value=_ext_flags)

    def _get_extension(self, filename):
        try:
            match = re.match(
                ".*(?={})(?P<ext>.*)".format("|".join(valid_extensions)),
                filename
            )
            return match.group("ext")
        except Exception:
            return None

    def _split_extension(self, filename):
        match = re.match(
            "(?P<name>.*)\\.(?={})(?P<ext>.*)".format(
                "|".join(valid_extensions)
            ),
            filename
        )
        try:
            return match.group("name"), match.group("ext")
        except Exception:
            return match.group("name"), None

    def _write_image(self, name, input_ext):
        image_writer[self.output_extension].write(
            ".".join([name, self.output_extension]),
            image_reader[input_ext].read(".".join([name, input_ext]))
        )

    def _get_path_iterator(self):
        if self.traversal:
            for root, dirs, files in walk(self.image_or_path):
                yield root, [
                    self._split_extension(f)
                    for f in filter(
                        lambda f: self._get_extension(f) in valid_extensions,
                        files
                    )
                ]
        else:
            return [
                self.image_or_path, [
                    self._split_extension(f)
                    for f in filter(
                        lambda f: self._get_extension(f) in valid_extensions,
                        listdir(self.image_or_path)
                    )
                ]
            ]

    def execute(self):
        if isfile(self.image_or_path):
            name, extension = self._get_extension(basename(self.image_or_path))
            if not extension == self.output_extension:
                self._write_image(name, extension)
                if self.remove_source:
                    remove(self.image_or_path)
        else:
            for directory, files in self._get_path_iterator():
                for name, extension in files:
                    if not extension == self.output_extension:
                        self._write_image(join(directory, name), extension)
                        if self.remove_source:
                            remove(
                                ".".join([join(directory, name), extension])
                            )
