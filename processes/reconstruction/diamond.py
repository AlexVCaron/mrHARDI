from multiprocessing import cpu_count

from piper.pipeline import ShellProcess

from config import append_image_extension, get_img_extension


class DiamondArguments:
    class _MoseModel:
        def precomputed(self):
            return True

        def __str__(self):
            return ""

    class _MoseFile(_MoseModel):
        def __init__(self, mose_file):
            self.mose = mose_file

        def precomputed(self):
            return True

        def __str__(self):
            return "--mosemask {}".format(self.mose)

    class _MoseAlg(_MoseModel):
        def __init__(self, model, args):
            self.model = (model, args)

        def precomputed(self):
            return False

        def __str__(self):
            return "--automose {} {}".format(*self.model)

    class _FascicleModel:
        def __init__(
            self, name="diamondNCcyl", args=None, awaited_output_fn=None
        ):
            self.model = (name, args if args else [])
            if awaited_output_fn:
                self.awaited_outputs = awaited_output_fn

        def __str__(self):
            return "--fascicle {} {}".format(
                self.model[0], " ".join(self.model[1])
            )

        def awaited_outputs(self, base_name, extension, n_fascicles):
            return [fmt.format(base_name, extension) for fmt in [
                "{}_fractions.{}",
                "{}_hei.{}",
                "{}_heiAD.{}",
                "{}_kappa.{}",
                "{}_kappaAD.{}"
            ] + ["{}_t" + str(i) + ".{}" for i in range(n_fascicles)]]

    def __init__(self):
        self.n = 1
        self.p = cpu_count()
        self.regul = 1.
        self.model = DiamondArguments._FascicleModel()
        self.extra_args = ""
        self.mose = DiamondArguments._MoseModel()

    @property
    def max_fascicle_per_voxel(self):
        return self.n

    @property
    def will_compute_mosemap(self):
        return not self.mose.precomputed()

    def format_argument_string(self, mask=None):
        return "-n {} -p {} -r {} {} {} {}".format(
            self.n, self.p, self.regul, self.model, self.mose, self.extra_args
        ) + " -m {}".format(mask) if mask else ""

    def get_model_output_keys(self, base_name, extension):
        return self.model.awaited_outputs(base_name, extension, self.n)


class DiamondProcess(ShellProcess):
    def __init__(
        self, output_prefix, diamond_arguments=None,
        force_masked=False, img_key_deriv="img",
        additional_required_inputs=None
    ):
        if additional_required_inputs is None:
            additional_required_inputs = []

        super().__init__(
            "Diamond Tensor Distribution Reconstruction", output_prefix,
            [img_key_deriv] + additional_required_inputs + (
                ["mask"] if force_masked else []
            ), [] if force_masked else ["mask"]
        )

        if diamond_arguments:
            assert isinstance(diamond_arguments, DiamondArguments)
            self._diamond_args = diamond_arguments
        else:
            self._diamond_args = DiamondArguments()

    @property
    def required_output_keys(self):
        return self._generate_awaited_output_keys()

    def _execute(self, str_arguments, *args, **kwargs):
        return "crlDCIEstimate {}".format(str_arguments)

    def execute(self, *args, **kwargs):
        img, mask = self._input
        output_img = append_image_extension(self._get_prefix())

        str_arguments = "-i {} -o {} {}".format(
            img, output_img, self._diamond_args.format_argument_string(mask)
        )

        super().execute(*args, str_arguments, **kwargs)

        self._update_output_dictionary(output_img)

    def _update_output_dictionary(self, output_img):
        self._output_package.update({
            self.primary_input_key: output_img
        })

    def _generate_awaited_output_keys(self):
        n_tensors = self._diamond_args.max_fascicle_per_voxel
        gen_mose = self._diamond_args.will_compute_mosemap
        model_output_keys = self._diamond_args.get_model_output_keys(
            self._get_prefix(), get_img_extension()
        )

        return ["t{}".format(i) for i in range(n_tensors)] + (
            ["mose"] if gen_mose else []
        ) + model_output_keys
