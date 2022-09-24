import nibabel as nib
import numpy as np
from traitlets import Bool, Dict

from mrHARDI.base.application import (mrHARDIBaseApplication,
                                      output_prefix_argument,
                                      required_file)
from mrHARDI.compute.utils import validate_affine


_aliases = {
    "in": "AffineValidation.image",
    "ref": "AffineValidation.reference",
    "out": "AffineValidation.output"
}

_flags = dict(
    stdout=(
        {"AffineValidation": {"output_stdout": True}},
        "Redirect output information to stdout (else quiet)"
    )
)

class AffineValidation(mrHARDIBaseApplication):
    image = required_file(description="Input image to compare")
    reference = required_file(description="Reference image for the comparison")
    output = output_prefix_argument(required=False)
    output_stdout = Bool(False).tag(config=True)

    aliases = Dict(default_value=_aliases)
    flags = Dict(default_value=_flags)
    

    def execute(self):
        img = nib.load(self.image)
        ref = nib.load(self.reference)
        is_similar, aff = validate_affine(img.affine, ref.affine, img.shape)

        if self.output_stdout:
            if not is_similar:
                print("Error : images have different affine\n")

        if self.output:
            if is_similar:
                np.savetxt(aff, "{}_correct_affine.txt".format(self.output))
            else:
                t1, t2 = img.affine[:3, -1], ref.affine[:3, -1]
                rx1, rx2 = img.affine[0, :3], ref.affine[0, :3]
                ry1, ry2 = img.affine[1, :3], ref.affine[1, :3]
                rz1, rz2 = img.affine[2, :3], ref.affine[2, :3]
                with open(
                    "{}_affine_components.txt".format(self.output), "w+"
                ) as f:
                    f.writelines([
                        "Component,x1,y1,z1,x2,y2,z2",
                        "T,{},{},{}".format(*t1, *t2),
                        "Rx,{},{},{}".format(*rx1, *rx2),
                        "Ry,{},{},{}".format(*ry1, *ry2),
                        "Rz,{},{},{}".format(*rz1, *rz2)
                    ])
