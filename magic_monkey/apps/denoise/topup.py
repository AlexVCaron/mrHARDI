from os import chmod

import nibabel as nib
from traitlets import Dict, Instance, Unicode

from magic_monkey.base.application import (MagicMonkeyBaseApplication,
                                           MultipleArguments,
                                           output_prefix_argument,
                                           required_arg,
                                           required_number)
from magic_monkey.base.fsl import prepare_acqp_file
from magic_monkey.config.topup import TopupConfiguration

_aliases = dict(
    b0='Topup.b0',
    rev='Topup.rev',
    dwell='Topup.dwell',
    extra='Topup.extra_arguments',
    out='Topup.output_prefix'
)

_description = """
Command-line utility used to parametrize and create scripts performing topup 
correction on b0 volumes. For more information on the parameters available for 
the topup executable, please refer to the website [1].

References :
------------
[1] https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/topup
[Andersson 2003] J.L.R. Andersson, S. Skare, J. Ashburner. How to correct 
                 susceptibility distortions in spin-echo echo-planar images: 
                 application to diffusion tensor imaging. NeuroImage, 
                 20(2):870-888, 2003.
"""


class Topup(MagicMonkeyBaseApplication):
    description = _description
    configuration = Instance(TopupConfiguration).tag(config=True)

    b0 = required_arg(
        MultipleArguments, [],
        "Principal B0 volumes used for Topup correction",
        traits_args=(Unicode,)
    )
    rev = MultipleArguments(
        Unicode, [],
        help="Reverse acquisitions used for deformation correction"
    ).tag(config=True, ignore_write=True)
    dwell = required_number(
        description="Dwell time of the acquisitions", ignore_write=False
    )

    output_prefix = output_prefix_argument()

    extra_arguments = Unicode(
        u'',
        help="Extra arguments to pass to topup, "
             "as a string, will be passed directly"
    ).tag(config=True)

    aliases = Dict(_aliases)

    def _start(self):
        ap_shapes = [nib.load(b0).shape for b0 in self.b0]
        pa_shapes = [nib.load(b0).shape for b0 in self.rev]

        acqp = prepare_acqp_file(ap_shapes, pa_shapes, self.dwell)

        with open("{}_acqp.txt".format(self.output_prefix), 'w+') as f:
            f.write("# MAGIC MONKEY -------------------------\n")
            f.write("# Autogenerated acquisition parameters file\n\n")
            f.write(acqp)

        with open("{}_config.cnf".format(self.output_prefix), 'w+') as f:
            f.write("# MAGIC MONKEY -------------------------\n")
            f.write("# Autogenerated Topup configuration file\n\n")
            f.write(self.configuration.serialize())

        with open("{}_script.sh".format(self.output_prefix), 'w+') as f:
            f.write("#!/usr/bin/env bash\n\n")
            f.write("# MAGIC MONKEY -------------------------\n")
            f.write("# Autogenerated Topup script\n\n")

            f.write("in_b0=$1\n")
            f.write("out_prefix=$2\n")
            f.write("echo \"Running topup on $1\\n\"\n")
            f.write(
                "topup --imain=\"$in_b0\" --datain={1} --config={2} "
                "--out=\"{0}{3}\" --fout=\"{0}{4}\" "
                "--iout=\"{0}{5}\" {6}\n".format(
                    "${out_prefix}",
                    "{}_params.txt".format(self.output_prefix),
                    "{}_config.cnf".format(self.output_prefix),
                    "_topup_results.txt", "_topup_field.nii.gz", ".nii.gz",
                    self.extra_arguments
                ))

        chmod("{}_script.sh".format(self.output_prefix), 0o0777)
