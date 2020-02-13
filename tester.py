import nibabel as nib
import numpy as np
from magic_monkey.b0_process import extract_b0, B0PostProcess

pa = nib.load("/media/vala2004/b1f812ac-9843-4a1f-877a-f1f3bd303399/data/mcgill/amir_schmuel/pa_1/3_DiffRaw_SuperRes.nii")
ap = nib.load("/media/vala2004/b1f812ac-9843-4a1f-877a-f1f3bd303399/data/mcgill/amir_schmuel/ap_1/2_DiffRaw_SuperRes.nii")

ap_bvals = np.loadtxt("/media/vala2004/b1f812ac-9843-4a1f-877a-f1f3bd303399/data/mcgill/amir_schmuel/base/2/20190617_105138ep2dgsliderp8mmisoCUSPs008a001_new.bval")
pa_bvals = np.loadtxt("/media/vala2004/b1f812ac-9843-4a1f-877a-f1f3bd303399/data/mcgill/amir_schmuel/base/3_PA/20190617_105138ep2dgsliderp8mmisoCUSPPAs010a001_new.bval")

b0_pa = extract_b0(pa.get_fdata(), pa_bvals, mean=B0PostProcess.batch)
b0_ap = extract_b0(ap.get_fdata(), ap_bvals, mean=B0PostProcess.batch)

nib.save(nib.Nifti1Image(b0_pa, pa.affine, pa.header), "/media/vala2004/b1f812ac-9843-4a1f-877a-f1f3bd303399/data/mcgill/amir_schmuel/processing/b0_preproc/stride30_b0_pa.nii.gz")
nib.save(nib.Nifti1Image(b0_ap, ap.affine, ap.header), "/media/vala2004/b1f812ac-9843-4a1f-877a-f1f3bd303399/data/mcgill/amir_schmuel/processing/b0_preproc/stride30_b0_ap.nii.gz")
