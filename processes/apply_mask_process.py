import sys

import nibabel as nib

from config import append_image_extension
from magic_monkey.apply_mask import apply_mask_on_data
from multiprocess.pipeline.process import Process


class ApplyMaskProcess(Process):
    def __init__(self, output_prefix, img_key_deriv="img"):
        super().__init__("Apply mask", output_prefix, [img_key_deriv, "mask"])

    def _execute(self, log_file_path, *args, **kwargs):
        img, mask = self._input
        output_img = append_image_extension(self._get_prefix())

        std_out = sys.stdout
        with open(log_file_path, "w+") as log_file:
            log_file.write("Loading input volume {}\n".format(img))
            data = nib.load(img)
            log_file.write("Loading mask {}\n".format(mask))
            mask = nib.load(mask).get_fdata().astype(bool)

            log_file.write("Applying mask to data")
            sys.stdout = log_file
            out_data = apply_mask_on_data(data.get_fdata(), mask)
            sys.stdout = std_out

            log_file.write("Saving volume to file {}.nii\n".format(output_img))
            nib.save(nib.Nifti1Image(out_data, data.affine), output_img)

        self._output_package.update({
            self.primary_input_key: output_img
        })
