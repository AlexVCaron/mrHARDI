from os import getcwd
from os.path import basename, join

import numpy as np
from traitlets import Instance, Unicode
from traitlets.config import ArgumentError, Dict

from magic_monkey.base.application import (MagicMonkeyBaseApplication,
                                           MultipleArguments,
                                           mask_arg,
                                           nthreads_arg,
                                           output_prefix_argument,
                                           required_arg,
                                           required_file)
from magic_monkey.base.shell import launch_shell_process
from magic_monkey.traits.csd import (CSDAlgorithm,
                                     TournierResponseAlgorithm)
from magic_monkey.config.csd import (FiberResponseConfiguration,
                                     CSDConfiguration)

_csd_aliases = {
    'in': 'CSD.image',
    'bvals': 'CSD.bvals',
    'bvecs': 'CSD.bvecs',
    'responses': 'CSD.responses',
    'out': 'CSD.output_prefix',
    'mask': 'CSD.mask',
    'nn_dirs': 'CSD.non_neg_directions',
    'dc_freq': 'CSD.deconv_frequencies',
    'p': 'CSD.n_threads'
}


_csd_description = """
Performs constrained spherical deconvolution on diffusion weighted images. The 
image acquisition sequence must provide enough gradient directions to perform 
the deconvolution up the the desired order. The program uses *MRtrix* [1] to 
do the actual computation.

References :
------------
[1] https://mrtrix.readthedocs.io/en/latest/reference/commands/dwi2fod.html
[2] Tournier, J.-D.; Calamante, F., Gadian, D.G. & Connelly, A. Direct 
    estimation of the fiber orientation density function from 
    diffusion-weighted MRI data using spherical deconvolution. NeuroImage, 
    2004, 23, 1176-1185.
[3] Tournier, J.-D.; Smith, R. E.; Raffelt, D.; Tabbara, R.; Dhollander, T.; 
    Pietsch, M.; Christiaens, D.; Jeurissen, B.; Yeh, C.-H. & Connelly, A. 
    MRtrix3: A fast, flexible and open software framework for medical image 
    processing and visualisation. NeuroImage, 2019, 202, 116137.
[4] Tournier, J.-D.; Calamante, F. & Connelly, A. Robust determination of the 
    fibre orientation distribution in diffusion MRI: Non-negativity 
    constrained super-resolved spherical deconvolution. NeuroImage, 2007, 35, 
    1459-1472.
[5] Jeurissen, B; Tournier, J-D; Dhollander, T; Connelly, A & Sijbers, J. 
    Multi-tissue constrained spherical deconvolution for improved analysis of 
    multi-shell diffusion MRI data. NeuroImage, 2014, 103, 411-426.
"""


class CSD(MagicMonkeyBaseApplication):
    name = u"Spherical Deconvolution"
    description = _csd_description
    configuration = Instance(CSDConfiguration).tag(config=True)

    image = required_file(description="Input dwi image")
    bvals = required_file(description="Input b-values")
    bvecs = required_file(description="Input b-vectors")

    responses = required_arg(
        MultipleArguments,
        description="Response filenames for the different tissues "
                    "(depending on the algorithm of choice), must be "
                    "in order [wm, gm, csf] (if using MSMT)",
        traits_args=(Unicode,), traits_kwargs=dict(minlen=1, maxlen=3)
    )

    output_prefix = output_prefix_argument()

    mask = mask_arg()

    non_neg_directions = Unicode(
        help="Text file containing directions upon which the non-negativity "
             "constraint is applied, spread on a sphere of radius 1. Supply "
             "a list of (azimuth, elevation) tuples"
    ).tag(config=True)
    deconv_frequencies = Unicode(
        help="List of weights on spherical harmonics coefficients. Used to "
             "initialize deconvolution, supply a file containing the values "
             "separated by spaces"
    ).tag(config=True)

    n_threads = nthreads_arg()

    aliases = Dict(_csd_aliases)

    def _validate_required(self):
        super()._validate_required()

        if self.deconv_frequencies:
            if self.configuration.algorithm.name != "csd":
                raise ArgumentError(
                    "Frequency filter only required "
                    "when using the CSD algorithm "
                )

            with open(self.deconv_frequencies) as f:
                freqs = f.readline().split(" ")
                if len(freqs) != self.configuration.lmax:
                    raise ArgumentError(
                        "{} frequencies found. Need {}".format(
                            len(freqs), self.configuration.lmax
                        ) + " for the wanted order"
                    )

        if len(self.responses) == 2:
            raise ArgumentError(
                "Either provide 1 response for white matter of 3 responses "
                "for white matter, gray matter and csf"
            )

        if len(self.responses) != len(self.configuration.algorithm.responses):
            raise ArgumentError(
                "{} responses provided, ".format(len(self.responses)) +
                "{} algorithm requires {}".format(
                    self.configuration.algorithm.name,
                    len(self.configuration.algorithm.responses)
                )
            )

    def _generate_config_file(self, filename):
        self.configuration.algorithm = CSDAlgorithm()
        super()._generate_config_file(filename)

    def execute(self):
        current_path = getcwd()
        optionals = []

        if not self.configuration.shells:
            shells, counts = np.unique(
                np.loadtxt(self.bvals),
                return_counts=True
            )
            mask = shells > 0
            shells = shells[mask]
            counts = counts[mask]

            if not self.configuration.algorithm.multishell:
                self.configuration.shells = [shells[counts.argmax()]]
            else:
                self.configuration.shells = shells.tolist()


        if self.mask:
            optionals.append("-mask {}".format(self.mask))

        if self.non_neg_directions:
            optionals.append("-directions {}".format(self.non_neg_directions))

        if self.deconv_frequencies:
            optionals.append("-filter {}".format(self.deconv_frequencies))

        if self.configuration.algorithm.name == "msmt_csd":
            if self.configuration.algorithm.predicted_signal:
                optionals.append("-predicted_signal {}_pred_s.nii.gz".format(
                    self.output_prefix
                ))

        optionals.append("-nthreads {}".format(self.n_threads))
        optionals.append("-fslgrad {} {}".format(self.bvecs, self.bvals))

        command = "dwi2fod {} {} {} {} {}".format(
            self.configuration.algorithm.cli_name,
            " ".join(optionals),
            self.image,
            " ".join("{} {}".format(
                res_file, "{}_{}.nii.gz".format(self.output_prefix, res)
            ) for res_file, res in zip(
                self.responses,
                self.configuration.algorithm.responses
            )),
            self.configuration.serialize()
        )

        launch_shell_process(command, join(current_path, "{}.log".format(
            basename(self.output_prefix)
        )))


_fr_aliases = {
    'in': 'FiberResponse.image',
    'bvals': 'FiberResponse.bvals',
    'bvecs': 'FiberResponse.bvecs',
    'out': 'FiberResponse.output_prefix',
    'mask': 'FiberResponse.mask',
    'p': 'FiberResponse.n_threads'
}

_fr_description = """
Compute the single-fiber response needed for the constrained spherical 
deconvolution. Algorithms for multi-tissue responses are also available, 
giving out also the gray matter and the cerebro-spinal fluid responses as
well. The program uses *MRtrix* [1] to do the actual computation.

References :
------------
[1] https://mrtrix.readthedocs.io/en/latest/reference/commands/dwi2fod.html
[2] Tournier, J.-D.; Smith, R. E.; Raffelt, D.; Tabbara, R.; Dhollander, T.; 
    Pietsch, M.; Christiaens, D.; Jeurissen, B.; Yeh, C.-H. & Connelly, A. 
    MRtrix3: A fast, flexible and open software framework for medical image 
    processing and visualisation. NeuroImage, 2019, 202, 116137.
[3] Dhollander, T.; Raffelt, D. & Connelly, A. Unsupervised 3-tissue response 
    function estimation from single-shell or multi-shell diffusion MR data 
    without a co-registered T1 image. ISMRM Workshop on Breaking the Barriers 
    of Diffusion MRI, 2016, 5.
[4] Dhollander, T.; Mito, R.; Raffelt, D. & Connelly, A. Improved white matter 
    response function estimation for 3-tissue constrained spherical 
    deconvolution. Proc Intl Soc Mag Reson Med, 2019, 555.
[5] Tournier, J.-D.; Calamante, F.; Gadian, D. G. & Connelly, A. Direct 
    estimation of the fiber orientation density function from 
    diffusion-weighted MRI data using spherical deconvolution. NeuroImage, 
    2004, 23, 1176-1185.
[6] Jeurissen, B.; Tournier, J.-D.; Dhollander, T.; Connelly, A. & Sijbers, J. 
    Multi-tissue constrained spherical deconvolution for improved analysis of 
    multi-shell diffusion MRI data. NeuroImage, 2014, 103, 411-426.
[7] Tax, C. M.; Jeurissen, B.; Vos, S. B.; Viergever, M. A. & Leemans, A. 
    Recursive calibration of the fiber response function for spherical 
    deconvolution of diffusion MRI data. NeuroImage, 2014, 86, 67-80.
[8] Tournier, J.-D.; Calamante, F. & Connelly, A. Determination of the 
    appropriate b-value and number of gradient directions for 
    high-angular-resolution diffusion-weighted imaging. NMR Biomedicine, 2013, 
    26, 1775-1786.
"""


class FiberResponse(MagicMonkeyBaseApplication):
    name = u"Fiber Response"
    description = _fr_description
    configuration = Instance(FiberResponseConfiguration).tag(config=True)

    image = required_file(description="Input dwi image")
    bvals = required_file(description="Input b-values")
    bvecs = required_file(description="Input b-vectors")

    output_prefix = output_prefix_argument()

    mask = mask_arg()
    n_threads = nthreads_arg()

    aliases = Dict(_fr_aliases)

    def _generate_config_file(self, filename):
        self.configuration.algorithm = TournierResponseAlgorithm()
        super()._generate_config_file(filename)

    def execute(self):
        current_path = getcwd()
        optionals = []

        if not self.configuration.shells:
            shells, counts = np.unique(np.loadtxt(self.bvals), return_counts=True)
            mask = shells > 0
            shells = shells[mask]
            counts = counts[mask]

            if not self.configuration.algorithm.multishell:
                self.configuration.shells = [shells[counts.argmax()]]
            else:
                self.configuration.shells = shells.tolist()

        if self.mask:
            optionals.append("-mask {}".format(self.mask))

        optionals.append("-nthreads {}".format(self.n_threads))
        optionals.append("-fslgrad {} {}".format(self.bvecs, self.bvals))

        command = "dwi2response {} {} {} {} {}".format(
            self.configuration.algorithm.cli_name,
            " ".join(optionals),
            self.image,
            " ".join(
                "{}_{}.txt".format(self.output_prefix, res)
                for res in self.configuration.algorithm.responses
            ),
            self.configuration.serialize()
        ).rstrip(" ")

        launch_shell_process(command, join(current_path, "{}.log".format(
            basename(self.output_prefix)
        )))
