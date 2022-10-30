from os.path import isdir
from multiprocessing import cpu_count
from re import M
import nibabel as nib
import numpy as np
from traitlets import Bool, Instance, Integer, Unicode

from mrHARDI.base.application import (mrHARDIBaseApplication,
                                      output_prefix_argument,
                                      required_file)
from mrHARDI.base.shell import launch_shell_process
from mrHARDI.config.ants import AntsMultivariateTemplateConfiguration


_template_args = {
    "in": "AntsMultivariateTemplate.input_csv",
    "out": "AntsMultivariateTemplate.output",
    "ref": "AntsMultivariateTemplate.reference",
    "n": "AntsMultivariateTemplate.niter",
    "p": "AntsMultivariateTemplate.processes",
    "v": "AntsMultivariateTemplate.verbose"
}


class AntsMultivariateTemplate(mrHARDIBaseApplication):
    configuration = Instance(
        AntsMultivariateTemplateConfiguration
    ).tag(config=True)

    input_csv = required_file(
        description="Input CSV file. Each line refer to an "
                    "input image or set of images (separated "
                    "by a comma) to use to create the template")

    output = output_prefix_argument(None, allow_none=True, required=False)

    reference = Unicode(
        None, allow_none=True,
        help="Input reference to use to create the template"
    ).tag(config=True)

    niter = Integer(
        4, help="Number of iterations (gets multiplied "
                "by the number of images supplied)"
    ).tag(config=True)

    processes = Integer(cpu_count()).tag(config=True)
    verbose = Bool(False).tag(config=True)

    def execute(self):
        args = []
        im0 = np.loadtxt(
            self.input_csv, delimiter=",", dtype=str, max_rows=1
        )[0]
        args.append("-k {}".format(len(im0)))

        img = nib.load(im0[0])
        args.append("-d {}".format(len(img.shape)))

        log_prefix = ""
        if self.output:
            args.append("-o {}".format(self.output))
            log_prefix = self.output
            if isdir(self.output):
                log_prefix += "template"

        if self.reference:
            args.append("-z {}".format(self.reference))
        else:
            self.configuration.initial_rigid = True

        args.append(self.configuration.serialize(max(img.header.get_zooms())))

        launch_shell_process(
            "antsMultivariateTemplateConstruction2.sh {}".format(
                " ".join(args),
            ),
            log_prefix
        )
