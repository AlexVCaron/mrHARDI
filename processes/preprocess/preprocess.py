from multiprocessing import cpu_count
from os.path import join

from multiprocess.process import Process
from magic_monkey.b0_process import B0PostProcess, extract_b0, squash_b0
from magic_monkey.concatenate_dwi import concatenate_dwi
from magic_monkey.prepare_topup_command import prepare_topup_params
from magic_monkey.prepare_eddy_command import prepare_eddy_index
import nibabel as nib
import numpy as np
import sys
from os import chmod


class DenoiseProcess(Process):
    def __init__(self, input, output, mask):
        super().__init__("Denoise on {}".format(input.split("/")[-1]))
        self._input = input
        self._output = output
        self._mask = mask
        self._n_cores = cpu_count()

    def execute(self):
        self._launch_process(
            "dwidenoise {input} {output} -mask {mask} -nthreads {threads}".format(
                input=self._input,
                output=self._output,
                mask=self._mask,
                threads=self._n_cores
            )
        )


class ExtractB0Process(Process):
    def __init__(self, dwi_in, bvals_in, b0_out, strides=None, mean_post_proc=B0PostProcess.batch):
        super().__init__("ExtractB0 on {}".format(dwi_in.split("/")[-1]))
        self._input = [dwi_in, bvals_in]
        self._output = b0_out
        self._params = [strides, mean_post_proc]

    def execute(self):
        self._launch_process(self._execute)

    def _execute(self, log_file_path):
        std_out = sys.stdout
        with open(log_file_path, "w+") as log_file:
            log_file.write("Loading input dwi {}\n".format(self._input[0]))
            in_dwi = nib.load(self._input[0])
            bvals = np.loadtxt(self._input[1])

            log_file.write("Extracting b0 volumes\n")
            sys.stdout = log_file
            data = extract_b0(in_dwi.get_fdata(), bvals, self._params[0], self._params[1])
            sys.stdout = std_out

            log_file.write("Saving b0 volumes to file {}\n".format(self._output))

            nib.save(nib.Nifti1Image(data, in_dwi.affine), self._output)


class SquashB0Process(Process):
    def __init__(self, dwi_in, bvals_in, bvecs_in, output, dtype=np.float, mean_post_proc=B0PostProcess.batch):
        super().__init__("Squash B0 on {}".format(dwi_in.split("/")[-1]))
        self._input = [dwi_in, bvals_in, bvecs_in]
        self._output = output
        self._mean_strat = mean_post_proc
        self._dtype = dtype

    def execute(self):
        self._launch_process(self._execute)

    def _execute(self, log_file_path):
        std_out = sys.stdout
        with open(log_file_path, "w+") as log_file:
            log_file.write("Loading input dwi {}\n".format(self._input[0]))
            in_dwi = nib.load(self._input[0])
            bvals = np.loadtxt(self._input[1])
            bvecs = np.loadtxt(self._input[2])

            log_file.write("Squashing b0 volumes\n")
            sys.stdout = log_file
            data, bvals, bvecs = squash_b0(in_dwi.get_fdata(), bvals, bvecs, self._mean_strat)
            sys.stdout = std_out

            log_file.write("Saving squashed dataset to file {}".format(self._output))

            nib.save(nib.Nifti1Image(data.astype(self._dtype), in_dwi.affine), self._output)
            np.savetxt("{}.bvals".format(self._output.split(".")[0]), bvals, fmt="%d")
            np.savetxt("{}.bvecs".format(self._output.split(".")[0]), bvecs, fmt="%.6f")


class ConcatenateDatasets(Process):
    def __init__(self, dwi_list_in, out_prefix, bvals_list=None, bvecs_list=None):
        super().__init__("Concatenating DWI volumes :\n{}".format(
            "   - ".join([dwi.split("/")[-1] + "\n" for dwi in dwi_list_in])
        ))
        self._input_dwi = dwi_list_in
        self._input_bvals = bvals_list
        self._input_bvecs = bvecs_list
        self._output = out_prefix

    def execute(self):
        self._launch_process(self._execute)

    def _execute(self, log_file_path):
        std_out = sys.stdout
        with open(log_file_path, "w+") as log_file:
            log_file.write("Loading input dwi list : \n")
            log_file.write("   - ".join([dwi.split("/")[-1] + "\n" for dwi in self._input_dwi]))
            dwi_list = [nib.load(dwi) for dwi in self._input_dwi]
            bvals_list = [np.loadtxt(bvals) for bvals in self._input_bvals] if self._input_bvals else None
            bvecs_list = [np.loadtxt(bvecs) for bvecs in self._input_bvecs] if self._input_bvecs else None

            reference_affine = dwi_list[0].affine

            log_file.write("Concatenating datasets\n")
            sys.stdout = log_file
            out_dwi, out_bvals, out_bvecs = concatenate_dwi(
                [dwi.get_fdata() for dwi in dwi_list],
                bvals_list,
                bvecs_list
            )
            sys.stdout = std_out

            log_file.write("Saving volume to file {}\n".format(self._output))
            output_base = self._output.split(".")[0]

            nib.save(nib.Nifti1Image(out_dwi, reference_affine), self._output)

            if out_bvals is not None:
                log_file.write("Saving bvalues to file {}.bvals\n".format(output_base))
                np.savetxt("{}.bvals".format(output_base), out_bvals, fmt="%d")

            if out_bvecs is not None:
                log_file.write("Saving bvectors to file {}.bvecs\n".format(output_base))
                np.savetxt("{}.bvecs".format(output_base), out_bvecs.T, fmt="%.6f")


class PrepareTopupProcess(Process):
    def __init__(self, ap_b0_in, pa_b0_in, out_prefix, dwell_time, base_config="b02b0.cnf", extra_params=""):
        super().__init__("Preparing topup process")
        self._b0_vols = [ap_b0_in, pa_b0_in]
        self._dwell = dwell_time
        self._config = base_config
        self._extra = extra_params
        self._output = out_prefix

    def execute(self):
        self._launch_process(self._execute)

    def _execute(self, log_file_path):
        std_out = sys.stdout
        with open(log_file_path, "w+") as log_file:
            log_file.write("Loading input b0 AP shapes : \n")
            log_file.write("   - ".join([b0.split("/")[-1] + "\n" for b0 in self._b0_vols[0]]))
            ap_shapes = [nib.load(b0).shape for b0 in self._b0_vols[0]]
            log_file.write("Loading input b0 PA shapes : \n")
            log_file.write("   - ".join([b0.split("/")[-1] + "\n" for b0 in self._b0_vols[0]]))
            pa_shapes = [nib.load(b0).shape for b0 in self._b0_vols[1]]

            log_file.write("Preparing topup params file")
            sys.stdout = log_file
            params = prepare_topup_params(ap_shapes, pa_shapes, self._dwell)
            sys.stdout = std_out

            log_file.write("Saving parameters to file {}\n".format("{}_topup_params.txt".format(self._output)))
            with open("{}_topup_params.txt".format(self._output), "w+") as param_topup:
                param_topup.write(params)

            log_file.write("Generating configuration file for topup procedure\n")
            with open("{}_topup_config.cnf".format(self._output), "w+") as config_file:
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

            log_file.write("Generating topup script to file {}\n".format("{}_topup_command.sh".format(self._output)))
            with open("{}_topup_command.sh".format(self._output), "w+") as topup_command:
                topup_command.write("#!/usr/bin/env bash\n")
                topup_command.write("in_b0=$1\n")
                topup_command.write("echo \"Running topup on $1\\n\"\n")
                topup_command.write(
                    "topup --imain=$in_b0 --datain={} --config={} --out={} --fout={} --iout={} {}\n".format(
                        "{}_topup_params.txt".format(self._output),
                        "{}_topup_config.cnf".format(self._output),
                        "{}_topup_results".format(self._output),
                        "{}_topup_field".format(self._output),
                        "{}_topup_unwarped".format(self._output),
                        self._extra
                    ))

            chmod("{}_topup_command.sh".format(self._output), 0o0777)


class TopupProcess(Process):
    def __init__(self, script, in_b0):
        super().__init__("Applying Topup from script {} on dataset {}".format(script.split("/")[-1], in_b0.split("/")[-1]))
        self._script = script
        self._input = in_b0

    def execute(self):
        self._launch_process(
            "{} {}".format(self._script, self._input)
        )


class PrepareEddyProcess(Process):
    def __init__(self, dt_bvals, topup_acq_params, out_prefix, repol=True, mporder=4, slspec=None, use_cuda=True):
        super().__init__("Prepare Eddy process")
        self._bvals = dt_bvals
        self._topup = topup_acq_params
        self._repol = repol
        self._mporder = mporder
        self._slspec = slspec
        self._output = out_prefix
        self._use_cuda = use_cuda

    def execute(self):
        self._launch_process(self._execute)

    def _execute(self, log_file_path):
        std_out = sys.stdout
        with open(log_file_path, "w+") as log_file:
            log_file.write("Input bvals : \n")
            log_file.write("   - ".join([bvals.split("/")[-1] + "\n" for bvals in self._bvals]))

            log_file.write("Preparing eddy index files\n")
            acc_b0s = 1

            sys.stdout = log_file
            for bvals in self._bvals:
                ap_bvals = np.loadtxt(bvals)
                indexes = prepare_eddy_index(ap_bvals, acc_b0s)
                acc_b0s = int(indexes[-1]) + 1
                self._write_index_file_for_dataset(indexes, bvals.split("/")[-1].split(".")[0], log_file)

            sys.stdout = std_out

            log_file.write("Writing eddy command to script {}".format("{}_eddy_command.sh".format(self._output)))
            with open("{}_eddy_command.sh".format(self._output), "w+") as eddy_command:
                eddy_command.write("#!/usr/bin/env bash\n")

                if self._use_cuda:
                    eddy_command.write("\n# Preparing environment\n")
                    eddy_command.write("CUDA_HOME=/usr/local/cuda-9.1\n")
                    eddy_command.write("export LD_LIBRARY_PATH=$CUDA_HOME/extras/CUPTI/lib64:$CUDA_HOME/lib64:$LD_LIBRARY_PATH\n")
                    eddy_command.write("export PATH=$CUDA_HOME/bin:$PATH\n")

                eddy_command.write("\n")
                eddy_command.write("in_dwi=$1\n")
                eddy_command.write("in_bvals=$2\n")
                eddy_command.write("in_bvecs=$3\n")
                eddy_command.write("in_mask=$4\n")
                eddy_command.write("in_index=$5\n")
                eddy_command.write("in_topup=$6\n")
                eddy_command.write("out_eddy=$7\n")

                eddy_command.write("echo \"Using {}\"\n\n".format("Eddy (Cuda 9.1)" if self._use_cuda else "Eddy (CPU)"))

                base_args = self._get_base_eddy_arguments()

                if self._use_cuda:
                    cuda_args = []
                    if self._repol:
                        cuda_args += ["--repol"]

                    if self._mporder:
                        cuda_args += ["--mporder={} --s2v_niter=5 --s2v_lambda=1 --s2v_interp=spline".format(
                            self._mporder)]

                    if self._slspec:
                        cuda_args += [" --slspec={}".format(self._slspec)]

                    # eddy_command.write("nvprof --metrics dram_utilization --devices 0 --log-file {0}/cuda.log ".format(
                    #     "/{}".format(join(*(self._output.split("/")[:-1])))
                    # ))
                    eddy_command.write("eddy_cuda {} {}".format(base_args, " ".join(cuda_args)))
                else:
                    eddy_command.write("eddy {}".format(base_args))

            chmod("{}_eddy_command.sh".format(self._output), 0o0777)

    def _write_index_file_for_dataset(self, indexes, base_name, log_file):
        log_file.write("Writing index for eddy to file {}\n".format("{}_index.txt".format(base_name)))
        with open("/{}_index.txt".format(join(*(self._output.split("/")[:-1]), base_name)), "w+") as f:
            f.write(" ".join([str(i) for i in indexes]))

    def _get_base_eddy_arguments(self):
        return "--imain=$in_dwi --mask=$in_mask --acqp={} --index=$in_index --bvecs=$in_bvecs --bvals=$in_bvals --topup=$in_topup --out=$out_eddy --data_is_shelled -v".format(
                    self._topup
                )


class EddyProcess(Process):
    def __init__(self, script, in_dwi, in_bvals, in_bvecs, mask, in_index, in_topup, out_eddy):
        super().__init__("Applying Eddy from script {} on dataset".format(script.split("/")[-1], in_dwi.split("/")[-1]))
        self._script = script
        self._input = [in_dwi, in_bvals, in_bvecs]
        self._mask = mask
        self._index = in_index
        self._topup = in_topup
        self._output = out_eddy
        self._n_cores = cpu_count()

    def execute(self):
        self._launch_process("{} {} {} {} {} {} {}_topup_results {}".format(self._script, *self._input, self._mask, self._index, self._topup, self._output))
