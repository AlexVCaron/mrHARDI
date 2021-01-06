from enum import Enum as PyEnum

import nibabel as nib
import numpy as np

from dipy.segment.mask import crop, bounding_box
from fury import actor, window
from fury.window import Scene

from traitlets import Unicode, Float, Integer, Dict, Bool, List, Enum

from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    output_prefix_argument, MultipleArguments

_aliases = {
    "in": "Mosaic.images",
    "out": "Mosaic.output",
    "back": "Mosaic.background",
    "mask": "Mosaic.mask",
    "fo": "Mosaic.front_opacity",
    "fb": "Mosaic.back_opacity",
    "begin": "Mosaic.begin",
    "end": "Mosaic.end",
    "stride": "Mosaic.stride",
    "border": "Mosaic.border_thickness",
    "length": "Mosaic.length",
    "res": "Mosaic.length_resolution",
    "hue": "Mosaic.hue",
    "sat": "Mosaic.saturation",
    "val": "Mosaic.value",
    "ramp": "Mosaic.ramp",
    "scale": "Mosaic.scale",
    "std": "Mosaic.n_std",
    "lbp": "Mosaic.label_precision",
    "lbn": "Mosaic.n_labels"
}

_flags = dict(
    indiv_bar=(
        {"Mosaic": {"separate_colorbars": True}},
        "Produce a colorbar for each mosaic"
    ),
    norm=(
        {"Mosaic": {"normalize": True}},
        "Normalize the images"
    ),
    larger_on_side=(
        {"Mosaic": {"larger_on_side": True}},
        "Puts the larger side of the mosaic on the rows"
    ),
    back_unmask=(
        {"Mosaic": {"mask_background": False}},
        "Disables masking on the background image"
    ),
    no_crop=(
        {"Mosaic": {"mask_crop": False}},
        "Disable cropping X and Y axes to mask shape"
    ),
    top_down=(
        {"Mosaic": {"left_right": False}},
        "Lay the mosaics top -> down instead of left -> right"
    ),
    no_bar=(
        {"Mosaic": {"colorbar": False}},
        "Disable the display of a colorbar"
    ),
    bottom_bar=(
        {"Mosaic": {"vertical_colorbar": False}},
        "Put the colorbar at the bottom of the mosaic"
    ),
    color_range=(
        {"Mosaic": {"color_around_mean": False}},
        "Color on the range of values of the image instead of around the mean"
    ),
    rgb=(
        {"Mosaic": {"is_rgb": True, "colorbar": True}},
        "Specify that input volumes are RGB"
    )
)


class Mosaic(MagicMonkeyBaseApplication):
    _ramp_functional = dict(
        linear=lambda lut: lut.SetRampToLinear(),
        sqrt=lambda lut: lut.SetRampToSQRT(),
        scurve=lambda lut: lut.SetRampToSCurve()
    )

    _scale_functional = dict(
        linear=lambda lut: lut.SetScaleToLinear(),
        log=lambda lut: lut.SetScaleToLog10()
    )

    images = MultipleArguments(
        Unicode(), [],
        help="Volumes to lay into mosaic. All images must have the same "
             "contrasts, since the lut table is calculated on the range of "
             "values across all images. They will each be put in mosaics "
             "side to side (or bottom to top)."
    ).tag(config=True, required=True)
    background = MultipleArguments(
        Unicode(), [],
        help="Background volumes, common to all input images"
    ).tag(config=True)
    mask = Unicode(
        help="Mask for the input image. Only data inside the "
             "mask will be rendered, the rest will be overwritten "
             "to 0. Start and end bounds will be fitted to the mask "
             "bounds if they bleed outside of it."
    ).tag(config=True)

    front_opacity = Float(1., help="Opacity of the background image").tag(
        config=True
    )
    back_opacity = Float(1., help="Opacity of the background image").tag(
        config=True
    )
    mask_background = Bool(True, help="Masks the background to 0").tag(
        config=True
    )
    mask_crop = Bool(True, help="Crop X and Y axes to limits of mask").tag(
        config=True
    )

    hue = List(Float(), [0., 0.]).tag(config=True)
    saturation = List(Float(), [0., 0.]).tag(config=True)
    value = List(Float(), [0., 1.]).tag(config=True)

    ramp = Enum(
        ["linear", "sqrt", "scurve"], "linear",
        help="Set the ramp function for the actor lookup table"
    ).tag(config=True)
    scale = Enum(
        ["linear", "log"], "linear",
        help="Set the scale function for the actor lookup table"
    ).tag(config=True)

    normalize = Bool(False).tag(config=True)

    begin = Integer(0, help="First slice").tag(config=True)
    stride = Integer(1, help="Skip of slices").tag(config=True)
    end = Integer(help="Last slice").tag(config=True)

    border_thickness = Integer(
        10, help="Thickness of the border between images"
    ).tag(config=True)
    length = Integer(
        10, help="Number of elements on one side of the output mosaic"
    ).tag(config=True)
    length_resolution = Integer(
        2000, help="Resolution of the side of the mosaic "
                   "determined by the length argument"
    ).tag(config=True)
    larger_on_side = Bool(
        False, help="Place the larger side of the mosaic "
                    "on the rows instead of the columns"
    ).tag(config=True)
    left_right = Bool(True, help="Lay the mosaics from left to right").tag(
        config=True
    )
    colorbar = Bool(True, help="Display a colorbar with the mosaic").tag(
        config=True
    )
    color_around_mean = Bool(True, help="Color the image around the mean").tag(
        config=True
    )
    separate_colorbars = Bool(False, help="Produce a colorbar per mosaic").tag(
        config=True
    )
    is_rgb = Bool(False).tag(config=True)
    vertical_colorbar = Bool(True).tag(config=True)
    label_precision = Integer(3).tag(config=True)
    n_labels = Integer(5).tag(config=True)
    n_std = List(
        Float(), [0.5, 1.5], help="Number of standard deviations "
                                  "around the mean to display"
    ).tag(
        config=True
    )

    output = output_prefix_argument()

    aliases = Dict(default_value=_aliases)
    flags = Dict(default_value=_flags)

    _cache = {
        "imgs": [],
        "back": [],
        "back_actors": [],
        "front_actors": [],
        "lut": []
    }

    def _crop_images_to_mask(self):
        if "mask" in self._cache:
            bmin, bmax = bounding_box(self._cache["mask"].astype(int))
            self._cache["mask"] = crop(self._cache["mask"], bmin, bmax)
        else:
            bmin, bmax = bounding_box(self._cache["imgs"][0])

        for i, img in enumerate(self._cache["imgs"]):
            self._cache["imgs"][i] = crop(img, bmin, bmax)

        if "back" in self._cache:
            for i, img in enumerate(self._cache["back"]):
                self._cache["back"][i] = crop(img, bmin, bmax)

        self.begin = int(self.begin - bmin[-1])
        self.end = int(self.end - bmin[-1])
        self.end = int(min(self.end, bmax[-1]))

    def _mask_outside_mask(self):
        if "mask" in self._cache:
            mask = self._cache["mask"]
            for i, img in enumerate(self._cache["imgs"]):
                img[~mask] = 0
                self._cache["imgs"][i] = img

            for i, img in enumerate(self._cache["back"]):
                img[~mask] = 0
                self._cache["back"][i] = img

    def _create_back_actor(self):
        if "back" in self._cache:
            for back in self._cache["back"]:
                self._cache["back_actors"].append(
                    actor.slicer(back, opacity=self.back_opacity)
                )

    def _get_global_values_range(self):
        mins, maxs = [], []
        for img in self._cache["imgs"]:
            values = self._get_values_range(img)
            mins.append(values[0])
            maxs.append(values[1])

        return min(mins), max(maxs)

    def _get_values_range(self, img):
        values = (img[img > 0].min(), img.max())
        if self.color_around_mean:
            mean, std = img[img > 0].mean(), img[img > 0].std()
            values = (
                max(values[0], mean - self.n_std[0] * std),
                min(values[1], mean + self.n_std[1] * std)
            )

        return values

    def _get_lut_table(self, value_range):
        lut = actor.colormap_lookup_table(
            value_range, self.hue, self.saturation, self.value
        )
        lut.SetNumberOfTableValues(200)
        self._ramp_functional[self.ramp](lut)
        self._scale_functional[self.scale](lut)
        return lut

    def _compute_lut(self):
        if not self.is_rgb:
            if not self.separate_colorbars:
                values = self._get_global_values_range()
                self._cache["lut"].append(self._get_lut_table(values))
            else:
                for img in self._cache["imgs"]:
                    values = self._get_values_range(img)
                    self._cache["lut"].append(self._get_lut_table(values))

    def _get_cache_lut(self, index):
        if self.separate_colorbars:
            return self._cache["lut"][index]
        return self._cache["lut"][0]

    def _create_front_actors(self):
        for i, img in enumerate(self._cache["imgs"]):
            lut = None
            if not self.is_rgb:
                lut = actor.colormap_lookup_table(
                    (0., 255.), self.hue, self.saturation, self.value
                )
                lut.SetNumberOfTableValues(
                    self._get_cache_lut(i).GetNumberOfTableValues()
                )
                self._ramp_functional[self.ramp](lut)
                self._scale_functional[self.scale](lut)
                lut.Build()
            self._cache["front_actors"].append(actor.slicer(
                img,
                opacity=self.front_opacity,
                lookup_colormap=lut
            ))

    def _get_z_bounds(self):
        start = self.begin
        end = self.end if self.end else max(
            act.shape[2] for act in self._cache["front_actors"]
        )

        if "mask" in self._cache:
            mask = self._cache["mask"]
            has_data = np.where(np.apply_along_axis(
                np.any, axis=0, arr=mask.reshape((-1, mask.shape[-1]))
            ))
            start = max(start, has_data[0].min())
            end = min(end, has_data[-1].max() + 1)

        return start, end

    def _get_xy_bounds(self):
        xy = np.array([act.shape[:2] for act in self._cache["front_actors"]])
        return xy[:, 0].max(), xy[:, 1].max()

    def _get_n_mosaics(self):
        return len(self._cache["imgs"])

    def _generate_mosaic(
        self, scene, n, rows, cols, cnt, start_x, start_y, X, Y, Z
    ):
        border = self.border_thickness
        front_actor = self._cache["front_actors"][n]
        for j in range(rows):
            for i in range(cols):
                pos = (
                    start_x + (X + border) * i,
                    cols * (Y + border) - (Y + border) * j + start_y,
                    0
                )

                for act in self._cache["back_actors"]:
                    back_mosaic = act.copy()
                    back_mosaic.display(None, None, cnt)
                    back_mosaic.SetPosition(pos)
                    back_mosaic.SetInterpolate(False)
                    scene.add(back_mosaic)

                pos = pos[:2] + (0.5,)

                front_mosaic = front_actor.copy()
                front_mosaic.display(None, None, cnt)
                front_mosaic.SetPosition(pos)
                front_mosaic.SetInterpolate(False)
                scene.add(front_mosaic)

                cnt += self.stride
                if cnt > Z:
                    break

            if cnt > Z:
                break

    def execute(self):
        for image in self.images:
            img = nib.load(image)
            data = img.get_fdata().astype(img.get_data_dtype())
            if self.normalize:
                data = (data - data.min()) / (data.max() - data.min())
            self._cache["imgs"].append(data)

        if self.mask:
            self._cache["mask"] = nib.load(self.mask).get_fdata().astype(bool)

        if self.background:
            for back in self.background:
                bck = nib.load(back)
                self._cache["back"].append(bck.get_fdata().astype(
                    bck.get_data_dtype()
                ))

        self._mask_outside_mask()

        if self.mask_crop:
            self._crop_images_to_mask()

        self._create_back_actor()
        self._compute_lut()
        self._create_front_actors()
        start, end = self._get_z_bounds()

        X, Y, Z = self._get_xy_bounds() + (end,)

        rows = int(np.ceil((end - start) / (self.stride * self.length)))
        cols = self.length
        res = (
            int(np.ceil(cols / rows * self.length_resolution)),
            self.length_resolution
        )

        if rows > cols and not self.larger_on_side:
            cols, rows = rows, cols
            res = res[::-1]
        elif cols > rows and self.larger_on_side:
            cols, rows = rows, cols
            res = res[::-1]

        if self.left_right:
            res = (res[0] * self._get_n_mosaics(), res[1])
        else:
            res = (res[0], res[1] * self._get_n_mosaics())

        scene = Scene()
        scene.projection("parallel")
        border = self.border_thickness
        num_mosaics = self._get_n_mosaics()

        for n in range(self._get_n_mosaics()):
            cnt = start
            start_x, start_y = 0, 0
            if self.left_right:
                start_x = n * (cols * (X + border) + 2 * border)
            else:
                start_y = (num_mosaics - n) * (rows * (Y + border) + 2 * border)

            self._generate_mosaic(
                scene, n, rows, cols, cnt, start_x, start_y, X, Y, Z
            )

        scene.reset_camera_tight(1.2)

        if self.colorbar:
            n_bars = len(self._cache["lut"])
            bounds = scene.ComputeVisiblePropBounds()
            for i, lut in enumerate(self._cache["lut"]):
                bar_to_horizontal = (
                    not self.vertical_colorbar or
                    (n_bars > 1 and self.left_right)
                )
                if bar_to_horizontal:
                    p0 = ((bounds[0] + i * border / res[0]) + i / n_bars, 0.01)
                    p1 = (1. / n_bars, 0.1)
                else:
                    p0 = (0.9, ((bounds[2] + i * border) / res[1]) + i / n_bars)
                    p1 = (0.1, 1. / n_bars)

                print("Bar pos {}, size {}".format(p0, p1))

                bar = actor.scalar_bar(lut)
                bar.SetPosition(*p0)
                bar.SetPosition2(*p1)
                bar.SetLabelFormat("%6.{}f".format(self.label_precision))
                bar.SetMaximumNumberOfColors(60)
                bar.SetNumberOfLabels(self.n_labels)
                if bar_to_horizontal:
                    bar.SetOrientationToHorizontal()
                scene.add(bar)

        # scene.reset_camera_tight(1.2)
        # scene.zoom(1.)
        # window.show(scene, size=res, reset_camera=False)
        window.snapshot(scene, self.output, res)
