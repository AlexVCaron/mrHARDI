import numpy as np
from traitlets import Dict, Instance, Unicode, default

from fury import window, actor

from magic_monkey.base.application import (MagicMonkeyBaseApplication,
                                           required_file)
from magic_monkey.compute.bshells import get_bshells_voronoi
from magic_monkey.config.acquisition import TriangulationConfiguration

_description = """
Small utility optimizing an acquisition protocol (b-vectors mainly for now) 
on a nextflow pipeline.
"""

_aliases = dict(
    bvals='AcquisitionOptimizer.bvals',
    bvecs='AcquisitionOptimizer.bvecs',
    # dwi='AcquisitionOptimizer.dwi',
    # rev='AcquisitionOptimizer.rev',
    # dmeta='AcquisitionOptimizer.dwi_metadata',
    # rmeta='AcquisitionOptimizer.rev_metadata'
)


class AcquisitionOptimizer(MagicMonkeyBaseApplication):
    class TriConf(TriangulationConfiguration):
        @default('app_flags')
        def _app_flags_default(self):
            return {
                "dont-group-shells": (
                    {
                        "TriConf": {
                            "regroup_radii": False
                        }
                    },
                    "Group shells by b-value using threshold"
                )
            }

        @default('app_aliases')
        def _app_aliases_default(self):
            return {
                "bthr": "TriConf.regroup_threshold"
            }

    name = u"Acquisition Optimizer"
    description = _description

    configuration = Instance(
        TriConf,
        kw={
            "default_overrides": {
                "regroup_threshold": 40,
                "radii_precision": 1E-2
            }
        }
    ).tag(config=True)

    bvals = required_file(description="B-value file following fsl format")
    bvecs = required_file(description="B-vector file following fsl format")
    # dwi = required_file(description="Input diffusion weighted volume to test")
    # dwi_metadata = required_file(
    #     description="Metadata file associated to the dwi volume"
    # )
    # rev = Unicode(
    #     help="Input reverse encoded diffusion weighted volume to test"
    # ).tag(config=True)
    # rev_metadata = Unicode(
    #     help="Metadata file associated to the reverse dwi volume"
    # ).tag(config=True)

    aliases = Dict(_aliases)

    def _start(self):
        bvals = np.loadtxt(self.bvals)
        bvecs = np.loadtxt(self.bvecs).T

        bvals, voronoi = get_bshells_voronoi(
            bvals, bvecs,
            regroup=self.configuration.regroup_radii,
            bval_thr=self.configuration.regroup_threshold,
            precision=self.configuration.radii_precision
        )

        lines = []
        for s, vor in voronoi:
            lines.append("Shell {}".format(s))
            for pt, verts, area in vor:
                lines.append(" -- PT {} | {} units".format(pt, area))
                for vert in verts:
                    lines.append("   {}".format(vert))

        print("\n".join(lines))
