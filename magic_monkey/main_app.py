#!/usr/bin/env python3

import sys

from magic_monkey.base.application import MagicMonkeyBaseApplication


def cast_unicode(s):
    print(s)
    if isinstance(s, bytes):
        return s.decode(sys.stdin.encoding, 'replace')
    return s


class MagicMonkeyApplication(MagicMonkeyBaseApplication):
    def execute(self):
        if self.subapp:
            self.subapp.start()

    @classmethod
    def launch_instance(cls, argv=None, **kwargs):
        print("Launching instance")
        print(argv if argv else "No argv sent")
        assert not isinstance(argv, str)
        argv = sys.argv[1:] if argv is None else argv
        print(argv)
        argv = [cast_unicode(arg) for arg in argv]
        super().launch_instance(argv, **kwargs)

    def _example_command(self, *args):
        return "magic_monkey command <args> <flags>"

    subcommands = dict(
        ants_motion=(
            "magic_monkey.apps.register.AntsMotionCorrection",
            '4D motion correction'
        ),
        ants_registration=(
            "magic_monkey.apps.register.AntsRegistration",
            'Register images via ants'
        ),
        ants_transform=(
            "magic_monkey.apps.register.AntsTransform",
            'Apply a registration transform'
        ),
        apply_mask=("magic_monkey.apps.utils.ApplyMask", 'Apply mask to image'),
        apply_topup=(
            "magic_monkey.apps.denoise.ApplyTopup",
            'Apply Topup correction to a set of images'
        ),
        b0=(
            "magic_monkey.apps.utils.B0Utils",
            'Basic processing on B0 slices of dwi volumes'
        ),
        shells=(
            "magic_monkey.apps.utils.ExtractShells",
            'Extract a subset of shells from a dwi dataset'
        ),
        check=(
            "magic_monkey.apps.utils.AssertDwiDimensions",
            'Basic checks on b-values/b-vectors conformity to an dwi 4D image'
        ),
        concatenate=(
            "magic_monkey.apps.utils.Concatenate",
            'Concatenates images together'
        ),
        convert=(
            "magic_monkey.apps.utils.ConvertImage",
            "Convert attributes of images"
        ),
        csd=(
            "magic_monkey.apps.reconstruct.CSD",
            'Perform constrained spherical deconvolution'
        ),
        diamond=(
            "magic_monkey.apps.reconstruct.Diamond",
            'Perform diamond reconstruction'
        ),
        diamond_metrics=(
            "magic_monkey.apps.measure.DiamondMetrics", 'Compute DTI metrics'
        ),
        dti=("magic_monkey.apps.reconstruct.DTI", 'Perform dti reconstruction'),
        dti_metrics=(
            "magic_monkey.apps.measure.TensorMetrics",
            'Compute DTI metrics'
        ),
        eddy=("magic_monkey.apps.denoise.Eddy", 'Execute eddy correction'),
        eddy_viz=(
            "magic_monkey.apps.visualize.VisualizeEddyParameters",
            "Visualization of eddy's optimization train"
        ),
        fitbox=(
          "magic_monkey.apps.utils.FitBox",
          'Fit a bounding box with reference to another image'
        ),
        fit2box=(
            "magic_monkey.apps.utils.FitToBox",
            'Pad or crop an image to a bounding box'
        ),
        gif=(
            "magic_monkey.apps.visualize.GifAnimator",
            'Create at gif from a list of images'
        ),
        metadata=(
            "magic_monkey.apps.utils.DwiMetadataUtils",
            'Create metadata file(s) describing one or more dwi datasets'
        ),
        mosaic=(
            "magic_monkey.apps.visualize.Mosaic",
            'Generate a mosaic for a 3D measure or image'
        ),
        n4=(
            "magic_monkey.apps.denoise.N4BiasCorrection",
            'Denoise rician and chi squared noise artifacts from dwi datasets'
        ),
        pft=(
            "magic_monkey.apps.track.PftTracking",
            'Execute particle filtering tracking'
        ),
        replicate=(
            "magic_monkey.apps.utils.ReplicateImage",
            'Replicate an image to fit another one on the last axis'
        ),
        response=(
            "magic_monkey.apps.reconstruct.FiberResponse",
            'Compute single fiber response (and gm and csf if msmt)'
        ),
        split=(
            "magic_monkey.apps.utils.SplitImage",
            'Split an image given an axis'
        ),
        topup=("magic_monkey.apps.denoise.Topup", 'Execute topup correction')
    )


launch_new_instance = MagicMonkeyApplication.launch_instance


def console_entry_point():
    launch_new_instance()


if __name__ == '__main__':
    console_entry_point()



