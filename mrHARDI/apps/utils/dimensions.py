import json
import sys

import nibabel as nib
import numpy as np
from dipy.segment.mask import crop
from scipy.linalg import qr, lu
from traitlets import Unicode, Any, Dict

from mrHARDI.compute.utils import voxel_to_world, world_to_voxel
from mrHARDI.base.application import (mrHARDIBaseApplication,
                                           required_file,
                                           output_file_argument,
                                           BoundingBox)

_fit2_aliases = {
    "in": "FitToBox.image",
    "out": "FitToBox.output",
    "bbox": "FitToBox.bounding_box",
    "pbox": "FitToBox.json_box",
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

    return nib.Nifti1Image(data_crop.astype(img.get_data_dtype()), new_affine)


class FitToBox(mrHARDIBaseApplication):
    image = required_file(description="Input image to fit to the box")
    output = output_file_argument()

    bounding_box = BoundingBox(
        None, allow_none=True, help="A bouding box in world coordinates"
    ).tag(config=True, required=True, exclusive_group="bbox", group_index=0)
    json_box = Unicode(
        None, allow_none=True, help="A .json bounding box calculated by Scilpy"
    ).tag(config=True, required=True, exclusive_group="bbox", group_index=1)

    fill_value = Any(
        0, help="Fill value for voxels outside the image, but inside "
                "the box. Must be castable to input image datatype"
    ).tag(config=True)

    aliases = Dict(default_value=_fit2_aliases)

    def execute(self):
        image = nib.load(self.image)

        if self.json_box:
            with open(self.json_box, 'r') as fbox:
                bbox = json.load(fbox)
                bbox = WorldBoundingBox(
                    np.asarray(bbox['minimums']),
                    np.asarray(bbox['maximums']),
                    np.asarray(bbox['voxel_size'])
                )
        else:
            bbox = WorldBoundingBox(
                np.asarray(self.bounding_box[0::2]),
                np.asarray(self.bounding_box[1::2]),
                np.asarray(image.header.get_zooms()[0:3])
            )

        voxel_mins = world_to_voxel(bbox.minimums, image.affine)
        voxel_maxs = world_to_voxel(bbox.maximums, image.affine)

        if np.any(voxel_mins > 0) or np.any(
            np.less(voxel_maxs, image.shape[:3])
        ):
            if not self.json_box:
                with open("tmp_bbox.json", 'w') as fbox:
                    json.dump({
                        "minimums": bbox.minimums.tolist(),
                        "maximums": bbox.maximums.tolist(),
                        "voxel_size": bbox.voxel_size.tolist()
                    }, fbox)
                self.json_box = "tmp_bbox.json"

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
    "ref": "FitBox.reference",
    "out": "FitBox.output",
    "pbox": "FitBox.json_box"
}


class FitBox(mrHARDIBaseApplication):
    image = required_file(description="Input image to fit the box to")
    reference = required_file(description="Reference image for the box")
    output = output_file_argument()

    json_box = Unicode(
        None, allow_none=True, help="A .json bounding box calculated by Scilpy"
    ).tag(config=True, required=True)

    aliases = Dict(default_value=_fit_aliases)

    def _change_world(self, coords, ref_affine, to_affine):
        p, l, u = lu(ref_affine[:3, :3])
        q, r = qr(l @ u)
        t = ref_affine[:3, -1]

        tmp = ((p @ np.diag(np.sign(np.diag(r)))) @ q).T @ (coords - t)

        p, l, u = lu(to_affine[:3, :3])
        q, r = qr(l @ u)
        t = to_affine[:3, -1]

        return p @ np.diag(np.sign(np.diag(r))) @ q @ tmp + t

    def execute(self):
        image = nib.load(self.image)
        ref_affine = nib.load(self.reference).affine

        with open(self.json_box, 'r') as fbox:
            bbox = json.load(fbox)
            bbox = WorldBoundingBox(
                np.asarray(bbox['minimums']),
                np.asarray(bbox['maximums']),
                np.asarray(bbox['voxel_size'])
            )

        voxel_mins = world_to_voxel(
            self._change_world(bbox.minimums, ref_affine, image.affine),
            image.affine
        )
        voxel_maxs = world_to_voxel(
            self._change_world(bbox.maximums, ref_affine, image.affine),
            image.affine
        )

        ref_bbox = WorldBoundingBox(
            np.asarray(voxel_to_world(voxel_mins, image.affine)),
            np.asarray(voxel_to_world(voxel_maxs, image.affine)),
            np.asarray(image.header.get_zooms()[0:3])
        )

        with open("{}.json".format(self.output), 'w') as fbox:
            json.dump({
                "minimums": ref_bbox.minimums.tolist(),
                "maximums": ref_bbox.maximums.tolist(),
                "voxel_size": ref_bbox.voxel_size.tolist()
            }, fbox)
