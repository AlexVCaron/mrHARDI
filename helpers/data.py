import json
import os
import tempfile

import h5py
import nibabel as nib
import numpy as np

DATA_KEYS = ["img", "bvals", "bvecs", "affine", "mask", "anat"]


def load_dwi_repetition(subject, repetition, repetition_path):
    base_name = os.path.join(
        repetition_path, "{}_".format(repetition) + "{}.{}"
    )

    with open(os.path.join(repetition_path, "rep_config.json")) as f:
        rep_config = json.load(f)

    affine = nib.load(base_name.format("dwi", "nii.gz")).affine

    data = {
        "img": base_name.format("dwi", "nii.gz"),
        "bvals": base_name.format("dwi", "bvals"),
        "bvecs": base_name.format("dwi", "bvecs"),
        "dir": rep_config["acq_direction"],
        "affine": affine
    }

    if os.path.exists(base_name.format("mask", "nii.gz")):
        data["mask"] = base_name.format("mask", "nii.gz")
    if os.path.exists(base_name.format("anat", "nii.gz")):
        data["anat"] = base_name.format("anat", "nii.gz")

    return data


def create_hdf5_dataset(
    n_subjects, n_reps, output_prefix, rep_fn,
    sub_fn=lambda *args, **kwargs: None,
    temporary=True, auto_delete=True
):
    if temporary:
        file = tempfile.NamedTemporaryFile(
            prefix=output_prefix, delete=auto_delete,
        )
    else:
        file = open(output_prefix, "w")

    with h5py.File(file, "w") as archive:
        for i in range(n_subjects):
            subject = archive.create_group("sub{}".format(i))
            sub_fn(subject, i)

            for j in range(n_reps):
                rep = subject.create_group("rep{}".format(j))
                rep_fn(subject, rep, i, j)

    return file


def create_pipeline_input_subject(
    subject, idx, shape, dtype=float, init_val=None,
    single_anat=True, single_mask=True
):
    if single_anat:
        subject.create_dataset(
            "anat", shape, dtype, np.full(shape, init_val if init_val else idx)
        )
    if single_mask:
        subject.create_dataset("mask", shape, dtype, np.ones(shape))


def create_pipeline_input_rep_h5(
    subject, rep, s_idx, r_idx, shape, dtype=float,
    init_val=None, mask=False, anat=False
):
    data = create_pipeline_input_rep_dict(
        s_idx, r_idx, shape, dtype, init_val, mask, anat
    )

    rep.create_dataset("img", shape, dtype, data["img"])
    rep.create_dataset("bvals", (shape[-1],), dtype, data["bvals"])
    rep.create_dataset("bvecs", (shape[-1], 3), dtype, data["bvecs"])
    rep.create_dataset("affine", (4, 4), dtype, data["affine"])

    if mask:
        rep.create_dataset("mask", shape[:-1], dtype, data["mask"])

    if anat:
        rep.create_dataset("anat", shape[:-1], dtype, data["anat"])


def create_pipeline_input_rep_dict(
    s_idx, r_idx, shape, dtype=float, init_val=None, mask=False, anat=False
):
    data = {
        "img": np.full(shape, init_val if init_val else s_idx, dtype),
        "bvals": np.arange(0, shape[-1]).astype(dtype),
        "bvecs": np.repeat(
            np.arange(0, shape[-1])[:, None], 3, axis=1
        ).astype(dtype),
        "affine": np.diag([1, 1, 1, 1]).astype(dtype)
    }
    if mask:
        data["mask"] = np.ones(shape[:-1], dtype)

    if anat:
        data["anat"] = np.full(
            shape[:-1], init_val if init_val else s_idx, dtype
        )

    return data


def assert_data_point(data, data_shape, key_modifiers={}, dtype=float):
    k_mods = {**{k: k for k in data.keys()}, **key_modifiers}

    for key in DATA_KEYS:
        assert k_mods[key] in data.keys(), \
            "Key '{}' is not in the data".format(key)

    np.testing.assert_equal(data[k_mods["img"]].shape, data_shape)
    np.testing.assert_equal(
        data[k_mods["affine"]], np.diag([1, 1, 1, 1]).astype(dtype)
    )
    np.testing.assert_equal(
        data[k_mods["bvals"]], np.arange(0, data_shape[-1]).astype(dtype)
    )
    np.testing.assert_equal(
        data[k_mods["bvecs"]],
        np.repeat(
            np.arange(0, data_shape[-1])[:, None], 3, axis=1
        ).astype(dtype)
    )
