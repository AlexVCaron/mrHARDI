from multiprocessing import cpu_count
from multiprocess.process import Process
import nibabel as nib
from numpy import zeros, apply_along_axis, ones
from magic_monkey.compute_fa_from_mrtrix_dt import compute_eigens, compute_fa


class DTIProcess(Process):
    def __init__(self, in_dwi, in_bvals, in_bvecs, out_dt, mask=None, n_proc=cpu_count()):
        super().__init__("Mrtrix DTI process")
        self._input = in_dwi
        self._bvals = in_bvals
        self._bvecs = in_bvecs
        self._mask = mask
        self._output = out_dt
        self._n_cores = n_proc

    def execute(self):
        options = "-fslgrad {} {} -nthreads {}".format(
            self._bvecs, self._bvals, self._n_cores
        )
        if self._mask:
            options += " -mask {}".format(self._mask)

        self._launch_process(
            "dwi2tensor {} {} {}".format(
                options, self._input, self._output
            )
        )


class ComputeFAProcess(Process):
    def __init__(self, in_dt, out_fa, mask=None):
        super().__init__("Compute FA from DT process")
        self._input = in_dt
        self._output = out_fa
        self._mask = mask

    def execute(self):
        self._launch_process(self._execute)

    def _execute(self, log_file_path):
        with open(log_file_path, "w+") as log_file:
            log_file.write("Opening input diffusion tensor image {}\n".format(self._input))
            dt_img = nib.load(self._input)

            if self._mask:
                log_file.write("Opening input mask {}\n".format(self._mask))
                mask = nib.load(self._mask)
            else:
                mask = ones(dt_img.shape[:-1])

            log_file.write("Calculating FA on diffusion tensors")
            fa_map = zeros(mask.shape)
            fa_map[mask.get_fdata().astype(bool)] = apply_along_axis(
                lambda dt: compute_fa(compute_eigens(dt)[0]),
                arr=dt_img.get_fdata()[mask.get_fdata().astype(bool)],
                axis=1
            )

            log_file.write("Saving FA map to {}".format(self._output))
            nib.save(nib.Nifti1Image(fa_map, dt_img.affine), self._output)
