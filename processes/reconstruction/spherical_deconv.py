from piper.pipeline import ShellProcess

from config import append_image_extension

from magic_monkey.config.algorithms.csd import _format_response_names, \
    SphericalDeconvAlgorithms, ResponseAlgorithms


class SphericalDeconvolutionProcess(ShellProcess):
    def __init__(
        self, output_prefix, algorithm=SphericalDeconvAlgorithms.csd,
        shells=None, lmax=None,
        img_key_deriv="img", output_key_is_odf=False, masked=False,
        algorithm_options=None
    ):
        super().__init__(
            "Mrtrix compute ODF via Spherical deconvolution", output_prefix,
            [img_key_deriv] + _format_response_names(
                algorithm.value["responses"]
            ) + (["mask"] if masked else []),
            ["mask"]
        )

        self._alg = algorithm
        self._shells = shells
        self._lmax = lmax
        self._name_odf = output_key_is_odf

        self._add_opts = {}

        if algorithm_options:
            assert isinstance(algorithm_options, dict)

            self._add_opts = dict(filter(
                lambda it: it[0] in self._alg.value["options"],
                algorithm_options
            ))

    @property
    def primary_output_key(self):
        return "odf" if self._name_odf else self.primary_input_key

    @property
    def required_output_keys(self):
        return [self.primary_output_key]

    def execute(self, *args, **kwargs):
        img, bvals, bvecs, responses, mask = self._input

        options = "-fslgrad {} {}".format(bvals, bvecs)

        output_img = append_image_extension(self._get_prefix())

        if mask:
            options += " -mask {}".format(mask)
        if self._shells:
            options += " -shells {}".format(self._shells)
        if self._lmax:
            options += " -lmax {}".format(self._lmax)
        if self._add_opts:
            options += " {}".format(" ".join([
                "-{} {}".format(k, v) for k, v in self._add_opts.items()
            ]))

        super().execute(
            *args, self._alg.name, img,
            responses, output_img, options, **kwargs
        )

        self._output_package.update({self.primary_output_key: output_img})

    def _execute(
        self, method, img, response, output, options, *args, **kwargs
    ):
        return "dwi2fod {} {} {} {} {}".format(
            method, img, response, output, options
        )


class ComputeResponseProcess(ShellProcess):
    def __init__(
        self, output_prefix, algorithm=ResponseAlgorithms.tax,
        shells=None, lmax=None, masked=False, img_key_deriv="img",
        algorithm_options=None
    ):
        super().__init__(
            "Mrtrix compute response for Spherical Deconvolution",
            output_prefix,
            [img_key_deriv, "bvals", "bvecs"] + (["mask"] if masked else []),
            ["mask"]
        )

        self._alg = algorithm
        self._shells = shells
        self._lmax = lmax
        self._add_opts = {}

        if algorithm_options:
            assert isinstance(algorithm_options, dict)

            self._add_opts = dict(filter(
                lambda it: it[0] in self._alg.value["options"],
                algorithm_options
            ))

    @property
    def required_output_keys(self):
        return _format_response_names(self._alg.value["responses"])

    def execute(self, *args, **kwargs):
        img, bvals, bvecs, mask = self._input

        alg_config = self._alg.value
        responses_names = _format_response_names(alg_config["responses"])
        responses = [
            append_image_extension("{}_{}".format(self._get_prefix(), rs))
            for rs in responses_names
        ]

        options = "-fslgrad {} {}".format(bvals, bvecs)

        if mask:
            options += " -mask {}".format(mask)
        if self._shells:
            options += " -shells {}".format(self._shells)
        if self._lmax:
            options += " -lmax {}".format(self._lmax)
        if self._add_opts:
            options += " {}".format(" ".join([
                "-{} {}".format(k, v) for k, v in self._add_opts.items()
            ]))

        super().execute(
            *args, self._alg.name, img, responses, options, **kwargs
        )

        self._output_package.update({
            rs: append_image_extension(
                "{}_{}".format(self._get_prefix(), rs)
            ) for rs in responses_names
        })

    def _execute(self, method, img, responses, options, *args, **kwargs):
        return "dwi2response {} {} {} {}".format(
            method, img, " ".join(responses), options
        )
