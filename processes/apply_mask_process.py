import sys
import nibabel as nib

from magic_monkey.apply_mask import apply_mask_on_data
from multiprocess.process import Process


class ApplyMaskProcess(Process):
    def __init__(self, in_data, in_mask, out_data):
        super().__init__("Apply mask to {}".format(in_data))
        self._input = in_data
        self._mask = in_mask
        self._output = out_data

    def execute(self):
        self._launch_process(self._execute)

    def _execute(self, log_file_path):
        std_out = sys.stdout
        with open(log_file_path, "w+") as log_file:
            log_file.write("Loading input volume {}\n".format(self._input))
            data = nib.load(self._input)
            log_file.write("Loading mask {}\n".format(self._mask))
            mask = nib.load(self._mask).get_fdata().astype(bool)

            log_file.write("Applying mask to data")
            sys.stdout = log_file
            out_data = apply_mask_on_data(data.get_fdata(), mask)
            sys.stdout = std_out

            log_file.write("Saving volume to file {}.nii\n".format(self._output))
            nib.save(nib.Nifti1Image(out_data, data.affine), self._output)
