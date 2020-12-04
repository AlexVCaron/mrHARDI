import pickle
import sys

import nibabel as nib
import numpy as np
from dipy.segment.mask import crop
from scilpy.utils.util import voxel_to_world, world_to_voxel
from traitlets import Unicode, Any, Dict

from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    required_file, output_file_argument, BoundingBox

_fit2_aliases = {
    "in": "FitToBox.image",
    "out": "FitToBox.output",
    "bbox": "FitToBox.bounding_box",
    "pbox": "FitToBox.pkl_box",
    "fill": "FitToBox.fill_value"
}


class WorldBoundingBox(object):
    def __init__(self, minimums, maximums, voxel_size):
        self.minimums = minimums
        self.maximums = maximums
        self.voxel_size = voxel_size


def crop_nifti(img, wbbox):
    """Applies cropping from a world space defined bounding box and fixes the
    affine to keep data aligned."""
    data = img.get_fdata(dtype=np.float32, caching='unchanged')
    affine = img.affine

    voxel_bb_mins = world_to_voxel(wbbox.minimums, affine)
    voxel_bb_maxs = world_to_voxel(wbbox.maximums, affine)

    # Prevent from trying to crop outside data boundaries by clipping bbox
    extent = list(data.shape[:3])
    for i in range(3):
        voxel_bb_mins[i] = min(extent[i], max(0, voxel_bb_mins[i]))
        voxel_bb_maxs[i] = min(extent[i], max(0, voxel_bb_maxs[i]))
    translation = voxel_to_world(voxel_bb_mins, affine)

    data_crop = np.copy(crop(data, voxel_bb_mins, voxel_bb_maxs))

    new_affine = np.copy(affine)
    new_affine[0:3, 3] = translation[0:3]

    return nib.Nifti1Image(data_crop, new_affine)


class FitToBox(MagicMonkeyBaseApplication):
    image = required_file(description="Input image to fit to the box")
    output = output_file_argument()

    bounding_box = BoundingBox(
        None, allow_none=True, help="A bouding box in world coordinates"
    ).tag(config=True, required=True, exclusive_group="bbox", group_index=0)
    pkl_box = Unicode(
        None, allow_none=True, help="A .pkl bounding box calculated by Scilpy"
    ).tag(config=True, required=True, exclusive_group="bbox", group_index=1)

    fill_value = Any(
        0, help="Fill value for voxels outside the image, but inside "
                "the box. Must be castable to input image datatype"
    ).tag(config=True)

    aliases = Dict(default_value=_fit2_aliases)

    def execute(self):
        image = nib.load(self.image)

        if self.pkl_box:
            setattr(
                sys.modules['__main__'], 'WorldBoundingBox', WorldBoundingBox
            )
            with open(self.pkl_box, 'rb') as pklf:
                bbox = pickle.load(pklf)
        else:
            bbox = WorldBoundingBox(
                self.bounding_box[0::2],
                self.bounding_box[1::2],
                image.header.get_zooms()[0:3]
            )

        voxel_mins = world_to_voxel(bbox.minimums, image.affine)
        voxel_maxs = world_to_voxel(bbox.maximums, image.affine)

        if np.any(voxel_mins > 0) or np.any(
            np.less(voxel_maxs, image.shape[:3])
        ):
            if not self.pkl_box:
                with open("tmp_bbox.pkl", 'wb') as pklf:
                    pickle.dump(bbox, pklf)
                self.pkl_box = "tmp_bbox.pkl"

            image = crop_nifti(image, bbox)

            voxel_mins = world_to_voxel(bbox.minimums, image.affine)
            voxel_maxs = world_to_voxel(bbox.maximums, image.affine)

        if np.any(voxel_mins < 0) or np.any(
            np.greater(voxel_maxs, image.shape[:3])
        ):
            pads = np.zeros((2, 3))
            pads[0, voxel_mins < 0] = -voxel_mins[voxel_mins < 0]
            pads[1, voxel_maxs > image.shape[:3]] = (
                voxel_maxs - image.shape[:3]
            )[voxel_maxs > image.shape[:3]]

            data = np.pad(
                image.get_fdata().astype(image.get_data_dtype()),
                pads.T.astype(int), 'constant', constant_values=self.fill_value
            )

            affine = image.affine
            affine[:3, -1] = voxel_to_world(voxel_mins, image.affine)
            image = nib.Nifti1Image(data, affine, image.header)

        nib.save(image, self.output)


_fit_aliases = {
    "in": "FitBox.image",
    "out": "FitBox.output",
    "pbox": "FitBox.pkl_box"
}


class FitBox(MagicMonkeyBaseApplication):
    image = required_file(description="Input image to fit to the box")
    output = output_file_argument()

    pkl_box = Unicode(
        None, allow_none=True, help="A .pkl bounding box calculated by Scilpy"
    ).tag(config=True, required=True)

    aliases = Dict(default_value=_fit_aliases)

    def execute(self):
        image = nib.load(self.image)

        setattr(sys.modules['__main__'], 'WorldBoundingBox', WorldBoundingBox)
        with open(self.pkl_box, 'rb') as pklf:
            bbox = pickle.load(pklf)

        voxel_mins = world_to_voxel(bbox.minimums, image.affine)
        voxel_maxs = world_to_voxel(bbox.maximums, image.affine)

        for i in range(3):
            if voxel_mins[i] > voxel_maxs[i]:
                voxel_mins[i] = image.shape[i] - voxel_mins[i]
                voxel_maxs[i] = image.shape[i] - voxel_maxs[i]

        ref_bbox = WorldBoundingBox(
            voxel_to_world(voxel_mins, image.affine),
            voxel_to_world(voxel_maxs, image.affine),
            image.get_header().get_zooms()[0:3]
        )

        with open("{}.pkl".format(self.output), 'wb') as pklf:
            pickle.dump(ref_bbox, pklf)
