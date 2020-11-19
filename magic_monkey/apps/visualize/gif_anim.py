from os.path import join
from tempfile import mkdtemp

import imageio
import pygifsicle
import nibabel as nib
import numpy as np

from traitlets import Unicode, Enum, Dict, Bool, Float
from enum import Enum as PyEnum

from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    required_arg, MultipleArguments, Resolution, output_prefix_argument
from magic_monkey.compute.math.tensor import compute_eigenvalues
from magic_monkey.traits.diamond import BoundingBox

from fury import actor, window

_aliases = {
    "in": "GifAnimator.images",
    "out": "GifAnimator.output",
    "odfs": "GifAnimator.odfs",
    "mask": "GifAnimator.mask",
    "alpha": "GifAnimator.background_opacity",
    "res": "GifAnimator.resolution",
    "box": "GifAnimator.bounding_box",
    "dir": "GifAnimator.camera_direction"
}

_flags = {
    "compress": (
        {'GifAnimator': {'compress': True}},
        "Compresses the output gif"
    )
}


class GifAnimator(MagicMonkeyBaseApplication):

    class ImageDirection(PyEnum):
        x = [1, 0, 0]
        y = [0, 1, 0]
        z = [0, 0, 1]
        nx = [-1, 0, 0]
        ny = [0, -1, 0]
        nz = [0, 0, -1]

    images = required_arg(
        MultipleArguments, traits_args=(Unicode,), default_value=None,
        description="List of images that will be transformed to one gif. They "
                    "must be supplied from background to foreground, and must "
                    "all abide to the same dimensions (except for the last "
                    "one). 3D images are treated as such. 4D images with are "
                    "processed following :\n"
                    "   - 1 element  : squeezed to a 3D image\n"
                    "   - 3 elements : a vector\n"
                    "   - 6 elements : a tensor\n"
                    "Timeseries are not handled by this application.\n"
                    "Note that ODF volumes must be given through the ODF "
                    "parameter of this application and will always be placed "
                    "at foreground."
    )

    odfs = Unicode(help="ODF volume to render to gif")

    mask = Unicode(help="Mask to apply on data")

    background_opacity = Float(
        1., help="Opacity of the background (from 0 to 1"
    ).tag(config=True)

    bounding_box = BoundingBox(allow_none=True).tag(config=True)

    resolution = Resolution().tag(config=True)

    camera_direction = Enum(
        ["x", "-x", "y", "-y", "z", "z"], ["-z"],
        help="Direction of view for the camera"
    ).tag(config=True)

    output = output_prefix_argument()

    compress = Bool(
        False, help="Compress the output gif image"
    ).tag(config=True)

    aliases = Dict(_aliases)
    flags = Dict(_flags)

    def _tensors2eigens(self, tensors, bbox):
        return compute_eigenvalues(tensors, bbox)

    def _get_actor_for_data(self, data, affine, bbox, opacity=1.):
        if len(data.shape) == 3:
            return actor.slicer(data[bbox], affine, opacity=opacity)
        elif data.shape[-1] == 3:
            return actor.peak_slicer(data[bbox], affine, opacity=opacity)
        elif data.shape[-1] == 6:
            return actor.tensor_slicer(
                *self._tensors2eigens(data, bbox), affine, opacity=opacity
            ) 

    def _get_actor_for_odfs(self, odf_img, bbox):
        return actor.odf_slicer(
            odf_img.get_fdata(), odf_img.affine, bbox, opacity=1.
        )

    def execute(self):
        back_img = nib.load(self.images[0])
        back_data = back_img.get_fdata().squeeze()

        proc_dir = mkdtemp()
        snapshots = []

        mask = nib.load(self.mask) if self.mask else np.ones_like(
            back_data
        ).astype(bool)

        bbox = self.bounding_box if self.bounding_box else list([
            e for t in zip(
                [0 for _ in range(len(back_data.shape))], back_data.shape
            ) for e in t
        ])

        back_data[~mask] = 0.

        scene = window.Scene()
        actors = [self._get_actor_for_data(
            back_data, back_img.affine, bbox, self.background_opacity
        )]

        self.images.pop(0)

        for img in self.images:
            nib_img = nib.load(img)
            data = nib_img.get_fdata().squeeze()
            data[~mask] = 0.
            actors.append(self._get_actor_for_data(data, nib_img.affine, bbox))

        if self.odfs:
            odfs = nib.load(self.odfs)
            actors.append(self._get_actor_for_odfs(odfs, bbox))

        camera_dir = self.ImageDirection[
            self.camera_direction.replace("-", "n")
        ]

        data_idx = np.argmax(np.absolute(camera_dir))
        data_dir = sum(camera_dir)
        data_start = bbox[2 * data_idx] \
            if data_dir > 0 else bbox[2 * data_idx + 1]
        data_end = bbox[2 * data_idx + 1] \
            if data_dir > 0 else bbox[2 * data_idx]

        for snap_ix, i in enumerate(range(data_start, data_end, data_dir)):
            extend = [None if j != 0 else i for j in camera_dir]
            for act in actors:
                act.display(extend)
                scene.add(act)

            scene.reset_camera()
            snapshots.append(join(proc_dir, "snap_{}.png".format(snap_ix)))
            window.record(
                scene, out_path=snapshots[-1],
                reset_camera=False, size=self.resolution
            )

        imageio.mimwrite(
            "{}.gif".format(self.output),
            [imageio.imread(im) for im in snapshots]
        )

        if self.compress:
            pygifsicle.optimize("{}.gif".format(self.output))
