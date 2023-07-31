from os import getcwd, makedirs
from os.path import basename, join
from tempfile import TemporaryDirectory

import nibabel as nib
import numpy as np
from scipy.io import loadmat
from scipy.spatial.transform import Rotation
from traitlets import Dict, Instance, Unicode, Bool, Enum
from traitlets.config.loader import ArgumentError

import nibabel as nib

from mrHARDI.base.application import (mrHARDIBaseApplication,
                                      MultipleArguments,
                                      output_prefix_argument,
                                      required_arg,
                                      required_file)
from mrHARDI.base.dwi import load_metadata, save_metadata
from mrHARDI.base.shell import launch_shell_process
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

    def _get_common_spacing(self, img_list):
        spacing = []
        for img in img_list:
            _img = nib.load(img)
            spacing.append(min(_img.header.get_zooms()[:3]))

        return min(spacing)

    def _setup_ants_ai_input(
        self, image_fname, cwd,
        mask_fname=None, env=None, ref_fname=None, spacing=None
    ):
        ext = ".".join(image_fname.split(".")[1:])
        name = image_fname.split(".")[0]

        image = nib.load(image_fname)

        if spacing is None:
            spacing = 2.5 * min(image.header.get_zooms()[:3])

        if mask_fname:
            mask = nib.load(mask_fname).get_fdata().astype(bool)
            data = image.get_fdata()
            data[~mask] = 0.
            nib.save(
                nib.Nifti1Image(
                    data, image.affine, image.header
                ),
                "init_transform/{}_masked.{}".format(name, ext)
            )
            image_fname = "init_transform/{}_masked.{}".format(name, ext)

        cmd = [
            "scil_crop_volume.py {} {} --output_bbox {} -f".format(
                image_fname,
                "init_transform/{}_cropped.{}".format(name, ext),
                "init_transform/{}_bbox.pkl".format(name)
            )
        ]
        image_fname = "init_transform/{}_cropped.{}".format(name, ext)

        if mask_fname:
            cmd.append("scil_crop_volume.py {} {} --input_bbox {} -f".format(
                mask_fname,
                "init_transform/{}_mask_cropped.{}".format(name, ext),
                "init_transform/{}_bbox.pkl".format(name)
            ))
            mask_fname = "init_transform/{}_mask_cropped.{}".format(name, ext)

        if ref_fname and self.configuration.match_histogram:
            cmd.append("ImageMath 3 {} HistogramMatch {} {}".format(
                "init_transform/{}_hmatch.{}".format(name, ext),
                image_fname,
                ref_fname
            ))
            image_fname = "init_transform/{}_hmatch.{}".format(name, ext)

        cmd.append("ResampleImageBySpacing 3 {} {} {} {} {} 1".format(
            image_fname,
            "init_transform/{}_res.{}".format(name, ext),
            spacing, spacing, spacing
        ))

        for c in cmd:
            launch_shell_process(
                c,
                join(cwd, "{}.log".format(
                    "{}_init_transform".format(basename(self.output_prefix))
                )),
                additional_env=env
            )

    def execute(self):
        current_path = getcwd()

        max_spacing = np.max(
            nib.load(self.moving_images[0]).header.get_zooms()[:3]
        )

        additional_env = {}
        if self.configuration.seed is not None:
            additional_env["ANTS_RANDOM_SEED"] = self.configuration.seed

        config_dict, ai_config_dict = {}, {}

        for i, target in enumerate(self.target_images):
            ext = ".".join(target.split(".")[1:])
            name = target.split(".")[0]
            config_dict["t{}".format(i)] = target
            ai_config_dict["t{}".format(i)] = "init_transform/{}_res.{}".format(
                name, ext
            )

        for i, moving in enumerate(self.moving_images):
            ext = ".".join(moving.split(".")[1:])
            name = moving.split(".")[0]
            config_dict["m{}".format(i)] = moving
            ai_config_dict["m{}".format(i)] = \
                "init_transform/{}_origin.{}".format(
                    name, ext
                )

        target_mask, moving_mask, masks_param = None, None, ""
        if self.mask:
            if len(self.mask) == 1:
                target_mask = moving_mask = self.mask
            else:
                target_mask, moving_mask = self.mask

            masks_param = " --masks [{},{}]".format(target_mask, moving_mask)

        if self.init_with_ants_ai and self.configuration.is_initializable():
            ai_subpath = join(current_path, "init_transform")
            ai_init_params = self.configuration.get_ants_ai_parameters(
                max_spacing
            )
            ai_init_params = ai_init_params.format(**ai_config_dict)
            ai_init_params += " -s [20,0.04]"

            if self.mask:
                ai_init_params += masks_param

            output_tranform = "{}/init_transform.mat".format(ai_subpath)
            ai_init_params += " -g [5,10x10x20] -p 0 --output {}".format(
                output_tranform
            )

            if self.verbose:
                ai_init_params += " --verbose 1"

            makedirs(ai_subpath, exist_ok=True)
            spacing = 2.5 * self._get_common_spacing(
                self.moving_images + self.target_images
            )

            for i, target in enumerate(self.target_images):
                self._setup_ants_ai_input(
                    target, current_path, target_mask, additional_env,
                    spacing=spacing
                )

            cmd, spacing = [], self._get_common_spacing(self.moving_images)
            for i, moving in enumerate(self.moving_images):
                self._setup_ants_ai_input(
                    moving,
                    current_path,
                    moving_mask,
                    additional_env,
                    self.target_images[min(i, len(self.target_images) - 1)],
                    spacing=spacing
                )

            ext = ".".join(self.moving_images[0].split(".")[1:])
            name = self.moving_images[0].split(".")[0]
            text = ".".join(self.target_images[0].split(".")[1:])
            tname = self.target_images[0].split(".")[0]
            cmd.append("antsAlignOrigin -d 3 -o {} -i {} -r {}".format(
                "init_transform/origin.mat",
                "init_transform/{}_res.{}".format(name, ext),
                "init_transform/{}_res.{}".format(tname, text)
            ))

            for i, moving in enumerate(self.moving_images):
                ext = ".".join(moving.split(".")[1:])
                name = moving.split(".")[0]
                cmd.append(
                    "antsApplyTransforms -d 3 -e 0 -n Linear "
                    "-t {} -i {} -r {} -o {}".format(
                        "init_transform/origin.mat",
                        moving,
                        self.target_images[0],
                        "init_transform/{}_origin.{}".format(name, ext)
                ))

            cmd.append("antsAI {}".format(ai_init_params))
            cmd.append(
                "cp init_transform/init_transform.mat "
                "init_transform/init_transform.mat.bak"
            )
            cmd.append("antsApplyTransforms -t {} -t {} -o {}".format(
                "init_transform/init_transform.mat",
                "init_transform/origin.mat",
                "Linear[init_transform/init_transform.mat,1]"
            ))

            for c in cmd:
                launch_shell_process(
                    c,
                    join(current_path, "{}.log".format(
                        "{}_init_transform".format(basename(self.output_prefix))
                    )),
                    additional_env=additional_env
                )

            self.configuration.set_initial_transform_from_ants_ai(
                output_tranform
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
            join(current_path, "{}.log".format(
                basename(self.output_prefix)
            )),
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

    def _get_mat_rotation(self, filename):
        # TODO: check center of rotation for all transforms 
        # and order of rotation for Euler 3D 
        mat = loadmat(filename)
        if "AffineTransform_double_3_3" in mat:
            arr = mat["AffineTransform_double_3_3"]
        elif "AffineTransform_float_3_3" in mat:
            arr = mat["AffineTransform_float_3_3"]
        elif "Euler3DTransform_double_3_3" in mat:
            arr = Rotation.from_euler(
                'zyx', mat["Euler3DTransform_double_3_3"][:3].flatten()
            ).as_matrix().flatten()
        elif "Euler3DTransform_float_3_3" in mat:
            arr = Rotation.from_euler(
                'zyx', mat["Euler3DTransform_float_3_3"][:3].flatten()
            ).as_matrix().flatten()
        else:
            print("Could not load rotation matrix from : {}".format(filename))
            return np.eye(3)

        return arr[:9].reshape((3, 3))

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
            bvecs = np.loadtxt(self.bvecs)
            bvecs = np.linalg.inv(image.affine[:3, :3]) @ bvecs

            for trans in self.transformations[::-1]:
                if trans.split(".")[-1] == "mat":
                    self.log.debug(
                        "Rotating bvecs with respect to transform {}".format(
                            basename(trans)
                        )
                    )
                    bvecs = self._get_mat_rotation(trans) @ bvecs

            ref = nib.load(self.transformation_ref)
            bvecs = ref.affine[:3, :3] @ bvecs

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
