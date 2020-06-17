from multiprocessing import cpu_count

import nibabel as nib
from numpy import zeros, apply_along_axis, ones

from config import append_image_extension
from magic_monkey.compute_fa_from_mrtrix_dt import compute_eigens, compute_fa
from multiprocess.pipeline.process import Process


class DTIProcess(Process):
    def __init__(
        self, output_prefix, n_proc=cpu_count(),
        masked=True, img_key_deriv="img"
    ):
        keys = [img_key_deriv, "bvals", "bvecs"]
        super().__init__(
            "Mrtrix DTI process", output_prefix,
            keys + ["mask"] if masked else keys,
            ["mask"]
        )

        self._n_cores = n_proc

    def _execute(self, options, img, output_img, *args, **kwargs):
        return "dwi2tensor {} {} {}".format(
            options, img, output_img
        )

    def execute(self, *args, **kwargs):
        img, bvals, bvecs, mask = self._input
        output_img = append_image_extension(self._get_prefix())

        options = "-fslgrad {} {} -nthreads {}".format(
            bvecs, bvals, self._n_cores
        )
        if mask:
            options += " -mask {}".format(mask)

        super().execute(options, img, output_img)

        self._output_package.update({
            self.primary_input_key: output_img
        })


class ComputeFAProcess(Process):
    def __init__(self, output_prefix, masked=True, img_key_deriv="img"):
        super().__init__(
            "Compute FA from DT process", output_prefix,
            [img_key_deriv, "mask"] if masked else [img_key_deriv],
            ["mask"]
        )

    def _execute(self, log_file_path, *args, **kwargs):
        img, mask = self._input
        output_img = append_image_extension(self._get_prefix())

        with open(log_file_path, "w+") as log_file:
            log_file.write(
                "Opening input diffusion tensor image {}\n".format(img)
            )
            dt_img = nib.load(img)

            if mask:
                log_file.write("Opening input mask {}\n".format(mask))
                mask = nib.load(mask)
            else:
                mask = ones(dt_img.shape[:-1])

            log_file.write("Calculating FA on diffusion tensors")
            fa_map = zeros(mask.shape)
            fa_map[mask.get_fdata().astype(bool)] = apply_along_axis(
                lambda dt: compute_fa(compute_eigens(dt)[0]),
                arr=dt_img.get_fdata()[mask.get_fdata().astype(bool)],
                axis=1
            )

            log_file.write("Saving FA map to {}".format(output_img))
            nib.save(nib.Nifti1Image(fa_map, dt_img.affine), output_img)

        self._output_package.update({
            self.primary_input_key: output_img
        })
