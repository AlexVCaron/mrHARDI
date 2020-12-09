from itertools import product

from dipy.core.gradients import gradient_table
from dipy.reconst.csdeconv import ConstrainedSphericalDeconvModel
from dipy.reconst.shm import SphHarmFit

from os.path import join, dirname
from tempfile import mkdtemp
from xml.etree import ElementTree as ET

import imageio
import pygifsicle
import nibabel as nib
import numpy as np

from dipy.data import get_sphere, default_sphere
from scilpy.utils.util import voxel_to_world, world_to_voxel

from traitlets import Unicode, Enum, Dict, Bool, Float, Integer
from enum import Enum as PyEnum

from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    required_arg, MultipleArguments, Resolution, output_prefix_argument, BoundingBox

from magic_monkey.compute.math.tensor import compute_eigenvalues

from fury import actor, window

_aliases = {
    "in": "GifAnimator.images",
    "out": "GifAnimator.output",
    "odfs": "GifAnimator.odfs",
    "bvals": "GifAnimator.bvals",
    "bvecs": "GifAnimator.bvecs",
    "response": "GifAnimator.response",
    "mask": "GifAnimator.mask",
    "alpha": "GifAnimator.background_opacity",
    "res": "GifAnimator.resolution",
    "box": "GifAnimator.bounding_box",
    "bdo": "GifAnimator.bdo_box",
    "dir": "GifAnimator.camera_direction",
    "dur": "GifAnimator.frame_duration",
    "loop": "GifAnimator.loop"
}

_flags = {
    "raw": (
        {'GifAnimator': {'compress': False}},
        "Disable output gif compression"
    ),
    "save-snaps": (
        {'GifAnimator': {'save_snapshots': True}},
        "Save snapshots to current directory"
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

    class AxisFlips(PyEnum):
        x = [1, 2, 0]
        y = [0, 2, 1]
        z = [0, 1, 2]
        nx = [1, 2, 0]
        ny = [0, 2, 1]
        nz = [0, 1, 2]

    class StridesFlip(PyEnum):
        x = [1, 1, 1]
        y = [-1, 1, 1]
        z = [1, 1, 1]
        nx = [1, 1, 1]
        ny = [-1, 1, 1]
        nz = [1, 1, 1]

    images = required_arg(
        MultipleArguments, traits_args=(Unicode(),),
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

    odfs = Unicode(help="ODF volume to render to gif").tag(config=True)
    bvals = Unicode(
        help="B-values, required to generate odfs model"
    ).tag(config=True)
    bvecs = Unicode(
        help="B-vectors, required to generate odfs model"
    ).tag(config=True)
    response = Unicode(
        help="Response function, required to generate odfs model"
    ).tag(config=True)

    mask = Unicode(help="Mask to apply on data").tag(config=True)

    background_opacity = Float(
        1., help="Opacity of the background (from 0 to 1"
    ).tag(config=True)

    bounding_box = BoundingBox(
        allow_none=True, help="Sextuplet [x,x,y,y,z,z] defining "
                              "the bounds of data in voxel space"
    ).tag(
        config=True, exclusive_group="bbox", group_index=0
    )

    bdo_box = Unicode(
        None, allow_none=True, help="MI-Brain bounding box (.bdo)"
    ).tag(
        config=True, exclusive_group="bbox", group_index=1
    )

    resolution = Resolution().tag(config=True)

    camera_direction = Enum(
        ["x", "nx", "y", "ny", "z", "nz"], "nz",
        help="Direction of view for the camera"
    ).tag(config=True)

    output = output_prefix_argument()

    frame_duration = Float(
        0.1, help="Number of seconds per frame"
    ).tag(config=True)

    loop = Integer(
        0, help="Number of cycles of the gif. If 0, "
                "the gif will cycle indefinitely"
    ).tag(config=True)

    compress = Bool(
        True, help="Compress the output gif image"
    ).tag(config=True)

    save_snapshots = Bool(
        False, help="Save snapshots to current direction"
    ).tag(config=True)

    aliases = Dict(default_value=_aliases)
    flags = Dict(default_value=_flags)

    def _tensors2eigens(self, tensors, bbox):
        mask = np.zeros(tensors.shape[:3])
        mask[bbox] = 1
        return compute_eigenvalues(
            tensors, mask.astype(bool),
            convention=(0, 1, 3, 2, 4, 5), reorder=False
        )

    def _align_snaps_to_z(self, data):
        return np.moveaxis(
            data, [0, 1, 2], self.AxisFlips[self.camera_direction].value
        )

    def _get_actor_for_data(self, data, affine, bbox, opacity=1.):
        strides = np.sign(np.diag(affine))[:3]
        strides[-1] *= -1
        strides *= self.StridesFlip[self.camera_direction].value
        if len(data.shape) == 3:
            dt = self._align_snaps_to_z(data[bbox])
            act = actor.slicer(
                dt, opacity=opacity, interpolation='nearest',
                value_range=((dt[dt > 0]).min(), (dt[dt > 0]).max())
            )
            return act
        elif data.shape[-1] == 3:
            if not np.issubdtype(data.dtype, np.integer):
                if len(data.shape) == 4:
                    data = data[..., None, :]
                dt = self._align_snaps_to_z(data[bbox] * strides)
                return actor.peak_slicer(
                    dt, opacity=opacity, linewidth=1,
                    colors=np.absolute(dt).squeeze(), lod=False
                )
            else:
                act = actor.slicer(
                    self._align_snaps_to_z(data[bbox])
                )
                return act
        elif data.shape[-1] == 6:
            evals, evecs = self._tensors2eigens(data, bbox)
            evecs *= strides[:, None]
            evecs = self._align_snaps_to_z(evecs[bbox])
            # fa = compute_fa(
            #     (np.flip(evals[bbox], -1), None),
            #     np.ones(evals[bbox].shape[:3]).astype(bool)
            # )
            # cfa = color(fa, np.moveaxis(np.flip(evecs[bbox, 0], -1), -2, -1))
            return actor.tensor_slicer(
                self._align_snaps_to_z(evals[bbox]), evecs,
                scale=0.4, scalar_colors=np.absolute(evecs[..., -1]),
                opacity=opacity, sphere=get_sphere('symmetric724')
            )

    def _get_actor_for_odfs(self, odfs):
        odfs = self._align_snaps_to_z(odfs)
        return actor.odf_slicer(
            odfs, opacity=1., scale=1., sphere=default_sphere, colormap='Wistia'
        )

    def _load_bdo_bounds(self, mask, mask_affine):
        xml_box = ET.parse(self.bdo_box).getroot()
        assert xml_box.get("type") == "Cuboid"
        origin = xml_box.find("origin")
        origin = [origin.get("x"), origin.get("y"), origin.get("z")]
        origin = np.array([float(p.replace(",", ".")) for p in origin])
        bdo_affine = xml_box.find("WorldTransformMatrix")
        bdo_affine = np.array([
            [
                float(ch.get("col{}".format(i + 1)).replace(",", "."))
                for i in range(3)
            ] for ch in bdo_affine
        ])
        bdo_affine = np.hstack((bdo_affine, origin[:, None]))
        bdo_affine = np.vstack((bdo_affine, [[0., 0., 0., 1.]]))

        world_corners = np.array([
            voxel_to_world(c, bdo_affine)
            for c in product([-1., 1.], [-1., 1.], [-1., 1.])
        ])

        world_corners = np.sort(
            np.vstack((world_corners.min(0),  world_corners.max(0))), axis=0
        )

        mask_affine[0, 0] *= -1.
        mask_affine[-1, 0] *= -1.
        mask_affine[1, 1] *= -1.
        mask_affine[-1, 1] *= -1.

        bbox = self._get_bbox_from_corners(world_corners, mask_affine)

        mask = self._compute_mask_on_box(bbox, bdo_affine, mask, mask_affine)

        return bbox, mask

    def _get_bbox_from_corners(self, corners, affine):
        return np.sort(np.vstack((
            world_to_voxel(corners[0], affine),
            world_to_voxel(corners[1], affine)
        )), axis=0).T.flatten()

    def _compute_mask_on_box(
        self, bbox, corners_affine, mask, mask_affine
    ):
        box_mask = np.zeros_like(mask).astype(bool)

        slicer = [slice(bbox[i], bbox[i + 1]) for i in range(0, len(bbox), 2)]
        for ix in np.moveaxis(
            np.mgrid[slicer], 0, -1
        ).reshape((-1, 3)).tolist():
            pt = world_to_voxel(
                voxel_to_world(ix, mask_affine), corners_affine
            )

            if np.all([
                -1. <= pt[0] <= 1.,
                -1. <= pt[1] <= 1.,
                -1. <= pt[2] <= 1.
            ]):
                box_mask[tuple(ix)] = True

        return mask & box_mask

    def _flip_to_background(self, data, affine, strides, ref_strides):
        to_flip = [s != rs for s, rs in zip(strides, ref_strides)]
        flips = [-1 if flip else 1 for flip in to_flip]
        affine[:3, :3] = np.diag(np.diag(affine)[:3] * flips)
        for i, flip in enumerate(to_flip):
            if flip:
                data = np.flip(data, i)

        return data, affine

    def _flip_bvecs_to_background(self, bvecs, strides, ref_strides):
        to_flip = [s != rs for s, rs in zip(strides, ref_strides)]
        for i, flip in enumerate(to_flip):
            if flip:
                bvecs[i] = -bvecs[i]

        return bvecs

    def execute(self):
        back_img = nib.load(self.images[0])
        back_data = back_img.get_fdata().astype(
            back_img.get_data_dtype()
        ).squeeze()
        back_stride = np.sign(np.diag(back_img.affine))[:3]

        if self.save_snapshots:
            proc_dir = mkdtemp(prefix="snapshots", dir=dirname(self.output))
        else:
            proc_dir = mkdtemp()

        snapshots = []

        mask = nib.load(self.mask).get_fdata().astype(bool) \
            if self.mask else np.ones_like(back_data, dtype=bool)

        if self.bdo_box:
            bbox, mask = self._load_bdo_bounds(mask, back_img.affine)
        elif self.bounding_box:
            bbox = self.bounding_box
        else:
            bbox = list([
                e for t in zip(
                    [0 for _ in range(len(back_data.shape))], back_data.shape
                ) for e in t
            ])

        slicer = tuple(
            slice(bbox[i], bbox[i + 1]) for i in range(0, len(bbox), 2)
        )

        back_data[~mask] = 0.

        # back_data, _ = self._flip_to_background(back_data, back_img.affine, back_stride, [-1, -1, 1])
        scene = window.Scene()
        actors = [self._get_actor_for_data(
            back_data, back_img.affine, slicer, self.background_opacity
        )]

        self.images.pop(0)

        for img in self.images:
            nib_img = nib.load(img)
            data = nib_img.get_fdata().squeeze()
            affine = nib_img.affine
            data, affine = self._flip_to_background(
                data, affine,
                np.sign(np.diag(nib_img.affine))[:3],
                back_stride
            )
            data, _ = self._flip_to_background(data, affine,
                                                    np.sign(np.diag(affine))[:3], [-1, -1, 1])
            data[~mask] = 0.
            actors.append(self._get_actor_for_data(
                data.astype(nib_img.get_data_dtype()), affine, slicer
            ))

        if self.odfs:
            coeffs = nib.load(self.odfs)
            affine = coeffs.affine
            strides = np.sign(np.diag(affine))[:3]
            data, affine = self._flip_to_background(
                coeffs.get_fdata(), affine, strides, back_stride
            )
            order = int((-3 + np.sqrt(9 + 8 * (1 + data.shape[-1] - 1))) / 2)
            bvals, bvecs = np.loadtxt(self.bvals), np.loadtxt(self.bvecs)
            #bvecs = self._flip_bvecs_to_background(bvecs, strides, back_stride)
            response = np.loadtxt(self.response)
            model = ConstrainedSphericalDeconvModel(
                gradient_table(bvals, bvecs),
                (response[:3], response[3]),
                sh_order=order
            )
            data = data[slicer]
            fit = SphHarmFit(model, data, np.ones_like(data).astype(bool))
            actors.append(
                self._get_actor_for_odfs(fit.odf(default_sphere))
            )

        camera_dir = self.ImageDirection[self.camera_direction].value

        data_idx = np.argmax(np.absolute(camera_dir))
        data_dir = sum(camera_dir)
        data_start = 0 if data_dir > 0 else \
            bbox[2 * data_idx + 1] - bbox[2 * data_idx] - 1
        data_end = bbox[2 * data_idx + 1] - bbox[2 * data_idx] \
            if data_dir > 0 else -1

        for snap_ix, i in enumerate(range(data_start, data_end, data_dir)):
            for act in actors:
                scene.add(act)
                act.display(None, None, i)


            # scene.set_camera(
            #     position=actors[0].GetCenter() - np.array(camera_dir) * (np.array(actors[0].GetCenter()) + displacement),
            #     focal_point=actors[0].GetCenter(),
            #     view_up=self.ViewUp[self.camera_direction].value
            # )
            scene.reset_clipping_range()
            scene.reset_camera()
            snapshots.append(join(proc_dir, "snap_{}.png".format(snap_ix)))
            window.show(scene, size=self.resolution, reset_camera=False,)
            window.snapshot(
                scene, snapshots[-1], size=self.resolution
            )
            # scene.rm_all()

        imageio.mimwrite(
            "{}.gif".format(self.output),
            [imageio.imread(im) for im in snapshots],
            duration=self.frame_duration, loop=self.loop,
            format="GIF-FI", quantizer="nq"
        )

        if self.compress:
            try:
                pygifsicle.optimize("{}.gif".format(self.output))
            except FileNotFoundError as e:
                print(e)
                print("Gifsicle must be installed to enable compression")
                print("On linux run : apt-get install gifsicle")
