from os import getcwd
from os.path import basename, join
import nibabel as nib
import numpy as np

from mrHARDI.base.shell import launch_shell_process
from mrHARDI.base.utils import if_join_str, split_ext
from mrHARDI.compute.math.stats import center_of_mass_difference
from mrHARDI.compute.utils import (compute_reorientation_to_frame,
                                   compute_reorientation_to_image,
                                   load_transform,
                                   save_transform)


def get_common_spacing(img_list, vote=min):
    spacing = []
    for img in img_list:
        _img = nib.load(img)
        spacing.append(vote(_img.header.get_zooms()[:3]))

    return vote(spacing)


def transform_images(
    images, transform_fname, suffix=None, base_dir=None, mask=None
):
    if base_dir is None:
        base_dir = getcwd()

    names = []
    for image in images:
        name, ext = split_ext(image, r"^(/?.*)\.(nii\.gz|nii)$")
        names.append(join(base_dir, "{}.{}".format(
            if_join_str([basename(name), suffix], "_"), ext
        )))

        img = nib.load(image)
        img_ornt = nib.io_orientation(img.affine)
        transform = load_transform(transform_fname, img_ornt)

        img = nib.Nifti1Image(
            img.get_fdata(), transform @ img.affine, img.header
        )

        nib.save(img, names[-1])

    out_mask = None
    if mask is not None:
        name, ext = split_ext(mask, r"^(/?.*)\.(nii\.gz|nii)$")
        out_mask = join(base_dir, "{}.{}".format(
            if_join_str([basename(name), suffix], "_"), ext
        ))

        img = nib.load(mask)
        img_ornt = nib.io_orientation(img.affine)
        transform = load_transform(transform_fname, img_ornt)

        img = nib.Nifti1Image(
            img.get_fdata(), transform @ img.affine, img.header
        )

        nib.save(img, out_mask)

    return names, out_mask


def align_by_center_of_mass(
    ref_fname, moving_fnames, out_mat_fname,
    ref_mask_fname=None, moving_mask_fname=None,
    align_mask_fnames=None, suffix=None, base_dir=None
):
    if base_dir is None:
        base_dir = getcwd()

    ref_img, main_img = nib.load(ref_fname), nib.load(moving_fnames[0])
    if ref_mask_fname:
        ref_mask = nib.load(ref_mask_fname).get_fdata().astype(bool)
    else:
        ref_mask = np.ones(ref_img.shape, dtype=bool)

    if moving_mask_fname:
        mov_mask = nib.load(moving_mask_fname).get_fdata().astype(bool)
    else:
        mov_mask = np.ones(main_img.shape, dtype=bool)

    main_to_ref = np.linalg.inv(ref_img.affine) @ \
        compute_reorientation_to_image(main_img, ref_img) @ main_img.affine

    ref_data = ref_img.get_fdata().astype(ref_img.get_data_dtype())
    main_data = main_img.get_fdata().astype(main_img.get_data_dtype())
    ref_data[~ref_mask] = 0
    main_data[~mov_mask] = 0

    trans = center_of_mass_difference(
        ref_data, main_data, main_to_ref, ref_img.header.get_zooms()[:3]
    )

    out_files = []
    for fname in moving_fnames:
        img = nib.load(fname)
        _t = compute_reorientation_to_image(ref_img, img)

        affine = img.affine
        affine[:3, 3] += _t[:3, :3] @ trans

        # Get extension, which can either be .nii or .nii.gz
        name, ext = split_ext(fname, r"^(/?.*)\.(nii\.gz|nii)$")
        out_files.append(join(base_dir, "{}.{}".format(
            if_join_str([basename(name), suffix], "_"), ext
        )))

        nib.save(
            nib.Nifti1Image(img.get_fdata(), affine, img.header),
            out_files[-1]
        )

    if align_mask_fnames is not None:
        for fname in align_mask_fnames:
            img = nib.load(fname)
            _t = compute_reorientation_to_image(ref_img, img)

            affine = img.affine
            affine[:-1, 3] += _t[:3, :3] @ trans

            name, ext = split_ext(fname, r"^(/?.*)\.(nii\.gz|nii)$")
            out_files.append(join(base_dir, "{}.{}".format(
                if_join_str([basename(name), suffix], "_"), ext
            )))

            nib.save(
                nib.Nifti1Image(img.get_fdata(), affine, img.header),
                out_files[-1]
            )

    _m = np.eye(4)
    _m[:3, 3] = trans
    save_transform(
        _m, "MatrixOffsetTransformBase_double_3_3", out_mat_fname
    )

    return out_files


def merge_transforms(
    out_transform, log_file, *transforms, additional_env=None
):
    cmd = "antsApplyTransforms {} -o Linear[{},0]".format(
        " ".join("-t {}".format(t) for t in transforms[::-1]),
        out_transform
    )

    launch_shell_process(
        cmd, log_file,
        additional_env=additional_env
    )
