from os import chmod, getcwd
from os.path import join, basename
from shutil import copyfile

import nibabel as nib
import numpy as np
from traitlets import Dict, Instance, Unicode, Enum, Bool
from traitlets.config.loader import ConfigError

from mrHARDI.base.application import (mrHARDIBaseApplication,
                                           MultipleArguments,
                                           output_prefix_argument,
                                           required_arg, required_file)
from mrHARDI.base.fsl import prepare_acqp_file, prepare_topup_index
from mrHARDI.base.dwi import load_metadata, save_metadata
from mrHARDI.base.shell import launch_shell_process
from mrHARDI.config.epi import (TopupConfiguration,
                                BlockMatchingEPIConfiguration)

_aliases = dict(
    b0s='BaseEpiCorrectionApplication.b0_volumes',
    extra='BaseEpiCorrectionApplication.extra_arguments',
    out='BaseEpiCorrectionApplication.output_prefix',
    bvals='BaseEpiCorrectionApplication.bvals',
    rev_bvals='BaseEpiCorrectionApplication.rev_bvals'
)

_flags = dict(
    verbose=(
        {"BaseEpiCorrectionApplication": {'verbose': True}},
        "activate verbose information output"
    )
)

_description = """
Command-line utility used to parametrize and create scripts performing epi 
correction on b0 volumes, using either Topup or Block Matching. For more 
information on the parameters available for the executables, please refer to 
[1] for Topup and [2] for Block Matching.

References :
------------
[1] https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/topup
[2] https://anima.readthedocs.io/en/latest/registration.html#susceptibility-distortion-correction
[Andersson 2003] J.L.R. Andersson, S. Skare, J. Ashburner. How to correct 
                 susceptibility distortions in spin-echo echo-planar images: 
                 application to diffusion tensor imaging. NeuroImage, 
                 20(2):870-888, 2003.
[Hedouin 2017] R. Hedouin, O. Commowick, E. Bannier, B. Scherrer, M. Taquet, 
               S.K. Warfield, C. Barillot. Block-Matching Distortion Correction 
               of Echo-Planar Images With Opposite Phase Encoding Directions. 
               IEEE Trans Med Imaging, 36(5):1106-1115, 2017.
"""


class BaseEpiCorrectionApplication(mrHARDIBaseApplication):
    name = u"EPI Correction"
    description = _description

    b0_volumes = required_file(
        description="Input b0 volumes to feed to Topup, with "
                    "reverse acquisitions inside the volume"
    )

    bvals = required_arg(
        MultipleArguments, [],
        "B-values of the volumes used for Topup correction",
        traits_args=(Unicode(),)
    )

    rev_bvals = MultipleArguments(
        Unicode(), [],
        help="B-values for the reverse acquisitions used for deformation "
             "correction, will be paired with same index b-values from the "
             "bvals argument. Acquisition direction will be determined "
             "inverting the related dataset one if none is supplied."
    ).tag(config=True, ignore_write=True)

    output_prefix = output_prefix_argument()

    extra_arguments = Unicode(
        u'',
        help="Extra arguments to pass to topup, "
             "as a string, will be passed directly"
    ).tag(config=True)

    indexing_strategy = Enum(
        ["closest", "first"], "first",
        help="Strategy used to find which line in the .acqp aligns "
             "with which volume in the supplied dwi volume. For datasets "
             "with evenly spaced b0, \"closest\" will give the best result. "
             "In any other cases, or if you don't know, use \"first\""
    )

    verbose = Bool().tag(config=True)

    aliases = Dict(default_value=_aliases)
    flags = Dict(default_value=_flags)

    def _generate_index_acqp(self, metadata):
        acqp = prepare_acqp_file(
            metadata.readout, metadata.directions
        )

        kwargs = dict(b0_comp=np.less) if self.configuration.strict else dict()

        bvals = [np.loadtxt(bvs, ndmin=1) for bvs in self.bvals]
        rev_bvals = [np.loadtxt(bvs, ndmin=1) for bvs in self.rev_bvals]
        if rev_bvals:
            bvals = [bv for bv in bvals + rev_bvals]

        indexes = prepare_topup_index(
            np.concatenate(bvals), 1, strategy=self.indexing_strategy,
            ceil=self.configuration.ceil_value, **kwargs
        )

        if indexes.max() > len(acqp.split("\n")):
            if len(acqp.split("\n")) == 1:
                indexes[:] = 1
            elif not len(acqp.split("\n")) == len(bvals):
                raise ConfigError(
                    "No matching configuration found for index "
                    "(maxing at {}) "
                    "and acqp file (containing {} lines)\n{}".format(
                        indexes.max(), len(acqp), acqp
                    )
                )
            else:
                indexes[:len(bvals[0])] = 1
                used_indexes = len(bvals[0])
                for i, bv in enumerate(bvals[1:]):
                    indexes[used_indexes:used_indexes + len(bv)] = i + 2
                    used_indexes += len(bv)

        metadata.topup_indexes = np.unique(indexes).tolist()

        used_indexes = 0
        for i, bvals in enumerate(self.bvals + self.rev_bvals):
            mt = load_metadata(bvals)
            mt.topup_indexes = [int(indexes[used_indexes])]
            save_metadata(
                "{}_topup_indexes".format(bvals.split(".")[0]), mt
            )
            used_indexes += mt.n

        with open("{}_acqp.txt".format(self.output_prefix), 'w+') as f:
            f.write(acqp)


class TopupCorrection(BaseEpiCorrectionApplication):
    configuration = Instance(TopupConfiguration).tag(config=True)

    def execute(self):
        metadata = load_metadata(self.b0_volumes)
        self._generate_index_acqp(metadata)

        with open("{}_config.cnf".format(self.output_prefix), 'w+') as f:
            max_spacing = np.max(
                nib.load(self.b0_volumes).header.get_zooms()[:3]
            )
            f.write(self.configuration.serialize(max_spacing))

        if self.verbose:
            if self.extra_arguments:
                self.extra_arguments += " --verbose"
            else:
                self.extra_arguments = "--verbose"

        with open("{}_script.sh".format(self.output_prefix), 'w+') as f:
            f.write("#!/usr/bin/env bash\n\n")
            f.write("# mrHARDI -------------------------\n")
            f.write("# Autogenerated Topup script\n\n")

            f.write("in_b0=$1\n")
            f.write("out_prefix=$2\n")
            f.write("echo \"Running topup on $in_b0\\n\"\n")
            f.write(
                "topup --imain=\"$in_b0\" --datain={1} --config={2} "
                "--out=\"{0}{3}\" --fout=\"{0}{4}\" "
                "--iout=\"{0}{5}\" {6}\n".format(
                    "${out_prefix}",
                    "{}_acqp.txt".format(self.output_prefix),
                    "{}_config.cnf".format(self.output_prefix),
                    "_results", "_field.nii.gz", ".nii.gz",
                    self.extra_arguments
                ))

        chmod("{}_script.sh".format(self.output_prefix), 0o0777)

        save_metadata(self.output_prefix, metadata)

        return super().execute()


class BMEpiCorrection(BaseEpiCorrectionApplication):
    configuration = Instance(BlockMatchingEPIConfiguration).tag(config=True)

    def execute(self):
        img = nib.load(self.b0_volumes)
        if img.shape[-1] > 2:
            raise ConfigError(
                "BMEpi only supports 1 forward and 1 reverse b0 "
                "volume. You supplied a total of {} volumes".format(
                    img.shape[-1]
                )
            )

        metadata = load_metadata(self.b0_volumes)

        phase_encode_directions = metadata.get_directions()
        if len(np.unique(np.absolute(phase_encode_directions), axis=0)) > 1:
            raise ConfigError(
                "BMEpi can only be applied on 1 set of phase "
                "encoding directions align in either x, y or z"
            )

        self._generate_index_acqp(metadata)

        with open("{}_movpar.txt", "w+") as f:
            f.write("0 0 0 0 0 0\n")
            f.write("0 0 0 0 0 0")

        phase_encode_direction = np.argmax(phase_encode_directions[0])
        phase_encode_sign = np.sign(phase_encode_directions[0, phase_encode_direction])
        phase_encode_sign = "-" if phase_encode_sign < 0 else ""
        readout = metadata.readout
        knot_spacing = 4. * np.max(img.header.get_zooms()[:3])
        with open("{}_script.sh".format(self.output_prefix), 'w+') as f:
            f.write("#!/usr/bin/env bash\n\n")
            f.write("# mrHARDI -------------------------\n")
            f.write("# Autogenerated BMEpi script\n\n")
            f.write("in_b0=$1\n")
            f.write("in_rev=$2\n")
            f.write("out_prefix=$3\n")
            f.write("n_threads=$4\n")
            f.write("echo \"Running BMEpi on $in_b0 and $in_rev\\n\"\n")

            init_trans_arg = ""
            if self.configuration.initialize_bm:
                init_trans_arg = "-i ${out_prefix}_init_field.nii.gz"
                f.write(
                    "animaDistortionCorrection -f $in_b0 -b $in_rev "
                    "-d {0} -T $n_threads -s {1} -o {2}{3}\n".format(
                        phase_encode_direction,
                        self.configuration.smoothing_sigma,
                        "${out_prefix}",
                        "_init_field.nii.gz"
                    )
                )

            f.write(
                "animaBMDistortionCorrection -f $in_b0 -b $in_rev "
                "-d {0} -T $n_threads -o {1}{2} -O {1}{3} {4} {5}\n".format(
                    phase_encode_direction,
                    "${out_prefix}",
                    "_bm_corrected.nii.gz",
                    "_bm_field.nii.gz",
                    self.configuration.serialize(),
                    init_trans_arg
                )
            )

            f.write(
                "mrhardi disp_to_fmap --in {0}{1} --readout {2} "
                "--pe {3} --out {0}{4}".format(
                    "${out_prefix}",
                    "_bm_field.nii.gz",
                    readout,
                    ["i", "j", "k"][phase_encode_direction] + phase_encode_sign,
                    "_bm_fieldmap.nii.gz"
                )
            )

            #f.write(
            #    "mrhardi bspline_coeff --in {0}{1} "
            #    "--spacing {2} --out {0}{3}".format(
            #        "${out_prefix}",
            #        "_bm_field.nii.gz",
            #        knot_spacing,
            #        "_bm_fieldcoef.nii.gz"
            #    )
            #)

        chmod("{}_script.sh".format(self.output_prefix), 0o0777)

        save_metadata(self.output_prefix, metadata)

        return super().execute()

class EpiCorrection(mrHARDIBaseApplication):
    subcommands = dict(
        topup=(TopupCorrection, "Topup correction subapp"),
        bmepi=(BMEpiCorrection, "Block Matching EPI correction subapp")
    )


_apply_topup_aliases = dict(
    dwi="ApplyTopup.dwi",
    bvals="ApplyTopup.bvals",
    bvecs="ApplyTopup.bvecs",
    rev="ApplyTopup.rev",
    acqp="ApplyTopup.acquisition_file",
    topup="ApplyTopup.topup_prefix",
    out="ApplyTopup.output_prefix"
)


class ApplyTopup(mrHARDIBaseApplication):
    name = u"Apply Topup"
    description = "Apply a Topup transformation to an image"

    topup_prefix = required_file(
        description="Path and file prefix of the files corresponding "
                    "to the transformation calculated by Topup"
    )

    acquisition_file = required_file(
        description="Acquisition file describing the "
                    "orientation and readout of the volumes"
    )

    dwi = required_arg(
        MultipleArguments, traits_args=(Unicode(),),
        description="Input image or list of images"
    )

    bvals = required_arg(
        MultipleArguments, traits_args=(Unicode(),),
        description="Input b-values for the input dwis"
    )

    bvecs = required_arg(
        MultipleArguments, traits_args=(Unicode(),),
        description="Input b-vectors for the input dwis"
    )

    rev = MultipleArguments(
        Unicode(), default_value=[],
        help="Input reverse encoded image or list of images"
    ).tag(config=True)

    output_prefix = output_prefix_argument()

    resampling = Enum(
        ["jac", "lsr"], "jac", help="Resampling method"
    ).tag(config=True)

    interpolation = Enum(
        ["trilinear", "spline"], "spline",
        help="Interpolation method, only used with jacobian resampling (jac)"
    ).tag(Config=True)

    dtype = Enum(
        ["char", "short", "int", "float", "double"], None, allow_none=True,
        help="Force output type. If none supplied, "
             "will be the same as the input type."
    ).tag(config=True)

    aliases = Dict(default_value=_apply_topup_aliases)

    def _inspect_for_rev_at(self, i, n_volumes):
        rev = nib.load(self.rev[i]) if i < len(self.rev) else None
        if rev and len(rev.shape) > 3 and rev.shape[-1] == n_volumes:
            return self.rev[i]
        return None

    def execute(self):
        working_dir = getcwd()

        base_args = "--topup={} --method={} --interp={}".format(
            self.topup_prefix, self.resampling, self.interpolation
        )

        base_args += " --datain={}".format(self.acquisition_file)

        if self.dtype:
            base_args += " --datatype={}".format(self.dtype)

        dwi_groups = []

        for i, (dwi, bval, bvec) in enumerate(
            zip(self.dwi, self.bvals, self.bvecs)
        ):
            bvalvec = np.loadtxt(bval)[:, None] * np.loadtxt(bvec).T
            metadata = load_metadata(dwi)
            acq_types = metadata.acquisition_slices_to_list()
            new_group = True
            rev_vol = self._inspect_for_rev_at(i, bvalvec.shape[0])
            for gp in dwi_groups:
                if gp["bvalvec"].shape[0] == bvalvec.shape[0]:
                    if np.allclose(gp["bvalvec"], bvalvec):
                        if len(gp["acq_types"]) == len(acq_types):
                            if gp["acq_types"] == acq_types:
                                new_group = False
                                gp["dwi"].append(dwi)
                                gp["rev"].append(rev_vol)
                                break

            if new_group:
                dwi_groups.append({
                    "dwi": [dwi], "rev": [rev_vol],
                    "bval": bval, "bvec": bvec,
                    "bvalvec": bvalvec,
                    "acq_types": acq_types
                })

        for i, group in enumerate(dwi_groups):
            imain = "--imain={}".format(",".join(
                ",".join([dwi, rev]) if rev else dwi
                for dwi, rev in zip(group["dwi"], group["rev"])
            ))
            indexes = np.concatenate([
                np.concatenate([
                    load_metadata(dwi).topup_indexes,
                    load_metadata(rev).topup_indexes
                ]) if rev else load_metadata(dwi).topup_indexes
                for dwi, rev in zip(group["dwi"], group["rev"])
            ])
            imain += " --inindex={}".format(
                ",".join(str(i) for i in indexes.tolist())
            )
            imain += " --out={}_group{}".format(self.output_prefix, i)

            metadata = load_metadata(group["dwi"][0])
            save_metadata("{}_group{}".format(self.output_prefix, i), metadata)

            copyfile(
                group["bval"], "{}_group{}.bval".format(self.output_prefix, i)
            )
            copyfile(
                group["bvec"], "{}_group{}.bvec".format(self.output_prefix, i)
            )

            launch_shell_process(
                'applytopup {} {}'.format(base_args, imain),
                join(working_dir, "{}_group{}.log".format(
                    basename(self.output_prefix), i
                ))
            )
