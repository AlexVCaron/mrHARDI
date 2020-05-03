import tempfile
import h5py
import numpy as np


DATA_KEYS = ["img", "bvals", "bvecs", "affine", "mask", "anat"]


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
    subject, idx, shape, dtype=float, init_val=None, single_anat=True, single_mask=True
):
    if single_anat:
        subject.create_dataset(
            "anat", shape, dtype, np.full(shape, init_val if init_val else idx)
        )
    if single_mask:
        subject.create_dataset("mask", shape, dtype, np.ones(shape))


def create_pipeline_input_rep(
    subject, rep, s_idx, r_idx, shape, dtype=float, init_val=None, mask=False, anat=False
):
    rep.create_dataset("img", shape, dtype, np.full(shape, init_val if init_val else s_idx))
    rep.create_dataset("bvals", (shape[-1],), dtype, np.arange(0, shape[-1]))
    rep.create_dataset("bvecs", (shape[-1], 3), dtype, np.repeat(np.arange(0, shape[-1])[:, None], 3, axis=1))
    rep.create_dataset("affine", (4, 4), dtype, np.diag([1, 1, 1, 1]))

    if mask:
        rep.create_dataset("mask", shape, dtype, np.ones(shape))

    if anat:
        rep.create_dataset("anat", shape, dtype, np.full(shape, init_val if init_val else s_idx))


def assert_data_point(data, data_shape, key_modifiers={}):
    k_mods = {**{k: k for k in data.keys()}, **key_modifiers}

    for key in DATA_KEYS:
        assert k_mods[key] in data.keys(), "Key '{}' is not in the data".format(key)

    np.testing.assert_equal(data[k_mods["img"]].shape, data_shape)
    np.testing.assert_equal(data[k_mods["bvals"]], np.arange(0, data_shape[-1]))
    np.testing.assert_equal(data[k_mods["bvecs"]], np.repeat(np.arange(0, data_shape[-1])[:, None], 3, axis=1))
    np.testing.assert_equal(data[k_mods["affine"]], np.diag([1, 1, 1, 1]))
