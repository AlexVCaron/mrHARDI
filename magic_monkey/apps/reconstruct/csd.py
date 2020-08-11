from os import getcwd

from traitlets import Instance, Unicode
from traitlets.config import ArgumentError, Dict

from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    MultipleArguments, required_file, required_arg, output_prefix_argument, \
    nthreads_arg, mask_arg
from magic_monkey.base.shell import launch_shell_process
from magic_monkey.config.csd import SphericalDeconvConfiguration, \
    FiberResponseConfiguration


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


class CSD(MagicMonkeyBaseApplication):
    configuration = Instance(SphericalDeconvConfiguration).tag(config=True)

    image = required_file(help="Input dwi image")
    bvals = required_file(help="Input b-values")
    bvecs = required_file(help="Input b-vectors")

    responses = required_arg(
        MultipleArguments,
        help="Response names for the different tissues "
             "(depending on the algorithm of choice)",
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
                if len(freqs) != self.config.lmax:
                    raise ArgumentError(
                        "{} frequencies found. Need {}".format(
                            len(freqs), self.config.lmax
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
                "{} algorithm requires {} responses".format(
                    self.configuration.algorithm.name,
                    len(self.configuration.algorithm.responses)
                )
            )

    def _start(self):
        current_path = getcwd()
        optionals = []

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
        optionals.append("-fslgrad {} {}".format(self.bvals, self.bvecs))
        optionals.append(self.configuration.serialize())

        command = "dwi2fod {} {} {} {}".format(
            " ".join(optionals),
            self.configuration.algorithm.name,
            self.image,
            " ".join("{} {}".format(
                res, "{}_{}.nii.gz".format(self.output_prefix, res)
            ) for res in self.configuration.algorithm.responses)
        )

        launch_shell_process(command, current_path)


_fr_aliases = {
    'in': 'FiberResponse.image',
    'bvals': 'FiberResponse.bvals',
    'bvecs': 'FiberResponse.bvecs',
    'out': 'FiberResponse.output_prefix',
    'mask': 'FiberResponse.mask',
    'p': 'FiberResponse.n_threads'
}


class FiberResponse(MagicMonkeyBaseApplication):
    configuration = Instance(FiberResponseConfiguration).tag(config=True)

    image = required_file(help="Input dwi image")
    bvals = required_file(help="Input b-values")
    bvecs = required_file(help="Input b-vectors")

    output_prefix = output_prefix_argument()

    mask = mask_arg()
    n_threads = nthreads_arg()

    aliases = Dict(_fr_aliases)

    def _start(self):
        current_path = getcwd()
        optionals = []

        if self.mask:
            optionals.append("-mask {}".format(self.mask))

        optionals.append("-nthreads {}".format(self.n_threads))
        optionals.append("-fslgrad {} {}".format(self.bvals, self.bvecs))
        optionals.append(self.configuration.serialize())

        command = "dwi2response {} {} {} {}".format(
            self.configuration.algorithm.name,
            self.image,
            " ".join(
                "{}_{}".format(self.output_prefix, res)
                for res in self.configuration.algorithm.responses
            ),
            " ".join(optionals)
        )

        launch_shell_process(command, current_path)
