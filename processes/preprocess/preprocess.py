import sys

import nibabel as nib
import numpy as np

from config import append_image_extension
from magic_monkey.b0_process import B0PostProcess, extract_b0, squash_b0
from magic_monkey.concatenate_dwi import concatenate_dwi
from piper.pipeline.process import PythonProcess


class ExtractB0Process(PythonProcess):
    def __init__(
        self, output_prefix, strides=None,
        mean_post_proc=B0PostProcess.batch, img_key_deriv="img"
    ):
        super().__init__(
            "ExtractB0 from a dwi volume", output_prefix,
            [img_key_deriv, "bvals"]
        )

        self._params = [strides, mean_post_proc]

        self._input = None

    def get_required_output_keys(self):
        return [self.primary_input_key]

    def _execute(self, log_file_path, *args, **kwargs):
        img, bvals = self._input
        strides, mean_fn = self._params
        output = append_image_extension(self._get_prefix())

        std_out = sys.stdout
        with open(log_file_path, "w+") as log_file:
            log_file.write("Loading input dwi {}\n".format(img))
            in_dwi = nib.load(img)
            bvals = np.loadtxt(bvals)

            log_file.write("Extracting b0 volumes\n")
            sys.stdout = log_file
            data = extract_b0(in_dwi.get_fdata(), bvals, strides, mean_fn)
            sys.stdout = std_out

            log_file.write("Saving b0 volumes to {}\n".format(output))

            nib.save(nib.Nifti1Image(data, in_dwi.affine), output)

        self._output_package.update({
            self.primary_input_key: output
        })


class SquashB0Process(PythonProcess):
    def __init__(
        self, output_prefix, dtype=np.float,
        mean_post_proc=B0PostProcess.batch, img_key_deriv="img"
    ):
        super().__init__(
            "Squash B0 of a dwi volume", output_prefix,
            [img_key_deriv, "bvals", "bvecs"]
        )

        self._mean_strat = mean_post_proc
        self._dtype = dtype

        self._input = None

    def get_required_output_keys(self):
        return [self.primary_input_key, "bvals", "bvecs"]

    def _execute(self, log_file_path, *args, **kwargs):
        img, bvals, bvecs = self._input
        prefix = self._get_prefix()

        std_out = sys.stdout
        with open(log_file_path, "w+") as log_file:
            log_file.write("Loading input dwi {}\n".format(img))
            in_dwi = nib.load(img)
            bvals = np.loadtxt(bvals)
            bvecs = np.loadtxt(bvecs)

            log_file.write("Squashing b0 volumes\n")
            sys.stdout = log_file
            data, bvals, bvecs = squash_b0(
                in_dwi.get_fdata(), bvals, bvecs, self._mean_strat
            )
            sys.stdout = std_out

            output_img = append_image_extension(prefix)
            log_file.write(
                "Saving squashed dataset to file {}".format(output_img)
            )
            nib.save(
                nib.Nifti1Image(data.astype(self._dtype), in_dwi.affine),
                output_img
            )
            np.savetxt("{}.bvals".format(prefix), bvals, fmt="%d")
            np.savetxt("{}.bvecs".format(prefix), bvecs, fmt="%.6f")

        self._output_package.update({
            self.primary_input_key: output_img,
            "bvals": "{}.bvals".format(prefix),
            "bvecs": "{}.bvecs".format(prefix)
        })


class ConcatenateDatasets(PythonProcess):
    def __init__(self, output_prefix, img_key_deriv="img", with_grads=True):
        keys = [img_key_deriv, "bvals", "bvecs"]
        super().__init__(
            "Concatenating DWI volumes", "{}.nii.gz".format(output_prefix),
            keys if with_grads else [img_key_deriv],
            ["bvals", "bvecs"]
        )

    def get_required_output_keys(self):
        return [self.primary_input_key]

    def _execute(self, log_file_path, *args, **kwargs):
        in_dwi, in_bvals, in_bvecs = self._input
        prefix = self._get_prefix()

        std_out = sys.stdout
        with open(log_file_path, "w+") as log_file:
            log_file.write("Loading input dwi list : \n")
            log_file.write("   - ".join([
                dwi.split("/")[-1] + "\n" for dwi in in_dwi
            ]))
            dwi_list = [nib.load(dwi) for dwi in in_dwi]
            bvals_list = [
                np.loadtxt(bvals) for bvals in in_bvals
            ] if in_bvals else None
            bvecs_list = [
                np.loadtxt(bvecs) for bvecs in in_bvals
            ] if in_bvals else None

            reference_affine = dwi_list[0].affine

            log_file.write("Concatenating datasets\n")
            sys.stdout = log_file
            out_dwi, out_bvals, out_bvecs = concatenate_dwi(
                [dwi.get_fdata() for dwi in dwi_list],
                bvals_list,
                bvecs_list
            )
            sys.stdout = std_out

            output = {self.primary_input_key: append_image_extension(prefix)}
            log_file.write("Saving volume to file {}\n".format(
                output[self.primary_input_key])
            )

            nib.save(
                nib.Nifti1Image(out_dwi, reference_affine),
                output[self.primary_input_key]
            )

            if out_bvals is not None:
                output["bvals"] = "{}.bvals".format(prefix)
                log_file.write("Saving bvals to {}\n".format(output["bvals"]))
                np.savetxt(output["bvals"], out_bvals, fmt="%d")

            if out_bvecs is not None:
                output["bvecs"] = "{}.bvecs".format(prefix)
                log_file.write("Saving bvecs to {}\n".format(output["bvecs"]))
                np.savetxt(output["bvecs"], out_bvecs.T, fmt="%.6f")

        self._output_package.update(output)

    @classmethod
    def prepare_input(cls, datapoints):
        return {
            k: {kk: [d[kk] for d in v] for kk in v[0]}
            for k, v in datapoints.items()
        }
