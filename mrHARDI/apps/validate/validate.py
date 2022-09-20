from traitlets import Bool

from mrHARDI.base.application import (mrHARDIBaseApplication,
                                      output_prefix_argument)

class Validate(mrHARDIBaseApplication):
    name = u"mrHARDI data validator"

    subcommands = {
        "affine": "mrHARDI.apps.validate.AffineValidation",
        "dwi": "mrHARDI.apps.validate.DWIValidation"
    }
