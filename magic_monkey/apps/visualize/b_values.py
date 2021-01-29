import nibabel as nib
import numpy as np
from fury import actor, window

from traitlets import Dict, Unicode

from base.application import MagicMonkeyBaseApplication, input_dwi_prefix


_aliases = {
    "in": "BValuesVisualization.dwi",
    "bvals": "BValuesVisualization.bvals"
}


class BValuesVisualization(MagicMonkeyBaseApplication):
    dwi = input_dwi_prefix()
    bvals = Unicode(help="B-values corresponding to input diffusion").tag(
        config=True, required=True
    )

    aliases = Dict(default_value=_aliases)

    def execute(self):
        dwi = nib.load(self.dwi).get_fdata()
        bvals = np.loadtxt(self.bvals)
        ubvals, counts = np.unique(np.sort(bvals), return_counts=True)

        cols, rows = len(ubvals), counts.max()
        scene = window.Scene()
        scene.projection("parallel")
        val_range = (dwi[dwi > 0].min(), dwi.max())
        X, Y = dwi.shape[:2]
        center_x = int(X / 2)
        mid_slice = int(dwi.shape[2] / 2)
        border = 10

        lut = actor.colormap_lookup_table(
            val_range, [0, 0], [0, 0], [0, 1]
        )
        lut.SetNumberOfTableValues(200)
        lut.SetRampToSQRT()

        for j in range(cols):
            dwi_indexes = np.where(bvals == ubvals[j])[0]
            title = actor.text_3d(
                str(ubvals[j]),
                position=((X + border) * j + center_x, 0.5 * rows * (Y + border) + Y, 0),
                justification='center',
                font_size=24
            )
            scene.add(title)
            for i in range(counts[j]):
                act = actor.slicer(
                    dwi[..., dwi_indexes[i]], value_range=val_range, lookup_colormap=lut
                )

                act.SetInterpolate(False)
                act.display(None, None, mid_slice)
                act.SetPosition(
                    (X + border) * j,
                    0.5 * rows * (Y + border) - (Y + border) * i,
                    0
                )

                scene.add(act)

        scene.reset_camera()
        scene.zoom(1.0)
        window.show(scene, size=(1000, 1000))
