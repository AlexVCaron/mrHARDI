import nibabel as nib
import numpy as np

from dipy.direction.probabilistic_direction_getter import \
    ProbabilisticDirectionGetter, \
    default_sphere

from dipy.tracking.local_tracking import ParticleFilteringTracking
from dipy.tracking.stopping_criterion import CmcStoppingCriterion

from monkey_io.io_process import PythonIOProcess


class PythonTrackingProcess(PythonIOProcess):
    def __init__(
        self, algorithm, algorithm_init, required_inputs, algorithm_outputs,
        output_prefix, output_processor=lambda outputs, algorithm: None
    ):
        super().__init__(
            "Tracking via {}".format(algorithm.value.__name__), output_prefix,
            required_inputs
        )

        self._algorithm = algorithm
        self._algorithm_init = algorithm_init
        self._output_keys = algorithm_outputs
        self._output_processor = output_processor

    @property
    def required_output_keys(self):
        return self._output_keys

    def _execute(self, log_file_path, *args, **kwargs):
        with open(log_file_path, "w+") as log_file:
            log_file.write("Initializing tracking algorithm")
            alg_args, alg_kwargs = self._algorithm_init(
                self._algorithm, dict(zip(self.input_keys, self._input))
            )
            log_file.write("Running tracking algorithm")
            outputs = self._algorithm(*alg_args, **alg_kwargs)
            log_file.write("Processing tracking results")
            self._output_processor(
                outputs, self._algorithm
            )


def dipy_pft_algorithm(
    sh_img_key, seed_init_fn, step_size=0.2, max_angle=20., maxlen=1000,
    backtracking_dist=2, tracking_dist=1, particle_cnt=15, max_cross=1,
    sphere=default_sphere, pve_wm_key="pve_wm", pve_gm_key="pve_gm",
    pve_csf_key="pve_csf", return_all=False
):
    def algorithm_init(alg, inputs):
        sh_img = nib.load(inputs[sh_img_key])
        dg = ProbabilisticDirectionGetter.from_shcoeff(
            sh_img.get_fdata(), max_angle=max_angle, sphere=sphere
        )

        pve_wm = nib.load(inputs[pve_wm_key]).get_fdata()
        pve_gm = nib.load(inputs[pve_gm_key]).get_fdata()
        pve_csf = nib.load(inputs[pve_csf_key]).get_fdata()
        voxel_size = np.average(pve_wm.header['pixdim'][1:4])

        cmc_crit = CmcStoppingCriterion.from_pve(
            pve_wm, pve_gm, pve_csf,
            step_size=step_size, average_voxel_size=voxel_size
        )

        seeds = seed_init_fn(inputs)

        return [dg, cmc_crit, seeds, inputs["affine"]], {
            "max_cross": max_cross,
            "step_size": step_size,
            "maxlen": maxlen,
            "pft_back_tracking_dist": backtracking_dist,
            "pft_front_tracking_dist": tracking_dist,
            "particle_count": particle_cnt,
            "return_all": return_all
        }

    return ParticleFilteringTracking, algorithm_init
