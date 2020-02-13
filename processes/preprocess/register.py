from multiprocessing import cpu_count
from numpy import array
from multiprocess.process import Process


def ants_rigid_step(
        grad_step=0.1, metric="MI", n_in_for_metric=1, metric_params=(1, 32, "Regular", 0.25),
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
        " --convergence [{},{},{}] ".format("x".join(str(i) for i in conv_max_iter), conv_eps, conv_win),
        "--shrink-factors {} ".format("x".join(str(s) for s in shrinks)),
        "--smoothing-sigmas {}vox".format("x".join(str(s) for s in smoothing)),
    ])


def ants_affine_step(
        grad_step=0.1, metric="MI", n_in_for_metric=1, metric_params=(1, 32, "Regular", 0.25),
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
        " --convergence [{},{},{}] ".format("x".join(str(i) for i in conv_max_iter), conv_eps, conv_win),
        "--shrink-factors {} ".format("x".join(str(s) for s in shrinks)),
        "--smoothing-sigmas {}vox".format("x".join(str(s) for s in smoothing)),
    ])


def ants_syn_step(
        grad_step=0.1, var_penality=3, var_total=0, metric="CC", n_in_for_metric=1, metric_params=(1, 4),
        conv_max_iter=(100, 70, 50, 20), conv_eps="1e-6", conv_win=10,
        shrinks=(8, 4, 2, 1), smoothing=(3, 2, 1, 0), syn_type="SyN"
):
    return "".join([
        "--transform {}[{},{},{}] ".format(syn_type, grad_step, var_penality, var_total),
        " ".join(["".join([
            "--metric {}".format(metric),
            "[{", "in{i}".format(i=in_metric), "}",
            ",{}]".format(",".join(str(p) for p in metric_params))
            ]) for in_metric in range(1, n_in_for_metric + 1)]),
        " --convergence [{},{},{}] ".format("x".join(str(i) for i in conv_max_iter), conv_eps, conv_win),
        "--shrink-factors {} ".format("x".join(str(s) for s in shrinks)),
        "--smoothing-sigmas {}vox".format("x".join(str(s) for s in smoothing)),
    ])


def ants_global_params(
        interpolation="Linear", dimension=3, use_float=False, inlier_range=[5E-3, 0.995],
        histogram_match=True, accross_modalities=True
):
    return "".join([
        "--dimensionality {} --float {} ".format(dimension, 1 if use_float else 0),
        "--interpolation {} --winsorize-image-intensities [{},{}]".format(interpolation, *inlier_range),
        " --use-histogram-matching {}".format(0 if accross_modalities else 1) if histogram_match else ""
    ])


class AntsRegisterProcess(Process):
    def __init__(self, input1, input2, output, steps, params, add_init_moving=True, verbose=False):
        super().__init__("Ants registration")
        self._input = [self._as_list(input1), self._as_list(input2)]
        self._output = output
        self._ants_steps = ([self._generate_moving()] if add_init_moving else []) + self._as_list(steps)
        self._params = params
        self._n_cores = cpu_count()
        self._verbose = verbose

    def execute(self):
        self._launch_process(
            "antsRegistration {} {} {}".format(
                " ".join([step.format(**{
                    "in{}".format(i + 1): "{},{}".format(self._input[0][i], self._input[1][i])
                    for i in range(len(self._input[0]))
                }) for step in self._ants_steps]),
                self._params,
                "--output [{0},{0}Warped.nii.gz,{0}InverseWarped.nii.gz]{1}".format(
                    self._output,
                    " --verbose" if self._verbose else ""
                )
            )
        )

    def _as_list(self, data):
        return data if type(data) in [list, array] else [data]

    def _generate_moving(self):
        return "--initial-moving-transform [{in1},1]"


class AntsApplyTransformProcess(Process):
    def __init__(self, input, affine_transform, reference, output, dimension=3, input_type=0, interpolation="Linear", fill_value=0, verbose=False):
        super().__init__("Apply Ants transform {} to {}".format(affine_transform[0].split("/")[-1], reference.split("/")[-1]))
        self._input = [input, reference, "[{},1]".format(affine_transform[0]) if affine_transform[1] else affine_transform[0]]
        self._output = output
        self._params = [input_type, dimension, interpolation, fill_value]
        self._verbose = verbose

    def execute(self):
        self._launch_process(" ".join([
            "antsApplyTransforms -i {0} -r {1} -t {2}".format(*self._input),
            "-o {}".format(self._output),
            "-e {} -d {} -n {} -f {}".format(*self._params),
            "--verbose" if self._verbose else ""
        ]))
