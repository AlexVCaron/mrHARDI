from os import cpu_count, getcwd

from traitlets import Instance, Unicode, List, Integer
from traitlets.config import ArgumentError, Dict

from magic_monkey.base.application import MagicMonkeyBaseApplication
from magic_monkey.base.shell import launch_shell_process
from magic_monkey.config.csd import SphericalDeconvConfiguration, \
    FiberResponseConfiguration


_csd_aliases = {
    'in': 'CSD.image',
    'bvals': 'CSD.bvals',
    'bvecs': 'CSD.bvecs',
    'responses': 'CSD.responses',
    'out': 'CSD.out',
    'mask': 'CSD.mask',
    'nn_dirs': 'CSD.non_neg_directions',
    'dc_freq': 'CSD.deconv_frequencies',
    'p': 'CSD.n_threads'
}


class CSD(MagicMonkeyBaseApplication):
    configuration = Instance(SphericalDeconvConfiguration).tag(config=True)

    image = Unicode().tag(config=True, required=True)
    bvals = Unicode().tag(config=True, required=True)
    bvecs = Unicode().tag(config=True, required=True)

    responses = List(Unicode, minlen=1, maxlen=3).tag(
        config=True, required=True
    )

    output_prefix = Unicode().tag(config=True, required=True)

    mask = Unicode().tag(config=True)
    non_neg_directions = Unicode().tag(config=True)
    deconv_frequencies = Unicode().tag(config=True)

    n_threads = Integer(cpu_count()).tag(config=True)

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

    def start(self):
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
    'in': 'CSD.image',
    'bvals': 'CSD.bvals',
    'bvecs': 'CSD.bvecs',
    'out': 'CSD.out',
    'mask': 'CSD.mask',
    'p': 'CSD.n_threads'
}


class FiberResponse(MagicMonkeyBaseApplication):
    configuration = Instance(FiberResponseConfiguration).tag(config=True)

    image = Unicode().tag(config=True, required=True)
    bvals = Unicode().tag(config=True, required=True)
    bvecs = Unicode().tag(config=True, required=True)

    output_prefix = Unicode().tag(config=True, required=True)

    mask = Unicode().tag(config=True)
    n_threads = Integer(cpu_count()).tag(config=True)

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
