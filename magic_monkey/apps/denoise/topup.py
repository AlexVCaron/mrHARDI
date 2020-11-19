from os import chmod

import numpy as np
from traitlets import Dict, Instance, Unicode, Enum, Bool
from traitlets.config.loader import ConfigError

from magic_monkey.base.application import (MagicMonkeyBaseApplication,
                                           MultipleArguments,
                                           output_prefix_argument,
                                           required_arg, required_file)
from magic_monkey.base.fsl import prepare_acqp_file, prepare_topup_index
from magic_monkey.base.dwi import load_metadata, save_metadata
from magic_monkey.config.topup import TopupConfiguration

_aliases = dict(
    b0s='Topup.b0_volumes',
    extra='Topup.extra_arguments',
    out='Topup.output_prefix',
    bvals='Topup.bvals',
    rev_bvals='Topup.rev_bvals'
)

_flags = dict(
    verbose=(
        {"Topup": {'verbose': True}},
        "activate verbose information output"
    )
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
    name = u"Topup"
    description = _description
    configuration = Instance(TopupConfiguration).tag(config=True)

    b0_volumes = required_file(
        description="Input b0 volumes to feed to Topup, with "
                    "reverse acquisitions inside the volume"
    )

    bvals = required_arg(
        MultipleArguments, [],
        "B-values of the volumes used for Topup correction",
        traits_args=(Unicode,)
    )

    rev_bvals = MultipleArguments(
        Unicode, [],
        help="B-values for the reverse acquisitions used for deformation "
             "correction, will be paired with same index b-values from the "
             "bvals argument. Acquisition direction will be determined "
             "inverting the related dataset one if none is supplied."
    ).tag(config=True, ignore_write=True)

    output_prefix = output_prefix_argument()

    final_bvals = Unicode(
        help="Bvalues of the final image on which Topup will be applied"
    ).tag(config=True)

    extra_arguments = Unicode(
        u'',
        help="Extra arguments to pass to topup, "
             "as a string, will be passed directly"
    ).tag(config=True)

    indexing_strategy = Enum(
        ["closest", "first"], "first",
        help="Strategy used to find which line in the .acqp aligns "
             "with which volume in the supplied dwi volume. For datasets "
             "with evenly spaced b0, \"closest\" will give the best result. "
             "In any other cases, or if you don't know, use \"first\""
    )

    verbose = Bool().tag(config=True)

    aliases = Dict(_aliases)
    flags = Dict(_flags)

    def execute(self):
        metadata = load_metadata(self.b0_volumes)

        acqp = prepare_acqp_file(
            metadata.dwell, metadata.directions
        )

        kwargs = dict(b0_comp=np.less) if self.configuration.strict else dict()

        bvals = [np.loadtxt(bvs) for bvs in self.bvals]
        rev_bvals = [np.loadtxt(bvs) for bvs in self.rev_bvals]
        bvals = np.ravel(np.column_stack((bvals, rev_bvals)))
        rev_bvals = np.ravel(np.column_stack(rev_bvals))

        indexes = prepare_topup_index(
            bvals, 1, strategy=self.indexing_strategy,
            ceil=self.configuration.ceil_value, **kwargs
        )

        if indexes.max() > len(acqp.split("\n")):
            if not len(acqp.split("\n")) == 2:
                raise ConfigError(
                    "No matching configuration found for index "
                    "(maxing at {}) "
                    "and acqp file (containing {} lines)\n{}".format(
                        indexes.max(), len(acqp), acqp
                    )
                )

            indexes[-len(rev_bvals):] = 2
            indexes[:len(indexes) - len(rev_bvals)] = 1

        metadata.topup_indexes = np.unique(indexes).tolist()

        used_indexes = 0
        for i, bvals in enumerate(self.bvals + self.rev_bvals):
            mt = load_metadata(bvals)
            mt.topup_indexes = [int(indexes[used_indexes])]
            save_metadata(
                "{}_topup_indexes".format(bvals.split(".")[0]), mt
            )
            used_indexes += mt.n

        with open("{}_acqp.txt".format(self.output_prefix), 'w+') as f:
            f.write(acqp)

        with open("{}_config.cnf".format(self.output_prefix), 'w+') as f:
            f.write(self.configuration.serialize())

        if self.verbose:
            if self.extra_arguments:
                self.extra_arguments += " --verbose"
            else:
                self.extra_arguments = "--verbose"

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
                    "{}_acqp.txt".format(self.output_prefix),
                    "{}_config.cnf".format(self.output_prefix),
                    "_results", "_field.nii.gz", ".nii.gz",
                    self.extra_arguments
                ))

        chmod("{}_script.sh".format(self.output_prefix), 0o0777)

        save_metadata(self.output_prefix, metadata)
