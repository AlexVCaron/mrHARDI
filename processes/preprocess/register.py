from multiprocessing import cpu_count

from numpy import array

from config import append_image_extension
from piper.pipeline.process import ShellProcess


def ants_rigid_step(
    grad_step=0.1, metric="MI", n_in_for_metric=1,
    metric_params=(1, 32, "Regular", 0.25),
    conv_max_iter=(1000, 500, 250, 100), conv_eps="1e-6", conv_win=10,
    shrinks=(8, 4, 2, 1), smoothing=(3, 2, 1, 0)
):
    return "".join([
        "--transform Rigid[{}] ".format(grad_step),
        " ".join(["".join([
            "--metric {}".format(metric),
            "[{", "in{i}".format(i=in_metric), "}",
            ",{}]".format(",".join(str(p) for p in metric_params))
            ]) for in_metric in range(1, n_in_for_metric + 1)]),
        " --convergence [{},{},{}] ".format(
            "x".join(str(i) for i in conv_max_iter), conv_eps, conv_win),
        "--shrink-factors {} ".format("x".join(str(s) for s in shrinks)),
        "--smoothing-sigmas {}vox".format("x".join(str(s) for s in smoothing)),
    ])


def ants_affine_step(
    grad_step=0.1, metric="MI", n_in_for_metric=1,
    metric_params=(1, 32, "Regular", 0.25),
    conv_max_iter=(1000, 500, 250, 100), conv_eps="1e-6", conv_win=10,
    shrinks=(8, 4, 2, 1), smoothing=(3, 2, 1, 0)
):
    return "".join([
        "--transform Affine[{}] ".format(grad_step),
        " ".join(["".join([
            "--metric {}".format(metric),
            "[{", "in{i}".format(i=in_metric), "}",
            ",{}]".format(",".join(str(p) for p in metric_params))
            ]) for in_metric in range(1, n_in_for_metric + 1)]),
        " --convergence [{},{},{}] ".format(
            "x".join(str(i) for i in conv_max_iter), conv_eps, conv_win),
        "--shrink-factors {} ".format("x".join(str(s) for s in shrinks)),
        "--smoothing-sigmas {}vox".format("x".join(str(s) for s in smoothing)),
    ])


def ants_syn_step(
    grad_step=0.1, var_penality=3, var_total=0, metric="CC", n_in_for_metric=1,
    metric_params=(1, 4), conv_max_iter=(100, 70, 50, 20), conv_eps="1e-6",
    conv_win=10, shrinks=(8, 4, 2, 1), smoothing=(3, 2, 1, 0), syn_type="SyN"
):
    return "".join([
        "--transform {}[{},{},{}] ".format(
            syn_type, grad_step, var_penality, var_total
        ),
        " ".join(["".join([
            "--metric {}".format(metric),
            "[{", "in{i}".format(i=in_metric), "}",
            ",{}]".format(",".join(str(p) for p in metric_params))
            ]) for in_metric in range(1, n_in_for_metric + 1)]),
        " --convergence [{},{},{}] ".format(
            "x".join(str(i) for i in conv_max_iter), conv_eps, conv_win),
        "--shrink-factors {} ".format("x".join(str(s) for s in shrinks)),
        "--smoothing-sigmas {}vox".format("x".join(str(s) for s in smoothing)),
    ])


def ants_global_params(
    interpolation="Linear", dimension=3, use_float=False,
    inlier_range=[5E-3, 0.995], histogram_match=True, accross_modalities=True
):
    return "".join([
        "--dimensionality {} --float {} ".format(
            dimension, 1 if use_float else 0),
        "--interpolation {} --winsorize-image-intensities [{},{}]".format(
            interpolation, *inlier_range),
        " --use-histogram-matching {}".format(
            0 if accross_modalities else 1) if histogram_match else ""
    ])


class AntsRegisterProcess(ShellProcess):
    def __init__(
        self, output_prefix,
        steps, params, add_init_moving=True, verbose=False
    ):
        super().__init__(
            "Ants registration", output_prefix, ["img_from", "img_to"]
        )

        self._ants_steps = (
            [self._generate_moving()] if add_init_moving else []
        ) + self._as_list(steps)

        self._params = params
        self._n_cores = cpu_count()
        self._verbose = verbose

    def get_required_output_keys(self):
        return ["ref", "affine"]

    def _execute(
        self, img_frm, img_to, prefix, warped_output,
        inv_warped_output, *args, **kwargs
    ):
        "antsRegistration {} {} {}".format(
            " ".join([step.format(**{
                "in{}".format(i + 1): "{},{}".format(img_frm[i], img_to[i])
                for i in range(len(img_frm))
            }) for step in self._ants_steps]),
            self._params,
            " ".join([
                "--output",
                "[{},{},{}]{}".format(
                    prefix,
                    warped_output,
                    inv_warped_output,
                    " --verbose" if self._verbose else ""
                )
            ])
        )

    def execute(self, *args, **kwargs):
        img_frm, img_to = self._input
        prefix = self._get_prefix()

        warped_output = append_image_extension("{}Warped".format(prefix))
        inv_warped_output = append_image_extension(
            "{}InverseWarped".format(prefix)
        )

        super().execute(
            *args, img_frm, img_to, prefix,
            warped_output, inv_warped_output,
            **kwargs
        )

        self._output_package.update({
            "ref": warped_output,
            "affine": "{}0GenericAffine.mat".format(prefix)
        })

    def _as_list(self, data):
        return data if type(data) in [list, array] else [data]

    def _generate_moving(self):
        return "--initial-moving-transform [{in1},1]"


class AntsApplyTransformProcess(ShellProcess):
    def __init__(
        self, output_prefix, dimension=3, input_type=0,
        interpolation="Linear", fill_value=0, verbose=False,
        img_key_deriv="img"
    ):
        super().__init__(
            "Apply Ants transform", output_prefix,
            [img_key_deriv, "affine", "ref"]
        )

        self._params = [input_type, dimension, interpolation, fill_value]
        self._verbose = verbose

    def get_required_output_keys(self):
        return [self.primary_input_key]

    def _execute(self, img, affine, ref, output, *args, **kwargs):
        return " ".join([
            "antsApplyTransforms -i {} -r {} -t {}".format(img, affine, ref),
            "-o {}".format(output),
            "-e {} -d {} -n {} -f {}".format(*self._params),
            "--verbose" if self._verbose else ""
        ])

    def execute(self, *args, **kwargs):
        img, affine, ref = self._input
        prefix = self._get_prefix()
        output = {
            self.primary_input_key: append_image_extension(prefix)
        }

        super().execute(img, affine, ref, output[self.primary_input_key])

        self._output_package.update(output)
