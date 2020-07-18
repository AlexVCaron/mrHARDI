import json
import os

import nibabel as nib
import numpy as np

from helpers.data import create_pipeline_input_rep_dict


def generate_fake_dir_dataset(
    output_root, n_subjects, n_repetitions, shape, dtype=float,
    init_value=None, subject_fmt="sub_{}", repetition_fmt="sub_{}_rep_{}",
    global_subject_mask=True, global_subject_anat=True
):
    assert len(os.listdir(output_root)) == 0

    for s in range(1, n_subjects + 1):
        s_name = subject_fmt.format(s)
        s_root = os.path.join(output_root, s_name)
        os.makedirs(s_root)

        if global_subject_mask:
            nib.save(
                nib.Nifti1Image(
                    np.ones(shape[:-1], int),
                    np.diag([1, 1, 1, 1])
                ),
                os.path.join(s_root, "{}_mask.nii.gz".format(s_name))
            )

        if global_subject_anat:
            nib.save(
                nib.Nifti1Image(
                    np.full(
                        shape[:-1], init_value if init_value else s, dtype
                    ),
                    np.diag([1, 1, 1, 1])
                ),
                os.path.join(s_root, "{}_anat.nii.gz".format(s_name))
            )

        for r in range(1, n_repetitions + 1):
            r_name = repetition_fmt.format(s, r)
            r_root = os.path.join(s_root, r_name)
            os.makedirs(r_root)

            config = {"acq_direction": "AP" if r % 2 == 0 else "PA"}
            with open(os.path.join(r_root, "rep_config.json"), "w+") as f:
                json.dump(config, f)

            data = create_pipeline_input_rep_dict(
                s, r, shape, dtype, init_value,
                not global_subject_mask, not global_subject_anat
            )

            nib.save(
                nib.Nifti1Image(data["img"], data["affine"]),
                os.path.join(r_root, "{}_dwi.nii.gz".format(r_name))
            )
            np.savetxt(
                os.path.join(r_root, "{}_dwi.bvals".format(r_name)),
                data["bvals"][None, :],
                '%d'
            )
            np.savetxt(
                os.path.join(r_root, "{}_dwi.bvecs".format(r_name)),
                data["bvecs"].T,
                '%.8f'
            )

            if not global_subject_mask:
                nib.save(
                    nib.Nifti1Image(data["mask"].astype(int), data["affine"]),
                    os.path.join(r_root, "{}_mask.nii.gz".format(r_name))
                )

            if not global_subject_anat:
                nib.save(
                    nib.Nifti1Image(data["anat"], data["affine"]),
                    os.path.join(r_root, "{}_anat.nii.gz".format(r_name))
                )


if __name__ == "__main__":
    pass
    # TODO : implement the parser
