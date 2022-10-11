from traitlets import Bool

from mrHARDI.base.application import (mrHARDIBaseApplication,
                                      output_prefix_argument)

class Validate(mrHARDIBaseApplication):
    name = u"mrhardi validate"

    subcommands = {
        "affine": (
            "mrHARDI.apps.validate.AffineValidation",
            "Validate spatial alignment of two images"
        ),
        "dwi": (
            "mrHARDI.apps.validate.DWIValidation",
            "Validate acquisition parameters of a DWI acquisition"
        )
    }
