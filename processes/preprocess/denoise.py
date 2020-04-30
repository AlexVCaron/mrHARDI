import sys
from multiprocessing import cpu_count
from os import chmod

import nibabel as nib
import numpy as np

from config import append_image_extension
from magic_monkey.prepare_eddy_command import prepare_eddy_index
from magic_monkey.prepare_topup_command import prepare_topup_params
from multiprocess.process import Process


class DenoiseProcess(Process):
    def __init__(self, output_prefix):
        super().__init__(
            "Denoising process via Mrtrix dwidenoise", output_prefix
        )

        self._n_cores = cpu_count()

        self._mask = None

    def set_inputs(self, package):
        self._input = [package["img"], package.pop("mask", None)]

    def execute(self):
        img, mask = self._input
        output = append_image_extension(self._get_prefix())

        args = [img, output, "-nthreads {}".format(self._n_cores)]

        if mask:
            args += ["-mask {}".format(mask)]

        self._launch_process("dwidenoise " + " ".join(args))

        self._output_package.update({
            "img": output
        })


class PrepareTopupProcess(Process):
    def __init__(
            self, out_prefix,
            dwell_time, base_config="b02b0.cnf", extra_params=""):
        super().__init__("Preparing topup process", out_prefix)

        self._dwell = dwell_time
        self._config = base_config
        self._extra = extra_params

    def set_inputs(self, package):
        self._input = package["img"]

    def execute(self):
        self._launch_process(self._execute)

    def _execute(self, log_file_path):
        ap_b0, pa_b0 = self._input
        prefix = self._get_prefix()

        std_out = sys.stdout
        with open(log_file_path, "w+") as log_file:
            log_file.write("Loading input b0 AP shapes : \n")
            log_file.write(
                "   - ".join([b0.split("/")[-1] + "\n" for b0 in ap_b0])
            )
            ap_shapes = [nib.load(b0).shape for b0 in ap_b0]

            log_file.write("Loading input b0 PA shapes : \n")
            log_file.write(
                "   - ".join([b0.split("/")[-1] + "\n" for b0 in pa_b0])
            )
            pa_shapes = [nib.load(b0).shape for b0 in pa_b0]

            log_file.write("Preparing topup params file")
            sys.stdout = log_file
            params = prepare_topup_params(ap_shapes, pa_shapes, self._dwell)
            sys.stdout = std_out

            output = {
                "param_topup": "{}_topup_params.txt".format(prefix),
                "config_topup": "{}_topup_config.cnf".format(prefix)
            }

            log_file.write(
                "Saving parameters to {}\n".format(output["param_topup"])
            )
            with open(output["param_topup"], "w+") as param_topup:
                param_topup.write(params)

            log_file.write("Generating configuration file for topup\n")
            with open(output["config_topup"], "w+") as config_file:
                config_file.write("# Resolution (knot-spacing) of warps in mm\n")
                config_file.write("--warpres=20,16,14,12,10,6,4,4,4\n")
                config_file.write("# Subsampling level (a value of 2 indicates that a 2x2x2 neighbourhood is collapsed to 1 voxel)\n")
                config_file.write("--subsamp=2,2,2,2,2,1,1,1,1\n")
                config_file.write("# FWHM of gaussian smoothing\n")
                config_file.write("--fwhm=8,6,4,3,3,2,1,0,0\n")
                config_file.write("# Maximum number of iterations\n")
                config_file.write("--miter=5,5,5,5,5,10,10,20,20\n")
                config_file.write("# Relative weight of regularisation\n")
                config_file.write("--lambda=0.005,0.001,0.0001,0.000015,0.000005,0.0000005,0.00000005,0.0000000005,0.00000000001\n")
                config_file.write("# If set to 1 lambda is multiplied by the current average squared difference\n")
                config_file.write("--ssqlambda=1\n")
                config_file.write("# Regularisation model\n")
                config_file.write("--regmod=bending_energy\n")
                config_file.write("# If set to 1 movements are estimated along with the field\n")
                config_file.write("--estmov=1,1,1,1,1,0,0,0,0\n")
                config_file.write("# 0=Levenberg-Marquardt, 1=Scaled Conjugate Gradient\n")
                config_file.write("--minmet=0,0,0,0,0,1,1,1,1\n")
                config_file.write("# Quadratic or cubic splines\n")
                config_file.write("--splineorder=3\n")
                config_file.write("# Precision for calculation and storage of Hessian\n")
                config_file.write("--numprec=double\n")
                config_file.write("# Linear or spline interpolation\n")
                config_file.write("--interp=spline\n")
                config_file.write("# If set to 1 the images are individually scaled to a common mean intensity\n")
                config_file.write("--scale=1")

            output["script_topup"] = "{}_topup_command.sh".format(prefix)

            log_file.write("Generating topup script to {}\n".format(
                output["script_topup"]
            ))
            with open(output["script_topup"], "w+") as topup_command:
                topup_command.write("#!/usr/bin/env bash\n")
                topup_command.write("in_b0=$1\n")
                topup_command.write("out_b0=$2")
                topup_command.write("echo \"Running topup on $1\\n\"\n")
                topup_command.write(
                    "topup --imain=$in_b0 --datain={} --config={} --out={} --fout={} --iout=$out_b0 {}\n".format(
                        output["param_topup"],
                        output["config_topup"],
                        "{}_topup_results".format(prefix),
                        "{}_topup_field".format(prefix),
                        output["img"],
                        self._extra
                    ))

            chmod(output["script_topup"], 0o0777)

        self._output_package.update(output)


class TopupProcess(Process):
    def __init__(self, output_prefix):
        super().__init__("Applying Topup on image", output_prefix)

    def set_inputs(self, package):
        self._input = [package["script_topup"], package["img"]]
        self._output_package.update({
            "param_topup": package["param_topup"]
        })

    def execute(self):
        output_img = append_image_extension(self._get_prefix())

        self._launch_process(
            "{} {}".format(*self._input, output_img)
        )

        self._output_package.update({
            "img": output_img
        })


class PrepareEddyProcess(Process):
    def __init__(
        self, out_prefix, repol=True, mporder=4, slspec=None, use_cuda=True
    ):
        super().__init__("Prepare Eddy process", out_prefix)

        self._repol = repol
        self._mporder = mporder
        self._slspec = slspec
        self._use_cuda = use_cuda

    def set_inputs(self, package):
        self._input = [package["bvals"], package["param_topup"]]

    def execute(self):
        self._launch_process(self._execute)

    def _execute(self, log_file_path):
        bvals, param_topup = self._input
        prefix = self._get_prefix()
        output = {
            "param_eddy": "{}_eddy_index.txt".format(prefix),
            "script_eddy": "{}_eddy_command.sh".format(prefix)
        }

        std_out = sys.stdout
        with open(log_file_path, "w+") as log_file:
            log_file.write("Input bvals : {}\n".format(bvals))

            log_file.write("Preparing eddy index files\n")

            sys.stdout = log_file
            bvals = np.loadtxt(bvals)
            indexes = prepare_eddy_index(bvals, 1)
            self._write_index_file_for_dataset(
                indexes, output["param_eddy"], log_file
            )

            sys.stdout = std_out

            log_file.write("Writing eddy command to script {}".format(
                output["script_eddy"]
            ))
            with open(output["script_eddy"], "w+") as eddy_command:
                eddy_command.write("#!/usr/bin/env bash\n")

                if self._use_cuda:
                    eddy_command.write("\n# Preparing environment\n")
                    eddy_command.write("CUDA_HOME=/usr/local/cuda-9.1\n")
                    eddy_command.write(":".join([
                        "export LD_LIBRARY_PATH=$CUDA_HOME/extras/CUPTI/lib64",
                        "$CUDA_HOME/lib64",
                        "$LD_LIBRARY_PATH\n"
                    ]))
                    eddy_command.write("export PATH=$CUDA_HOME/bin:$PATH\n")

                eddy_command.write("\n")
                eddy_command.write("in_dwi=$1\n")
                eddy_command.write("in_bvals=$2\n")
                eddy_command.write("in_bvecs=$3\n")
                eddy_command.write("in_mask=$4\n")
                eddy_command.write("in_index=$5\n")
                eddy_command.write("in_topup=$6\n")
                eddy_command.write("out_eddy=$7\n")

                eddy_command.write("echo \"Using {}\"\n\n".format(
                    "Eddy (Cuda 9.1)" if self._use_cuda else "Eddy (CPU)"
                ))

                base_args = self._get_base_eddy_arguments()

                if self._use_cuda:
                    cuda_args = []
                    if self._repol:
                        cuda_args += ["--repol"]

                    if self._mporder:
                        cuda_args += [" ".join([
                            "--mporder={}".format(self._mporder),
                            "--s2v_niter=5",
                            "--s2v_lambda=1,"
                            "--s2v_interp=spline"
                        ])]

                    if self._slspec:
                        cuda_args += [" --slspec={}".format(self._slspec)]

                    eddy_command.write("eddy_cuda {} {}".format(
                        base_args, " ".join(cuda_args)
                    ))
                else:
                    eddy_command.write("eddy {}".format(base_args))

            chmod(output["script_eddy"], 0o0777)

        self._output_package.update(output)

    def _write_index_file_for_dataset(self, indexes, file, log_file):
        log_file.write("Writing index for eddy to {}\n".format(file))
        with open(file, "w+") as f:
            f.write(" ".join([str(i) for i in indexes]))

    def _get_base_eddy_arguments(self):
        return " ".join([
            "--imain=$in_dwi --mask=$in_mask",
            "--acqp={} --index=$in_index".format(self._topup),
            "--bvecs=$in_bvecs --bvals=$in_bvals",
            "--topup=$in_topup --out=$out_eddy",
            "--data_is_shelled -v"
        ])


class EddyProcess(Process):
    def __init__(self, output_prefix):
        super().__init__("Applying Eddy", output_prefix)

        self._n_cores = cpu_count()

    def set_inputs(self, package):
        self._input = [
            package["script_eddy"], package["img"], package["mask"],
            package["bvals"], package["bvecs"],
            package["param_eddy"], package["param_topup"]
        ]

    def execute(self):
        script, img, mask, bvals, bvecs, index, topup = self._input
        prefix = self._get_prefix()

        output = {
            "img": append_image_extension(prefix),
            "bvals": "{}.bvals".format(prefix),
            "bvecs": "{}.bvecs".format(prefix)
        }

        self._launch_process(
            "{} {} {} {} {} {} {}_topup_results {}".format(
                script, img, bvals, bvecs, mask, index, topup, output["img"]
            )
        )

        self._output_package.append(output)
