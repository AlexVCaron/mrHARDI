import re
from copy import deepcopy

import nibabel as nib
import numpy as np
from traitlets import Instance, Unicode, Dict
from traitlets.config import Config

from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    required_file, output_prefix_argument
from magic_monkey.base.dwi import load_metadata, save_metadata
from magic_monkey.compute.b0 import extract_b0, squash_b0
from magic_monkey.config.utils import B0UtilsConfiguration

_b0_aliases = {
    'in': 'B0Utils.image',
    'bvals': 'B0Utils.bvals',
    'bvecs': 'B0Utils.bvecs',
    'out': 'B0Utils.output_prefix'
}
_b0_description = """
Utility program used to either extract B0 from a diffusion-weighted image or 
squash those B0 and output the resulting image.
"""


class B0Utils(MagicMonkeyBaseApplication):
    name = u"B0 Utilities"
    description = _b0_description
    configuration = Instance(B0UtilsConfiguration).tag(config=True)

    image = required_file(description="Input dwi image")
    bvals = required_file(description="Input b-values")
    bvecs = Unicode(help="Input b-vectors").tag(config=True, ignore_write=True)

    output_prefix = output_prefix_argument()

    aliases = Dict(default_value=_b0_aliases)

    def initialize(self, argv=None):
        assert argv and len(argv) > 0
        if not (
            any("help" in a for a in argv) or
            any("out-config" in a for a in argv) or
            any("safe" in a for a in argv)
        ):
            command, argv = argv[0], argv[1:]
            assert re.match(r'^\w(-?\w)*$', command), \
                "First argument must be the sub-utility to use {}".format(
                    B0UtilsConfiguration.current_util.values
                )
            super().initialize(argv)

            config = deepcopy(self.config)
            if 'B0UtilsConfiguration' in config:
                config['B0UtilsConfiguration'].update(
                    Config(current_util=command)
                )
            else:
                config['B0UtilsConfiguration'] = Config(current_util=command)
            self.update_config(config)
        else:
            super().initialize(argv)

    def _example_command(self, sub_command=""):
        return "magic_monkey {} [extract|squash] <args> <flags>".format(
            sub_command
        )

    def execute(self):
        if self.configuration.current_util == "extract":
            self._extract_b0()
        elif self.configuration.current_util == "squash":
            self._squash_b0()
        else:
            self.print_help()

    def _extract_b0(self):
        in_dwi = nib.load(self.image)
        bvals = np.loadtxt(self.bvals)
        kwargs = dict(b0_comp=np.less) if self.configuration.strict else dict()
        metadata = load_metadata(self.image)
        kwargs["metadata"] = metadata

        data = extract_b0(
            in_dwi.get_fdata().astype(in_dwi.get_data_dtype()), bvals,
            self.configuration.strides,
            self.configuration.get_mean_strategy_enum(),
            self.configuration.ceil_value,
            **kwargs
        )

        if metadata:
            save_metadata(self.output_prefix, metadata)

        out_dtype = in_dwi.get_data_dtype()
        if self.configuration.dtype:
            out_dtype = self.configuration.dtype

        img = nib.Nifti1Image(
            data.astype(out_dtype),
            in_dwi.affine, in_dwi.header
        )
        img.set_data_dtype(out_dtype)

        nib.save(img, "{}.nii.gz".format(self.output_prefix))

    def _squash_b0(self):
        in_dwi = nib.load(self.image)
        bvals = np.loadtxt(self.bvals)
        kwargs = dict(b0_comp=np.less) if self.configuration.strict else dict()
        metadata = load_metadata(self.image)
        kwargs["metadata"] = metadata

        bvecs = np.loadtxt(self.bvecs) if self.bvecs else None

        data, bvals, bvecs = squash_b0(
            in_dwi.get_fdata().atype(in_dwi.get_data_dtype()), bvals, bvecs,
            self.configuration.get_mean_strategy_enum(),
            self.configuration.ceil_value,
            **kwargs
        )

        if metadata:
            save_metadata(self.output_prefix, metadata)

        out_dtype = in_dwi.get_data_dtype()
        if self.configuration.dtype:
            out_dtype = self.configuration.dtype

        img = nib.Nifti1Image(
            data.astype(out_dtype),
            in_dwi.affine, in_dwi.header
        )
        img.set_data_dtype(out_dtype)

        nib.save(img, "{}.nii.gz".format(self.output_prefix))

        np.savetxt("{}.bval".format(self.output_prefix), bvals, fmt="%d")

        if self.bvecs:
            np.savetxt(
                "{}.bvec".format(self.output_prefix), bvecs, fmt="%.6f"
            )
