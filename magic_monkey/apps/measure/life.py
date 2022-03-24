import nibabel as nib
import numpy as np
from dipy.core.gradients import gradient_table
from dipy.io.streamline import load_tractogram
from dipy.tracking.life import FiberModel
from traitlets import Bool, Float, List

from magic_monkey.base.application import (MagicMonkeyBaseApplication,
                                           required_file)


class Life(MagicMonkeyBaseApplication):
    name = u"Life Filtering"
    tracks = required_file(
        description="Input tractogram (readable by StatefulTractogram"
    )

    dwi = required_file(description="Diffusion weighted image")
    bvals = required_file(description="List of gradient b-values")
    bvecs = required_file(description="List of gradient b-vectors")

    response = List(
        Float(), [0.001, 0., 0.], 3, 3, help="Model signal response function"
    ).tag(config=True)

    cache_sphere = Bool(True)

    def execute(self):
        bvals, bvecs = np.loadtxt(self.bvals), np.loadtxt(self.bvecs)
        gtab = gradient_table(bvals, bvecs)

        data = nib.load(self.dwi)
        tracks = load_tractogram(self.tracks, data.get_fdata())

        kwargs = {
            "evals": self.response,
            "sphere": None if self.cache_sphere else False
        }

        model = FiberModel(gtab)
        model.fit(data.get_fdata(), tracks.streamlines, data.affine, **kwargs)

