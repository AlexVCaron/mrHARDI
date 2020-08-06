from os import chmod

import nibabel as nib

from traitlets import Instance, List, default, Unicode, Float

from magic_monkey.base.application import MagicMonkeyBaseApplication
from magic_monkey.config.topup import TopupConfiguration
from magic_monkey.config.algorithms.fsl import prepare_acqp_file

_aliases = dict(
    b0='Topup.b0',
    rev='Topup.rev',
    dwell='Topup.dwell',
    extra='Topup.extra_arguments',
    out='Topup.output_prefix'
)


class Topup(MagicMonkeyBaseApplication):
    configuration = Instance(TopupConfiguration).tag(config=True)
    output_prefix = Unicode(u'topup').tag(config=True)

    b0 = List(Unicode, []).tag(config=True, required=True)
    rev = List(Unicode, []).tag(config=True)
    dwell = Float().tag(config=True, required=True)

    extra_arguments = Unicode(u'').tag(config=True)

    aliases = _aliases
    classes = List()

    @default('classes')
    def _classes_default(self):
        return [Topup, self.__class__, TopupConfiguration]

    def initialize(self, argv=None):
        super().initialize(argv)
        self.configuration = TopupConfiguration(parent=self)

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
