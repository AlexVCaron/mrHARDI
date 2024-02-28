from os import getcwd, makedirs
from os.path import basename, dirname, join, exists
from shutil import copyfile, copytree, rmtree
from tempfile import TemporaryDirectory

import nibabel as nib
import numpy as np
from traitlets import Dict, Instance, Unicode, Bool, Enum
from traitlets.config.loader import ArgumentError

import nibabel as nib

from mrHARDI.base.ants import create_ants_transform_script
from mrHARDI.base.application import (mrHARDIBaseApplication,
                                      MultipleArguments,
                                      output_prefix_argument,
                                      required_arg,
                                      required_file)
from mrHARDI.base.dwi import load_metadata, save_metadata
from mrHARDI.base.shell import launch_shell_process
from mrHARDI.base.utils import split_ext
from mrHARDI.compute.image import (align_by_center_of_mass,
                                   get_common_spacing,
                                   transform_images,
                                   merge_transforms)
from mrHARDI.compute.utils import load_transform
from mrHARDI.config.ants import (AntsConfiguration,
                                 AntsTransformConfiguration,
                                 AntsMotionCorrectionConfiguration,
                                 ImageType)
from mrHARDI.traits.ants import AntsAffine, AntsRigid, AntsSyN


_reg_aliases = {
    'target': 'AntsRegistration.target_images',
    'moving': 'AntsRegistration.moving_images',
    'mask': 'AntsRegistration.mask',
    'out': 'AntsRegistration.output_prefix'
}

_reg_flags = dict(
    verbose=(
        {"AntsRegistration": {'verbose': True}},
        "Enables verbose output"
    ),
    init_ai=(
        {"AntsRegistration": {'init_with_ants_ai': True}},
        "Generates initial transformation using grid search"
    )
)

_reg_description = """
Perform registration of a dataset over another one using Ants [1]. More 
information on the construction of an Ants command can be found here [2].

References :
------------
[1] http://stnava.github.io/ANTs/
[2] https://github.com/ANTsX/ANTs/wiki/Anatomy-of-an-antsRegistration-call
"""


class AntsRegistration(mrHARDIBaseApplication):
    name = u"ANTs Registration"
    description = _reg_description
    configuration = Instance(AntsConfiguration).tag(config=True)

    target_images = required_arg(
        MultipleArguments, traits_args=(Unicode(),),
        description="List of target images used in the passes of "
                    "registration. Those must equal the number of metric "
                    "evaluations of the resulting output command, including "
                    "the initial transform (if selected)"
    )
    moving_images = required_arg(
        MultipleArguments, traits_args=(Unicode(),),
        description="List of moving images used in the passes of "
                    "registration. Those must equal the number of metric "
                    "evaluations of the resulting output command, including "
                    "the initial transform (if selected)"
    )

    mask = MultipleArguments(
        Unicode(),
        help="Mask for the fixed and target images. If two masks are "
             "provided, they will be used independently, the first for "
             "the target, the second for the moving."
    ).tag(config=True)

    output_prefix = output_prefix_argument()

    init_with_ants_ai = Bool(False).tag(config=True)

    verbose = Bool(False).tag(config=True)

    aliases = Dict(default_value=_reg_aliases)
    flags = Dict(default_value=_reg_flags)

    def _generate_config_file(self, filename):
        self.configuration.passes = [
            AntsRigid(), AntsAffine(), AntsSyN()
        ]
        super()._generate_config_file(filename)

    def _setup_ants_ai_input(
        self, image_fname, log_file,
        ref_fname=None, mask_fname=None,
        spacing=None, additional_env=None,
        base_dir=None
    ):
        if base_dir is None:
            base_dir = getcwd()

        name, ext = split_ext(basename(image_fname), r"^(/?.*)\.(nii\.gz|nii)$")
        image = nib.load(image_fname)

        if spacing is None:
            spacing = 3. * min(image.header.get_zooms()[:3])

        if mask_fname:
            image_fname = join(base_dir, "{}_masked.{}".format(name, ext))

            mask = nib.load(mask_fname).get_fdata().astype(bool)
            data = image.get_fdata()
            data[~mask] = 0.

            nib.save(
                nib.Nifti1Image(data, image.affine, image.header),
                image_fname
            )

        cmd = [
            "scil_crop_volume.py {} {} --output_bbox {} -f".format(
                image_fname,
                join(base_dir, "{}_cropped.{}".format(name, ext)),
                join(base_dir, "{}_bbox.pkl".format(name))
            )
        ]
        image_fname = join(base_dir, "{}_cropped.{}".format(name, ext))

        if mask_fname:
            cmd.append("scil_crop_volume.py {} {} --input_bbox {} -f".format(
                mask_fname,
                join(base_dir, "{}_mask_cropped.{}".format(name, ext)),
                join(base_dir, "{}_bbox.pkl".format(name))
            ))
            mask_fname = join(base_dir, "{}_mask_cropped.{}".format(name, ext))

        if ref_fname and self.configuration.match_histogram:
            cmd.append("ImageMath 3 {} HistogramMatch {} {}".format(
                join(base_dir, "{}_hmatch.{}".format(name, ext)),
                image_fname,
                ref_fname
            ))
            image_fname = join(base_dir, "{}_hmatch.{}".format(name, ext))

        cmd.append("ResampleImageBySpacing 3 {} {} {} {} {} 1".format(
            image_fname,
            join(base_dir, "{}_res.{}".format(name, ext)),
            spacing, spacing, spacing
        ))

        for c in cmd: 
            launch_shell_process(
                c, log_file, additional_env=additional_env
            )

        return join(base_dir, "{}_res.{}".format(name, ext))

    def _call_ants_ai(
        self, targets, movings, ants_config, transform_fname,
        resampling_factor=3.,
        angular_step=40, angular_range=60,
        align_axes=False, align_center_of_mass=True,
        translation_step=6, translation_range=[10, 10, 10],
        target_mask=None, moving_mask=None,
        initial_transform=None,
        base_dir=None, log_file=None,
        additional_env=None, keep_files=False
    ):
        ai_config_dict = {}
        spacing = resampling_factor * get_common_spacing(
            movings + targets
        )

        if base_dir is None:
            base_dir = getcwd()

        if log_file is None:
            log_file = join(base_dir, "ants_ai.log")

        with TemporaryDirectory(dir=base_dir) as prep_dir:

            if initial_transform is not None:
                c = "antsApplyTransforms -e 0 -d 3"
                _m = []
                for m in movings:
                    _n = basename(m)
                    launch_shell_process(
                        "{} -t {} -r {} -i {} -o {}".format(
                            c, initial_transform,
                            targets[0], m, 
                            join(prep_dir, "{}_init_transform.{}".format(
                                _n.split(".")[0],
                                ".".join(_n.split(".")[1:])
                            ))
                        ), log_file,
                        additional_env=additional_env
                    )
                    _m.append(join(prep_dir, "{}_init_transform.{}".format(
                        _n.split(".")[0],
                        ".".join(_n.split(".")[1:])
                    )))
                    movings = _m
                if moving_mask is not None:
                    _n = basename(moving_mask)
                    launch_shell_process(
                        "{} -t {} -r {} -i {} -o {}".format(
                            c, initial_transform,
                            targets[0], moving_mask,
                            join(prep_dir, "{}_init_transform.{}".format(
                                _n.split(".")[0],
                                ".".join(_n.split(".")[1:])
                            ))
                        ), log_file,
                        additional_env=additional_env
                    )
                    moving_mask = join(prep_dir, "{}_init_transform.{}".format(
                        _n.split(".")[0],
                        ".".join(_n.split(".")[1:])
                    ))

            for i, target in enumerate(targets):
                _, ext = split_ext(target, r"^(/?.*)\.(nii\.gz|nii)$")
                ai_config_dict["t{}".format(i)] = join(
                    base_dir, "ants_ai_target{}.{}".format(i, ext)
                )

                targets[i] = self._setup_ants_ai_input(
                    target, log_file,
                    mask_fname=target_mask,
                    spacing=spacing,
                    additional_env=additional_env,
                    base_dir=prep_dir
                )

            for i, moving in enumerate(movings):
                _, ext = split_ext(moving, r"^(/?.*)\.(nii\.gz|nii)$")
                ai_config_dict["m{}".format(i)] = join(
                    base_dir, "ants_ai_moving{}.{}".format(i, ext)
                )

                movings[i] = self._setup_ants_ai_input(
                    moving, log_file,
                    ref_fname=targets[min(i, len(targets) - 1)],
                    mask_fname=moving_mask,
                    spacing=spacing,
                    additional_env=additional_env,
                    base_dir=prep_dir
                )

            if align_center_of_mass:
                movings = align_by_center_of_mass(
                    targets[0], movings, join(prep_dir, "center_of_mass.mat"),
                    align_mask_fnames=[moving_mask] \
                        if moving_mask is not None else None,
                    suffix="cm", base_dir=prep_dir
                )

                if moving_mask is not None:
                    movings, moving_mask = movings[:-1], movings[-1]

            for i, target in enumerate(targets):
                _, ext = split_ext(target, r"^(/?.*)\.(nii\.gz|nii)$")
                copyfile(target, join(
                    base_dir, "ants_ai_target{}.{}".format(i, ext)
                ))

            for i, moving in enumerate(movings):
                _, ext = split_ext(moving, r"^(/?.*)\.(nii\.gz|nii)$")
                copyfile(moving, join(
                    base_dir, "ants_ai_moving{}.{}".format(i, ext)
                ))

            ai_init_params = ants_config.get_ants_ai_parameters(spacing)
            ai_init_params = ai_init_params.format(**ai_config_dict)
            ai_init_params += " -s [{},{}] -p {} -g [{},{}]".format(
                angular_step, angular_range / 180., int(align_axes),
                translation_step, "x".join(str(t) for t in translation_range)
            )
            ai_init_params += " --output {}".format(
                join(base_dir, "ants_ai_transform.mat")
            )
            ai_init_params += " --verbose {}".format(int(self.verbose))

            if target_mask:
                if moving_mask is None:
                    ai_init_params += "--masks {}".format(target_mask)
                else:
                    ai_init_params += " --masks [{},{}]".format(
                        target_mask, moving_mask
                    )

            cmd = []
            cmd.append("antsAI {}".format(ai_init_params))

            if align_center_of_mass:
                cmd.append("antsApplyTransforms -t {} -t {} -o {}".format(
                    join(base_dir, "ants_ai_transform.mat"),
                    join(prep_dir, "center_of_mass.mat"),
                    "Linear[{},0]".format(transform_fname)
                ))
            else:
                cmd.append("mv {} {}".format(
                    join(base_dir, "ants_ai_transform.mat"),
                    transform_fname
                ))

            for c in cmd:
                launch_shell_process(
                    c, log_file,
                    additional_env=additional_env
                )

            if keep_files:
                copytree(
                    prep_dir, join(base_dir, "prepare"), dirs_exist_ok=True
                )

    def execute(self):
        current_path = getcwd()
        max_spacing = np.max(
            nib.load(self.moving_images[0]).header.get_zooms()[:3]
        )

        additional_env = {}
        if self.configuration.seed is not None:
            additional_env["ANTS_RANDOM_SEED"] = self.configuration.seed

        config_dict = {}

        for i, target in enumerate(self.target_images):
            config_dict["t{}".format(i)] = target

        for i, moving in enumerate(self.moving_images):
            config_dict["m{}".format(i)] = moving

        target_mask, moving_mask, masks_param = None, None, ""
        if self.mask:
            if len(self.mask) == 1:
                target_mask = moving_mask = self.mask[0]
            else:
                target_mask, moving_mask = self.mask

            masks_param = " --masks [{},{}]".format(target_mask, moving_mask)

        if self.init_with_ants_ai and self.configuration.is_initializable():
            coarse_subpath = join(current_path, "coarse_init")
            makedirs(coarse_subpath, exist_ok=True)
            fine_subpath = join(current_path, "fine_init")
            makedirs(fine_subpath, exist_ok=True)

            log_file = join(current_path, "{}_initialization.log".format(
                basename(self.output_prefix)
            ))

            self._call_ants_ai(
                self.target_images.copy(), self.moving_images.copy(),
                self.configuration, "coarse_initializer.mat",
                angular_step=160. / self.configuration.coarse_angular_split,
                translation_step=16. / self.configuration.coarse_linear_split,
                target_mask=target_mask,
                moving_mask=moving_mask if moving_mask != target_mask else None,
                base_dir=coarse_subpath,
                log_file=log_file,
                additional_env=additional_env,
                keep_files=True
            )

            self._call_ants_ai(
                self.target_images.copy(), self.moving_images.copy(),
                self.configuration, "fine_initializer.mat",
                angular_step=45. / self.configuration.fine_angular_split,
                translation_range=3 * [self.configuration.fine_linear_split],
                angular_range=20, translation_step=1,
                align_center_of_mass=False,
                initial_transform="coarse_initializer.mat",
                target_mask=target_mask,
                moving_mask=moving_mask if moving_mask != target_mask else None,
                base_dir=fine_subpath,
                log_file=log_file,
                additional_env=additional_env,
                keep_files=True
            )

            merge_transforms(
                "init_transform.mat", log_file, 
                "coarse_initializer.mat", "fine_initializer.mat",
                additional_env=additional_env
            )

            self.configuration.set_initial_transform_from_ants_ai(
                "init_transform.mat"
            )

        ants_config_fmt = self.configuration.serialize(max_spacing, masks_param)
        ants_config_fmt = ants_config_fmt.format(**config_dict)

        if self.verbose:
            ants_config_fmt += " --verbose"

        ants_config_fmt += " --output [{},{}]".format(
            self.output_prefix, "{}_warped.nii.gz".format(self.output_prefix)
        )

        launch_shell_process(
            "antsRegistration {}".format(ants_config_fmt),
            join(current_path, "{}.log".format(basename(self.output_prefix))),
            additional_env=additional_env
        )

        metadata = load_metadata(self.moving_images[0])
        if metadata:
            save_metadata("{}_warped".format(self.output_prefix), metadata)


_tr_aliases = {
    'in': 'AntsTransform.image',
    'out': 'AntsTransform.output',
    'dtype': 'AntsTransform.out_type',
    'ref': 'AntsTransform.transformation_ref',
    'trans': 'AntsTransform.transformations',
    'inv': 'AntsTransform.invert',
    'bvecs': 'AntsTransform.bvecs'
}

_tr_description = """
Apply a transformation (rigid, affine, non-linear) precomputed via Ants to an 
image.
"""


class AntsTransform(mrHARDIBaseApplication):
    name = u"ANTs Transform"
    description = _tr_description
    configuration = Instance(AntsTransformConfiguration).tag(config=True)

    image = required_file(description="Input image to transform")

    bvecs = Unicode(
        help="List of b-vectors to realign following "
             "rigid and affine transformations."
    ).tag(config=True)

    transformation_ref = required_file(
        description="Reference image for initial rigid transformation."
    )

    transformations = MultipleArguments(
        Unicode(), help="List of transformations to "
                        "apply, following ANTs ordering."
    ).tag(config=True, ignore_write=True)

    invert = MultipleArguments(
        Unicode(), help="List of boolean indicating if a "
                        "transformation needs to be reversed"
    ).tag(config=True, ignore_write=True)

    out_type = Enum(
        ["char", "uchar", "short", "int", "float", "double"],
        None,
        allow_none=True,
        help="Output datatype for the transformed image"
    ).tag(config=True)

    output = output_prefix_argument()

    aliases = Dict(default_value=_tr_aliases)

    def execute(self):
        current_path = getcwd()

        image = nib.load(self.image)
        shape = image.shape

        if self.configuration.image_type is None:
            is_3d_data = not (len(shape) == 4 and shape[-1] > 1)
            img_type = 0 if is_3d_data else 3
        else:
            img_type = ImageType[self.configuration.image_type].value

        trans_type = img_type
        if trans_type == ImageType.RGB.value:
            trans_type = ImageType.VECTOR.value

        args = "-e {} -r {}".format(trans_type, self.transformation_ref)

        if self.out_type:
            args += " -u {}".format(self.out_type)
        else:
            out_type = "default"
            if np.issubdtype(image.header.get_data_dtype(), np.integer):
                if np.issubdtype(
                    image.header.get_data_dtype(), np.signedinteger):
                    out_type = "int"
                else:
                    if image.header.get_data_dtype().itemsize == 1:
                        out_type = "uchar"
                    else:
                        out_type = "int"
            elif np.issubdtype(image.header.get_data_dtype(), np.floating):
                if image.header.get_data_dtype().itemsize > 4:
                    out_type = "double"
                else:
                    out_type = "float"
            elif np.issubdtype(image.header.get_data_dtype(), np.character):
                out_type = "char"

            args += " -u {}".format(out_type)

        invert = []
        if self.transformations and len(self.transformations) > 0:
            if not self.invert or len(self.invert) == 0:
                invert = [False for _ in range(len(self.transformations))]
            elif len(self.transformations) == len(self.invert):
                invert = [i == "true" for i in self.invert]
            else:
                ArgumentError(
                    "Number of invert flags doesn't "
                    "match number of transformations"
                )

            args += "".join(
                " -t [{},{}]".format(t, int(i)) for t, i in zip(
                    self.transformations, invert
                )
            )

        command = "antsApplyTransforms {}".format(
            self.configuration.serialize()
        )
        if img_type == ImageType.RGB.value:
            with TemporaryDirectory(dir=current_path) as tmp_dir:
                data = (image.get_fdata() / 255.)[..., None, :]
                nib.save(
                    nib.Nifti1Image(data, image.affine, image.header),
                    join(tmp_dir, "rgb_vec.nii.gz")
                )

                launch_shell_process(
                    "{} {} -i {} -o {}".format(
                        command, args,
                        join(tmp_dir, "rgb_vec.nii.gz"),
                        join(tmp_dir, "rgb_vec_trans.nii.gz")
                    ),
                    join(tmp_dir, "rgb_vec_trans.log")
                )

                output = nib.load(join(tmp_dir, "rgb_vec_trans.nii.gz"))
                nib.save(
                    nib.Nifti1Image(
                        output.get_fdata().squeeze() * 255.,
                        output.affine, output.header
                    ),
                    "{}.nii.gz".format(self.output)
                )
        elif (img_type == ImageType.SCALAR.value
              and len(shape) > 3 and shape[-1] > 1):
            with TemporaryDirectory(dir=current_path) as tmp_dir:
                data = image.get_fdata().reshape(shape[:3] + (-1,))

                for i in range(data.shape[-1]):
                    nib.save(
                        nib.Nifti1Image(
                            data[..., i], image.affine, image.header
                        ),
                        join(tmp_dir, "v{}.nii.gz".format(i))
                    )
                    launch_shell_process(
                        "{} {} -i {} -o {}".format(
                            command, args,
                            join(tmp_dir, "v{}.nii.gz".format(i)),
                            join(tmp_dir, "v{}_trans.nii.gz".format(i))
                        ),
                        join(tmp_dir, "v{}_trans.log".format(i))
                    )

                base_output = nib.load(
                    join(tmp_dir, "v0_trans.nii.gz")
                )
                out_data = base_output.get_fdata()[..., None]
                for i in range(1, data.shape[-1]):
                    other_data = nib.load(
                        join(tmp_dir, "v{}_trans.nii.gz".format(i))
                    ).get_fdata()[..., None]
                    out_data = np.concatenate((out_data, other_data), axis=-1)

                nib.save(
                    nib.Nifti1Image(
                        out_data.reshape(out_data.shape[:3] + shape[3:]),
                        base_output.affine, image.header
                    ),
                    "{}.nii.gz".format(self.output)
                )
        elif img_type == ImageType.VECTOR.value and len(shape) == 4:
            with TemporaryDirectory(dir=current_path) as tmp_dir:
                data = image.get_fdata()
                header = image.header.copy()
                header.set_intent('vector')

                if shape[-1] == 15:
                    for i in range(5):
                        nib.save(
                            nib.Nifti1Image(
                                data[..., None, (3 * i):(3 * (i + 1))],
                                image.affine, header
                            ),
                            join(tmp_dir, "v{}.nii.gz".format(i))
                        )
                        launch_shell_process(
                            "{} {} -i {} -o {}".format(
                                command, args,
                                join(tmp_dir, "v{}.nii.gz".format(i)),
                                join(tmp_dir, "v{}_trans.nii.gz".format(i))
                            ),
                            join(tmp_dir, "v{}_trans.log".format(i))
                        )

                    base_output = nib.load(join(tmp_dir, "v0_trans.nii.gz"))
                    data = base_output.get_fdata()
                    for i in range(1, 5):
                        other_data = nib.load(
                            join(tmp_dir, "v{}_trans.nii.gz".format(i))
                        ).get_fdata()
                        data = np.concatenate((data, other_data), axis=-1)
                else:
                    nib.save(
                        nib.Nifti1Image(
                            data[..., None, :], image.affine, header
                        ),
                        join(tmp_dir, "vectors.nii.gz")
                    )
                    launch_shell_process(
                        "{} {} -i {} -o {}".format(
                            command, args,
                            join(tmp_dir, "vectors.nii.gz"),
                            join(tmp_dir, "v_trans.nii.gz")
                        ),
                        join(tmp_dir, "v_trans.log")
                    )

                    base_output = nib.load(join(tmp_dir, "v_trans.nii.gz"))
                    data = base_output.get_fdata()

                nib.save(
                    nib.Nifti1Image(
                        data.squeeze(), base_output.affine, image.header
                    ),
                    "{}.nii.gz".format(self.output)
                )
        elif img_type == ImageType.TENSOR.value and len(shape) == 4:
            with TemporaryDirectory(dir=current_path) as tmp_dir:
                data = image.get_fdata()[..., None, (0, 1, 3, 2, 4, 5)]
                header = image.header.copy()
                zooms = header.get_zooms()
                header.set_zooms(zooms[:3] + (0.,))
                header.set_intent("symmetric matrix")
                nib.save(
                    nib.Nifti1Image(data, image.affine, header),
                    join(tmp_dir, "tensor.nii.gz")
                )

                launch_shell_process(
                    "{} {} -i {} -o {}".format(
                        command, args,
                        join(tmp_dir, "tensor.nii.gz"),
                        join(tmp_dir, "tensor_trans.nii.gz")
                    ),
                    join(tmp_dir, "tensor_trans.log")
                )

                output = nib.load(join(tmp_dir, "tensor_trans.nii.gz"))
                data = output.get_fdata().squeeze()[..., (0, 1, 3, 2, 4, 5)]
                nib.save(
                    nib.Nifti1Image(data, output.affine, output.header),
                    "{}.nii.gz".format(self.output)
                )
        elif img_type == ImageType.TIMESERIES.value and len(shape) == 4:
            with TemporaryDirectory(dir=current_path) as tmp_dir:
                data = image.get_fdata().astype(image.header.get_data_dtype())

                for i in range(data.shape[-1]):
                    nib.save(
                        nib.Nifti1Image(
                            data[..., i], image.affine, image.header
                        ),
                        join(tmp_dir, "v{}.nii.gz".format(i))
                    )
                    launch_shell_process(
                        "{} {} -i {} -o {}".format(
                            command, args,
                            join(tmp_dir, "v{}.nii.gz".format(i)),
                            join(tmp_dir, "v{}_trans.nii.gz".format(i))
                        ),
                        join(tmp_dir, "v{}_trans.log".format(i))
                    )

                base_output = nib.load(
                    join(tmp_dir, "v0_trans.nii.gz")
                )
                out_data = base_output.get_fdata()[..., None]
                for i in range(1, data.shape[-1]):
                    other_data = nib.load(
                        join(tmp_dir, "v{}_trans.nii.gz".format(i))
                    ).get_fdata()[..., None]
                    out_data = np.concatenate((out_data, other_data), axis=-1)

                nib.save(
                    nib.Nifti1Image(
                        out_data.reshape(out_data.shape[:3] + shape[3:]),
                        base_output.affine, image.header
                    ),
                    "{}.nii.gz".format(self.output)
                )
        else:
            command += " {} -i {} -o {}".format(
                args, self.image, "{}.nii.gz".format(self.output)
            )

            launch_shell_process(command, join(current_path, "{}.log".format(
                basename(self.output)
            )))

        metadata = load_metadata(self.image)
        if metadata:
            save_metadata(self.output, metadata)

        if self.bvecs:
            ref = nib.load(self.transformation_ref)
            ref_ornt = nib.io_orientation(ref.affine)
            bvecs = np.loadtxt(self.bvecs)

            for trans, inv in zip(self.transformations[::-1], invert[::-1]):
                if trans.split(".")[-1] == "mat":
                    self.log.debug(
                        "Rotating bvecs with {} : {} (in {})".format(
                            "inverse_transform" if inv else "transform",
                            basename(trans),
                            dirname(trans)
                        )
                    )
                    rot = load_transform(trans, ref_ornt)[:3, :3]
                    if inv:
                        rot = np.linalg.inv(rot)

                    bvecs = rot @ bvecs

            np.savetxt("{}.bvec".format(self.output), bvecs)


_motion_description = """
Perform motion correction (registration) of timeseries over templates using 
Ants [1]. The stages of registration are the same as antsRegistration, except 
there isn't a specification of convergence. The algorithm will thus run the 
total number of iterations specified for each stage before going to the next. 
An example of execution can be found at [2] or [3].

References :
------------
[1] http://stnava.github.io/ANTs/
[2] https://github.com/ANTsX/ANTs/blob/master/Scripts/antsMotionCorrExample
[3] https://stnava.github.io/fMRIANTs/
"""

_mot_aliases = {
    'target': 'AntsMotionCorrection.target_images',
    'moving': 'AntsMotionCorrection.moving_images',
    'out': 'AntsMotionCorrection.output_prefix'
}

_mot_flags = dict(
    verbose=(
        {"AntsMotionCorrection": {'verbose': True}},
        "Enables verbose output"
    )
)


class AntsMotionCorrection(mrHARDIBaseApplication):
    name = u"ANTs Motion Correction"
    description = _motion_description
    configuration = Instance(AntsMotionCorrectionConfiguration).tag(
        config=True
    )

    target_images = required_arg(
        MultipleArguments, traits_args=(Unicode(),),
        description="List of target images (2D or 3D) used in the passes of "
                    "registration. Those must equal the number of metric "
                    "evaluations of the resulting output command"
    )

    moving_images = required_arg(
        MultipleArguments, traits_args=(Unicode(),),
        description="List of moving images (must be 3D or 4D timeseries) used "
                    "in the passes of registration. Those must equal the "
                    "number of metric evaluations of the resulting output "
                    "command"
    )

    output_prefix = output_prefix_argument()

    verbose = Bool(False).tag(config=True)

    aliases = Dict(default_value=_mot_aliases)
    flags = Dict(default_value=_mot_flags)

    def _generate_config_file(self, filename):
        self.configuration.passes = [
            AntsRigid(
                is_motion_correction=True,
                name_dict={
                    "smooth": "smoothingSigmas",
                    "shrink": "shrinkFactors"
                }
            ),
            AntsAffine(
                is_motion_correction=True,
                name_dict={
                    "smooth": "smoothingSigmas",
                    "shrink": "shrinkFactors"
                }
            )
        ]
        super()._generate_config_file(filename)

    def execute(self):
        current_path = getcwd()

        max_spacing = np.max(
            nib.load(self.moving_images[0]).header.get_zooms()[:3]
        )

        ants_config_fmt = self.configuration.serialize(max_spacing)
        config_dict = {}

        for i, (target, moving) in enumerate(zip(
                self.target_images, self.moving_images
        )):
            config_dict["t{}".format(i)] = target
            config_dict["m{}".format(i)] = moving

        ants_config_fmt = ants_config_fmt.format(**config_dict)

        ants_config_fmt += " --output [{},{}]".format(
            self.output_prefix, "{}_warped.nii.gz".format(self.output_prefix)
        )

        if self.verbose:
            ants_config_fmt += " --verbose"

        launch_shell_process(
            "antsMotionCorr {}".format(ants_config_fmt),
            join(current_path, "{}.log".format(
                basename(self.output_prefix)
            ))
        )

        metadata = load_metadata(self.moving_images[0])
        if metadata:
            save_metadata("{}_warped".format(self.output_prefix), metadata)


_compose_aliases = {
    'in': 'ComposeANTsTransformations.fwd_transforms',
    'inv': 'ComposeANTsTransformations.inv_transforms',
    'fwd-inv': 'ComposeANTsTransformations.fwd_inverts',
    'inv-inv': 'ComposeANTsTransformations.inv_inverts',
    'ref': 'ComposeANTsTransformations.target_ref',
    'src': 'ComposeANTsTransformations.source_ref',
    'fwd_suffix': 'ComposeANTsTransformations.fwd_suffix',
    'inv_suffix': 'ComposeANTsTransformations.inv_suffix',
    'out': 'ComposeANTsTransformations.output',
    'ext': 'ComposeANTsTransformations.extension',
    'save_script_transforms': 'ComposeANTsTransformations.script_trans_dir'
}

_compose_flags = dict(
    image_transformations=(
        {"ComposeANTsTransformations": {'produce_img_transforms': True}},
        "Produce forward and inverse transforms for images"
    ),
    tractogram_transformations=(
        {"ComposeANTsTransformations": {'produce_tract_transforms': True}},
        "Produce forward and inverse transforms for tractograms"
    ),
    generate_scripts=(
        {"ComposeANTsTransformations": {'produce_transform_scripts': True}},
        "Produce scripts to help apply the non-composed transforms"
    )
)


class ComposeANTsTransformations(mrHARDIBaseApplication):
    name = u"Compose ANTs Transformations"
    description = "Compose a list of ANTs transformations into transforms " \
                  "stacks to apply on images and/or on tractograms"

    output = output_prefix_argument()

    fwd_transforms = required_arg(
        MultipleArguments, traits_args=(Unicode(),),
        description="List of transformations to compose"
    )

    inv_transforms = required_arg(
        MultipleArguments, traits_args=(Unicode(),),
        description="List of inverse transformations to compose. "
                    "Must be supplied in inverse order of fwd_transforms"
    )

    fwd_inverts = MultipleArguments(
        Bool(), help="List of boolean indicating if a forward"
                     "transformation needs to be inverted"
    ).tag(config=True)

    inv_inverts = MultipleArguments(
        Bool(), help="List of boolean indicating if an inverse"
                     "transformation needs to be inverted"
    ).tag(config=True)

    source_ref = required_file(
        description="Reference image for the source image"
    )

    target_ref = required_file(
        description="Reference image for the target image"
    )

    fwd_suffix = Unicode(
        "fwd", help="Suffix to append to the forward transformation"
    ).tag(config=True)
    inv_suffix = Unicode(
        "inv", help="Suffix to append to the inverse transformation"
    ).tag(config=True)

    extension = Enum(
        [".nii.gz", ".h5"], ".nii.gz",
        help="File type for the composite transformations"
    ).tag(config=True)

    script_trans_dir = Unicode(
        None, allow_none=True,
        help="Directory where to store the non-composed transforms "
             "used by the automatically generated scripts"
    ).tag(config=True)

    produce_img_transforms = Bool(
        False, help="Produce forward and inverse transforms for images"
    ).tag(config=True)
    produce_tract_transforms = Bool(
        False, help="Produce forward and inverse transforms for tractograms"
    ).tag(config=True)
    produce_transform_scripts = Bool(
        False, help="Produce scripts to help apply the non-composed transforms"
    ).tag(config=True)

    aliases = Dict(default_value=_compose_aliases)
    flags = Dict(default_value=_compose_flags)

    def _create_transformation_script(
        self, ref, trans, inv_trans, inverts, out_name, tractogram_transform=False
    ):
        def _is_affine(_f):
                return _f.split(".")[-1] in ["mat", "txt"]

        _trans, _inv = [], []
        if tractogram_transform:
            inverts = [not i for i in inverts]

        for _t, _i, _it in zip(trans, inverts, inv_trans):
            if not _is_affine(_t) and _i:
                _trans.append(_it)
                _inv.append(False)
            else:
                _trans.append(_t)
                _inv.append(_i)

        script = create_ants_transform_script(ref, _trans, _inv)
        with open(out_name, "w") as f:
            f.write(script)

    def execute(self):
        current_dir = getcwd()
        commands = []

        def _transforms_fmt(_t, _it, _i):
            def _is_affine(_f):
                return _f.split(".")[-1] in ["mat", "txt"]
            return " ".join(["{}{}".format(
                "-i " if _inv and _is_affine(_tr) else "",
                _itr if _inv and not _is_affine(_tr) else _tr
            ) for _inv, _tr, _itr in zip(_i, _t, _it)])

        composer_fmt = "ComposeMultiTransform 3 {out} -R {ref} {transforms}"

        fwd_trans, inv_trans = self.fwd_transforms, self.inv_transforms
        fwd_inv, inv_inv = self.fwd_inverts, self.inv_inverts

        if self.script_trans_dir is not None:
            makedirs(self.script_trans_dir, exist_ok=True)
            _t, _it = [], []
            for t in fwd_trans:
                _t.append(join(self.script_trans_dir, basename(t)))
                copyfile(t, _t[-1])
            for t in inv_trans:
                _it.append(join(self.script_trans_dir, basename(t)))
                copyfile(t, _it[-1])

            fwd_trans, inv_trans = _t, _it

        if self.produce_img_transforms:
            commands.append(
                composer_fmt.format(
                    out="{}_image_transform_{}{}".format(
                        self.output, self.fwd_suffix, self.extension
                    ),
                    ref=self.target_ref,
                    transforms=_transforms_fmt(
                        fwd_trans, inv_trans[::-1], fwd_inv
                    )
                )
            )
            commands.append(
                composer_fmt.format(
                    out="{}_image_transform_{}{}".format(
                        self.output, self.inv_suffix, self.extension
                    ),
                    ref=self.source_ref,
                    transforms=_transforms_fmt(
                        inv_trans, fwd_trans[::-1], inv_inv
                    )
                )
            )

        if self.produce_tract_transforms:
            commands.append(
                composer_fmt.format(
                    out="{}_tractogram_transform_{}{}".format(
                        self.output, self.fwd_suffix, self.extension
                    ),
                    ref=self.target_ref,
                    transforms=_transforms_fmt(
                        inv_trans, fwd_trans[::-1], [not i for i in inv_inv]
                    )
                )
            )
            commands.append(
                composer_fmt.format(
                    out="{}_tractogram_transform_{}{}".format(
                        self.output, self.inv_suffix, self.extension
                    ),
                    ref=self.source_ref,
                    transforms=_transforms_fmt(
                        fwd_trans, inv_trans[::-1], [not i for i in fwd_inv]
                    )
                )
            )

        if self.produce_transform_scripts:
            self._create_transformation_script(
                self.target_ref, fwd_trans, inv_trans, fwd_inv,
                "{}_fwd_image_transform.sh".format(self.output)
            )
            self._create_transformation_script(
                self.source_ref, inv_trans, fwd_trans, inv_inv,
                "{}_inv_image_transform.sh".format(self.output)
            )
            self._create_transformation_script(
                self.target_ref, inv_trans, fwd_trans, inv_inv,
                "{}_inv_tractogram_transform.sh".format(self.output),
                tractogram_transform=True
            )
            self._create_transformation_script(
                self.source_ref, fwd_trans, inv_trans, fwd_inv,
                "{}_fwd_tractogram_transform.sh".format(self.output),
                tractogram_transform=True
            )

        for c in commands:
            launch_shell_process(
                c,
                join(current_dir, "{}.log".format(
                    basename(self.output)
                ))
            )
