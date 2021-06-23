import glob
from os.path import basename

import nibabel as nib
import numpy as np
from traitlets import Integer, Enum, Dict, Undefined, Unicode, Bool
from traitlets.config import ArgumentError

from magic_monkey.base.application import (MagicMonkeyBaseApplication,
                                           required_file,
                                           output_file_argument,
                                           required_arg,
                                           MultipleArguments,
                                           output_prefix_argument,
                                           prefix_argument,
                                           required_number)
from magic_monkey.base.dwi import load_metadata, save_metadata
from magic_monkey.compute.utils import apply_mask_on_data, concatenate_dwi

_apply_mask_aliases = {
    'in': 'ApplyMask.image',
    'out': 'ApplyMask.output',
    'mask': 'ApplyMask.mask',
    'fill': 'ApplyMask.fill_value',
    'type': 'ApplyMask.dtype'
}


class ApplyMask(MagicMonkeyBaseApplication):
    _datatype = {
        "int": np.int,
        "long": np.long,
        "float": np.float,
        "float64": np.float64
    }

    name = u"Apply Mask"
    description = "Applies a mask to an image an fill the outside."
    image = required_file(description="Input image to mask")
    mask = required_file(description="Mask to apply on image ")

    fill_value = Integer(
        0, help="Value used to fill the image outside the mask"
    ).tag(config=True)
    dtype = Enum(
        ["int", "long", "float", "float64", Undefined], help="Output type"
    ).tag(config=True)

    output = output_file_argument()

    aliases = Dict(default_value=_apply_mask_aliases)

    def execute(self):
        data = nib.load(self.image)
        mask = nib.load(self.mask).get_fdata().astype(bool)

        dtype = self.dtype
        if dtype is None or dtype is Undefined:
            dtype = data.get_data_dtype()
        else:
            dtype = self._datatype[dtype]

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

        if (
            not all(len(dt.shape) == 3 for dt in data) or
            all(len(dt.shape == 4) for dt in data)
        ):
            data = [
                dt if len(dt.shape) == 4 else dt[..., None]
                for dt in data
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
        "Given an axis into an image, split the image "
        "into it's sub-parts along it. Can also reverse "
        "the split to reconstruct the initial image."
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


_seg_aliases = {
    'in': 'Segmentation2Mask.segmentation',
    'values': 'Segmentation2Mask.values',
    'labels': 'Segmentation2Mask.labels',
    'out': 'Segmentation2Mask.output_prefix'
}


class Segmentation2Mask(MagicMonkeyBaseApplication):
    segmentation = required_file(description="Input segmentation image")

    values = required_arg(
        MultipleArguments, traits_args=(Integer(),),
        description="Image intensities corresponding to tissues"
    )

    labels = required_arg(
        MultipleArguments, traits_args=(Unicode(),),
        description="Labels corresponding to each tissues "
                    "used to generate the output filenames"
    )

    output_prefix = output_prefix_argument()

    aliases = Dict(default_value=_seg_aliases)

    def _validate(self):
        super()._validate()
        if len(self.values) != len(self.labels):
            raise ArgumentError(
                "Number of images intensities differ from number of labels"
            )

    def execute(self):
        img = nib.load(self.segmentation)
        data = img.get_fdata().astype(int)

        for label, value in zip(self.labels, self.values):
            nib.save(
                nib.Nifti1Image((data == value).astype(np.uint8), img.affine),
                "{}_{}.nii.gz".format(self.output_prefix, label)
            )


_odd_aliases = {
    "in": "FixOddDimensions.image",
    "assoc": "FixOddDimensions.associations",
    "suffix": "FixOddDimensions.suffix",
    "strat": "FixOddDimensions.strategy"
}


class FixOddDimensions(MagicMonkeyBaseApplication):
    image = required_file(description="Input main image")

    associations = MultipleArguments(
        Unicode(), [], help="Other images associated with the main image, "
                          "for which the same slices should be added "
                          "or removed to achieve evenness"
    ).tag(config=True)

    strategy = Enum(
        ["add", "sub"], "sub",
        help="Either add a slice at 0 of an odd dimension "
             "or remove the slice with less information"
    ).tag(config=True)

    suffix = Unicode(
        "", help="Suffix to append to image names defining the output name"
    ).tag(config=True)

    aliases = Dict(default_value=_odd_aliases)

    def _validate_associations_shape(self, shape):
        for assoc in self.associations:
            if not np.allclose(nib.load(assoc).shape[:3], shape):
                raise ArgumentError(
                    "Association {} differs in shape from main image".format(
                        basename(assoc)
                    )
                )

    def _get_best_slices(self, odd_dims, img):
        best_slice = [None for _ in odd_dims]
        data = img.get_fdata()
        if len(img.shape) > 3:
            for _ in range(len(img.shape) - 3):
                data = np.mean(data, axis=-1)

        for i, is_odd in enumerate(odd_dims):
            if is_odd:
                slicer = [slice(0, s) for s in data.shape]
                slicer[i] = slice(0, 1)
                first_slice_mean = np.mean(data[tuple(slicer)])
                slicer = [slice(0, s) for s in data.shape]
                slicer[i] = slice(slicer[i].stop - 1, slicer[i].stop)
                last_slice_mean = np.mean(data[tuple(slicer)])
                if first_slice_mean > last_slice_mean:
                    best_slice[i] = "top"
                else:
                    best_slice[i] = "bottom"

        return best_slice

    def execute(self):
        img = nib.load(self.image)

        self._validate_associations_shape(img.shape[:3])

        odd_dims = tuple(s % 2 == 1 for s in img.shape[:3])

        slice_removal = None
        if self.strategy == "sub":
            slice_removal = self._get_best_slices(odd_dims, img)

        for image in [self.image] + self.associations:
            img = nib.load(image)
            metadata = load_metadata(image)
            name = image.split(".")[0] + self.suffix
            extension = ".".join(image.split(".")[1:])

            if self.strategy == "add":
                padding = [(1 if odd else 0, 0) for odd in odd_dims]
                for _ in img.shape[3:]:
                    padding += [(0, 0)]
                data = np.pad(img.get_fdata(), padding)

                if metadata is not None:
                    dir_idx = np.argmax(
                        np.absolute(metadata.directions[0]['dir'])
                    )
                    if odd_dims[dir_idx]:
                        metadata.slice_order = [[0]] + [
                            [i + 1 for i in ii] for ii in metadata.slice_order
                        ]

                        metadata.n_excitations += 1

            else:
                data = img.get_fdata()
                slicer = [slice(0, s) for s in img.shape]
                for i, (is_odd, sl) in enumerate(
                    zip(odd_dims, slice_removal)
                ):
                    if is_odd:
                        if sl == "bottom":
                            slicer[i] = slice(1, slicer[i].stop)
                        else:
                            slicer[i] = slice(
                                slicer[i].start, slicer[i].stop - 1
                            )

                data = data[tuple(slicer)]

                if metadata is not None:
                    dir_idx = np.argmax(
                        np.absolute(metadata.directions[0]['dir'])
                    )
                    if odd_dims[dir_idx]:
                        if slice_removal[dir_idx] == "bottom":
                            for i, so in enumerate(metadata.slice_order):
                                if 0 in so:
                                    so.remove(0)
                            metadata.slice_order = [
                                [s - 1 for s in so]
                                for so in metadata.slice_order
                                if len(so) > 0
                            ]
                        else:
                            max_idx, max_val = 0, 0
                            for i, so in enumerate(metadata.slice_order):
                                for s in so:
                                    if s > max_val:
                                        max_val = s
                                        max_idx = i

                            metadata.slice_order[max_idx].remove(max_val)
                            metadata.slice_order = [
                                so for so in metadata.slice_order
                                if len(so) > 0
                            ]

                        metadata.n_excitations = len(metadata.slice_order)

            nib.save(
                nib.Nifti1Image(data, img.affine, img.header),
                ".".join([name, extension])
            )

            if metadata is not None:
                save_metadata(name, metadata)
