from copy import copy
from os.path import exists

import nibabel as nib
from numpy import loadtxt
from traitlets.config import Bool, Dict, Enum

from magic_monkey.base.application import (ChoiceEnum, ChoiceList,
                                           MagicMonkeyBaseApplication,
                                           affine_file,
                                           output_prefix_argument,
                                           required_file)

_TENSOR_METRICS = ["fa", "md", "ad", "rd", "peaks"]


class TensorMetricsEnum(ChoiceEnum):
    def __init__(self, **kwargs):
        super().__init__(copy(_TENSOR_METRICS), **kwargs)


_aliases = {
    'metrics': 'TensorMetrics.metrics',
    'in': 'TensorMetrics.input_prefix',
    'out': 'TensorMetrics.output_prefix',
    'affine': 'TensorMetrics.affine'
}


_flags = dict(
    colors=(
        {'TensorMetrics': {'output_colors': True}},
        "create color map for compatible metrics based on eigenvectors"
    ),
    eigs=(
        {'TensorMetrics': {'save_eigs': True}},
        "save eigenvalues and eigenvectors to output"
    )
)


class TensorMetrics(MagicMonkeyBaseApplication):
    metrics = ChoiceList(
        copy(_TENSOR_METRICS), TensorMetricsEnum, copy(_TENSOR_METRICS),
        True, help="Tensor metrics to run on the outputs"
    ).tag(config=True)

    input_prefix = required_file(
        description="Prefix of dti outputs (including mask)")
    output_prefix = output_prefix_argument()
    affine = affine_file()

    save_eigs = Bool(
        False, help="Save eigenvalues and eigenvectors"
    ).tag(config=True)
    output_colors = Bool(
        False, help="Output color metrics if available"
    ).tag(config=True)

    cache = Dict({})

    aliases = Dict(_aliases)
    flags = Dict(_flags)

    def _start(self):
        import magic_monkey.traits.metrics.dti as metrics_module

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
