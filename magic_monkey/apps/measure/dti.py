from os.path import exists

import nibabel as nib
from numpy import ones, loadtxt

from traitlets import Enum, List, Unicode, Bool, Dict

from magic_monkey.base.application import MagicMonkeyBaseApplication
from magic_monkey.config.metrics.dti import compute_eigenvalues

_DTI_METRICS = ["fa", "md", "ad", "rd", "peaks"]


class DTIMetricsEnum(Enum):
    def __init__(self, **kwargs):
        super().__init__(_DTI_METRICS, **kwargs)


_aliases = {
    'metrics': 'DTIMetrics.metrics',
    'in': 'DTIMetrics.input_prefix',
    'out': 'DTIMetrics.output_prefix',
    'affine': 'DTIMetrics.affine'
}


_flags = dict(
    colors=(
        {'DTIMetrics': {'output_colors': True}},
        "create color map for compatible metrics based on eigenvectors"
    ),
    eigs=(
        {'DTIMetrics': {'save_eigs': True}},
        "save eigenvalues and eigenvectors to output"
    )
)


class DTIMetrics(MagicMonkeyBaseApplication):
    metrics = List(DTIMetricsEnum, _DTI_METRICS).tag(config=True)

    input_prefix = Unicode().tag(config=True, required=True)
    output_prefix = Unicode().tag(config=True, required=True)
    affine = Unicode().tag(config=True, required=True)

    save_eigs = Bool(False).tag(config=True)
    output_colors = Bool(False).tag(config=True)

    cache = Dict({})

    aliases = Dict(_aliases)
    flags = Dict(_flags)

    def _start(self):
        import magic_monkey.config.metrics.dti as metrics_module

        mask = None
        if exists("{}_mask.nii.gz".format(self.input_prefix)):
            mask = nib.load("{}_mask.nii.gz".format(self.input_prefix))

        affine = loadtxt(self.affine)

        for metric in self.metrics:
            klass = getattr(
                metrics_module, "{}Metric".format(metric.capitalize())
            )

            klass(
                self.input_prefix, self.output_prefix, self.cache,
                affine, mask=mask.get_fdata().astype(bool), shape=mask.shape,
                colors=self.output_colors
            ).measure()

        if self.save_eigs:
            evals, evecs = self.cache["eigs"]
            nib.save(
                nib.Nifti1Image(evals, affine),
                "{}_evals.nii.gz".format(evals)
            )
            nib.save(
                nib.Nifti1Image(evecs, affine),
                "{}_evecs.nii.gz".format(evals)
            )
