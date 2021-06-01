from os import chmod

import numpy as np
from GPUtil import GPUtil
from traitlets import Dict, Instance, Unicode, Bool, Enum
from traitlets.config.loader import ConfigError

from magic_monkey.base.application import (MagicMonkeyBaseApplication,
                                           output_prefix_argument,
                                           input_dwi_prefix)

from magic_monkey.base.fsl import prepare_acqp_file, prepare_topup_index
from magic_monkey.base.dwi import load_metadata, save_metadata, non_zero_bvecs
from magic_monkey.base.scripting import build_script
from magic_monkey.config.eddy import EddyConfiguration

_aliases = {
    "in": 'Eddy.image',
    "acqp": 'Eddy.acquisition_file',
    "rev": 'Eddy.rev_image',
    "out": 'Eddy.output_prefix'
}

_flags = dict(
    rev_eddy=(
        {"Eddy": {"eddy_on_rev": True}},
        "Enables eddy correction on dwi and "
        "reverse acquisition concatenated together"
    ),
    debug=(
        {"Eddy": {"debug": True}},
        "Enables output of debugging messages "
        "and of additional eddy outputs"
    ),
    dont_gpu=(
        {"Eddy": {"select_gpu": False}},
        "Disable GPU pre-selection for eddy cuda"
    )
)

_eddy_script = """
args=""
if [ $TOPUP ]
then
    args="$args --topup=$TOPUP"
fi
if [ $SCSFIELD ]
then
    args="$args --field=$SCSFIELD"
fi
if [ $SCSMAT ]
then
    args="$args --field_mat=$SCSMAT"
fi
if [ $SLSPEC ]
then
    args="$args --slspec=$SLSPEC"
fi

bargs="--imain=$dwi --acqp=$acqp --index=$index"
bargs="$bargs --bvecs=$bvec --bvals=$bval"

if [ -f $mask ]
then
    bargs="$bargs --mask=$mask"
fi

{executable} $bargs $args {more_args} --out=$output --very_verbose {debug_args}
"""

_description = """
Command-line utility used to parametrize and create scripts performing eddy 
correction on diffusion weighted images. For more information on the 
parameters available for the eddy executable, please refer to the website [1].

References :
------------
[1] https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/eddy
[Andersson 2016a] Jesper L. R. Andersson and Stamatios N. Sotiropoulos. 
                  An integrated approach to correction for off-resonance 
                  effects and subject movement in diffusion MR imaging. 
                  NeuroImage, 125:1063-1078, 2016.
"""


class Eddy(MagicMonkeyBaseApplication):
    name = u"Eddy"
    description = _description
    configuration = Instance(EddyConfiguration).tag(config=True)

    image = input_dwi_prefix()
    output_prefix = output_prefix_argument()

    acquisition_file = Unicode(
        help="Acquisition file describing the "
             "orientation and dwell of the volumes"
    ).tag(config=True)

    rev_image = Unicode(
        help="Input reverse acquisition image prefix "
             "(for image and bval/bvec/metadata if not b0)"
    ).tag(config=True)

    eddy_on_rev = Bool().tag(config=True)

    indexing_strategy = Enum(
        ["closest", "first"], "first",
        help="Strategy used to find which line in the .acqp aligns "
             "with which volume in the supplied dwi volume. For datasets "
             "with evenly spaced b0, \"closest\" will give the best result. "
             "In any other cases, or if you don't know, use \"first\""
    )

    debug = Bool(False).tag(config=True)
    select_gpu = Bool(True).tag(config=True)

    aliases = Dict(default_value=_aliases)
    flags = Dict(default_value=_flags)

    def _validate_required(self):
        super()._validate_required()

    def execute(self):
        bvals = np.loadtxt("{}.bval".format(self.image))
        non_zero_bvecs(self.image)
        metadata = load_metadata(self.image)
        if self.rev_image:
            rev_bvals = np.loadtxt("{}.bval".format(self.rev_image))
            non_zero_bvecs(self.rev_image)
            metadata.extend(load_metadata(self.rev_image))
        else:
            rev_bvals = np.array([])

        if not self.acquisition_file:
            acqp = prepare_acqp_file(
                metadata.dwell, metadata.directions
            )

            with open("{}_acqp.txt".format(self.output_prefix), 'w+') as f:
                f.write(acqp)
        else:
            acqp = []
            with open(self.acquisition_file) as f:
                acqp.extend(f.readlines())

        kwargs = dict(b0_comp=np.less) if self.configuration.strict else dict()

        if self.eddy_on_rev:
            bvals = np.concatenate((bvals, rev_bvals))

        indexes = prepare_topup_index(
            bvals, 1, strategy=self.indexing_strategy,
            ceil=self.configuration.ceil_value, **kwargs
        )

        if indexes.max() > len(acqp.split("\n")):
            if len(acqp.split("\n")) == 1:
                indexes[:] = 1
            else:
                dataset_indexes = metadata.dataset_indexes[1:] + [len(bvals)]
                if not len(acqp.split("\n")) == len(dataset_indexes):
                    raise ConfigError(
                        "No matching configuration found for index "
                        "(maxing at {}) "
                        "and acqp file (containing {} lines)\n{}".format(
                            indexes.max(), len(acqp.split("\n")), acqp
                        )
                    )

                indexes[:dataset_indexes[0]] = 1
                for i, idx in enumerate(dataset_indexes[1:]):
                    indexes[dataset_indexes[i]:idx] = i + 2

        with open(
            "{}_index.txt".format(self.output_prefix), "w+"
        ) as f:
            f.write(" ".join([str(i) for i in indexes]) + "\n")

        if self.configuration.enable_cuda:
            lines = [
                " ".join(["{:d}".format(mm) for mm in m]) + "\n"
                for m in metadata.slice_order
            ]

            with open("{}_slspec.txt".format(self.output_prefix), "w+") as f:
                f.writelines(lines)

        with open(
            "{}_script.sh".format(self.output_prefix), "w+"
        ) as f:
            eddy_exec = "eddy"
            if self.configuration.enable_cuda:
                if self.select_gpu:
                    mem_usage = [gpu.memoryUtil for gpu in GPUtil.getGPUs()]
                    if np.allclose(mem_usage, mem_usage[0], atol=1E-2):
                        gpu = GPUtil.getAvailable(order="random")[0]
                    else:
                        gpu = GPUtil.getAvailable(order="memory")[0]

                    eddy_exec = "CUDA_VISIBLE_DEVICES={} {}".format(
                        gpu, eddy_exec
                    )

                eddy_exec += "_cuda"
            else:
                eddy_exec += "_openmp"

            debug_args = ""
            if self.debug:
                dargs = [
                    "fields", "dfields", "cnr_maps", "range_cnr_maps",
                    "residuals", "history", "write_predictions"
                ]

                if (
                    self.configuration.slice_to_vol and
                    self.configuration.slice_to_vol["mporder"] > 1
                ):
                    dargs.extend(["write_scatter_brain_predictions"])

                if (
                    self.configuration.enable_cuda and
                    self.configuration.outlier_model is not None
                ):
                    dargs.extend(["with_outliers"])

                debug_args = " ".join("--{}=True".format(d) for d in dargs)

            if self.eddy_on_rev:
                bvals = np.loadtxt("{}.bval".format(self.image))
                rev_bvals = np.loadtxt("{}.bval".format(self.rev_image))
                if (
                    len(bvals) == len(rev_bvals) and
                    np.allclose(bvals, rev_bvals)
                ):
                    bvecs = np.loadtxt("{}.bvec".format(self.image))
                    rev_bvecs = np.loadtxt("{}.bvec".format(self.rev_image))
                    if np.allclose(bvecs, rev_bvecs):
                        self.configuration.resampling = "lsquare"

            if self.configuration.resampling == "lsquare":
                self.configuration.fill_empty = True

            if self.configuration.slice_to_vol is not None:
                self.configuration.slice_to_vol.set_mporder(
                    metadata.n_excitations
                )

            script = build_script(
                _eddy_script.format(
                    executable=eddy_exec,
                    more_args=self.configuration.serialize(),
                    debug_args=debug_args
                ),
                [
                    "dwi", "bval", "bvec", "mask", "acqp",
                    "index", "output"
                ],
                ["topup", "slspec", "scsfield", "scsmat"],
                header="\n".join([
                    "# Preparing environment",
                    "CUDA_HOME=/usr/local/cuda-9.1",
                    "export LD_LIBRARY_PATH=" + ":".join([
                        "$CUDA_HOME/extras/CUPTI/lib64",
                        "$CUDA_HOME/lib64",
                        "$LD_LIBRARY_PATH"
                    ]),
                    "export PATH=$CUDA_HOME/bin:$PATH\n"
                ]) if self.configuration.enable_cuda else ""
            )
            f.write(script)

        chmod("{}_script.sh".format(self.output_prefix), 0o0777)

        metadata.multiband_corrected = (
            self.configuration.slice_to_vol is not None or
            self.configuration.susceptibility is not None
        ) or metadata.multiband_corrected

        save_metadata(self.output_prefix, metadata)
