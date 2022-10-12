from copy import copy
from os.path import exists

import nibabel as nib

from traitlets.config import Bool, Dict
from traitlets.config.loader import ConfigError

from mrHARDI.base.application import (ChoiceEnum, ChoiceList,
                                           mrHARDIBaseApplication,
                                           output_prefix_argument,
                                           required_file)

from mrHARDI.base.dwi import load_metadata

_TENSOR_METRICS = ["fa", "md", "ad", "rd", "peaks"]


class TensorMetricsEnum(ChoiceEnum):
    def __init__(self, **kwargs):
        super().__init__(copy(_TENSOR_METRICS), **kwargs)


_aliases = {
    'metrics': 'TensorMetrics.metrics',
    'in': 'TensorMetrics.input_prefix',
    'out': 'TensorMetrics.output_prefix'
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

_description = """
Compute metrics over the diffusion tensor reconstruction. 
"""


class TensorMetrics(mrHARDIBaseApplication):
    name = u"DTI Metrics"
    description = _description
    metrics = ChoiceList(
        copy(_TENSOR_METRICS), TensorMetricsEnum(), copy(_TENSOR_METRICS),
        True, help="Tensor metrics to run on the outputs"
    ).tag(config=True)

    input_prefix = required_file(
        description="Prefix of dti outputs (including mask)")
    output_prefix = output_prefix_argument()

    save_eigs = Bool(
        False, help="Save eigenvalues and eigenvectors"
    ).tag(config=True)
    output_colors = Bool(
        False, help="Output color metrics if available"
    ).tag(config=True)

    cache = Dict(default_value={})

    aliases = Dict(default_value=_aliases)
    flags = Dict(default_value=_flags)

    def execute(self):
        import mrHARDI.traits.metrics.dti as metrics_module

        mask = None
        if exists("{}_mask.nii.gz".format(self.input_prefix)):
            mask = nib.load("{}_mask.nii.gz".format(self.input_prefix))

        metadata = load_metadata("{}.nii.gz".format(self.input_prefix))
        if metadata is None:
            raise ConfigError(
                "Need a metadata file for {}".format(self.input_prefix)
            )

        for metric in self.metrics:
            klass = getattr(
                metrics_module, "{}Metric".format(metric.capitalize())
            )

            dti_image = nib.load("{}_dti.nii.gz".format(self.input_prefix))
            kwargs = {
                "shape": dti_image.shape[:-1],
                "colors": self.output_colors
            }
            if mask:
                kwargs["mask"] = mask.get_fdata().astype(bool)

            klass(
                self.input_prefix, self.output_prefix, self.cache,
                metadata.affine, **kwargs
            ).measure()

        if self.save_eigs:
            evals, evecs = self.cache["eigs"]
            nib.save(
                nib.Nifti1Image(evals, metadata.affine),
                "{}_evals.nii.gz".format(self.output_prefix)
            )
            nib.save(
                nib.Nifti1Image(evecs, metadata.affine),
                "{}_evecs.nii.gz".format(self.output_prefix)
            )
