#!/usr/bin/env python3

import sys

from mrHARDI.base.application import mrHARDIBaseApplication


def cast_unicode(s):
    if isinstance(s, bytes):
        return s.decode(sys.stdin.encoding, 'replace')
    return s


class mrHARDIApplication(mrHARDIBaseApplication):
    def execute(self):
        if self.subapp:
            self.subapp.start()

    @classmethod
    def launch_instance(cls, argv=None, **kwargs):
        assert not isinstance(argv, str)
        argv = sys.argv[1:] if argv is None else argv
        argv = [cast_unicode(arg) for arg in argv]
        super().launch_instance(argv, **kwargs)

    def _example_command(self, *args):
        return "mrhardi [cmd] <args> <flags>"

    subcommands = dict(
        ants_motion=(
            "mrHARDI.apps.register.AntsMotionCorrection",
            '4D motion correction'
        ),
        ants_registration=(
            "mrHARDI.apps.register.AntsRegistration",
            'Register images via ants'
        ),
        ants_transform=(
            "mrHARDI.apps.register.AntsTransform",
            'Apply a registration transform'
        ),
        apply_mask=(
            "mrHARDI.apps.utils.ApplyMask", 'Apply mask to image'
        ),
        apply_topup=(
            "mrHARDI.apps.denoise.ApplyTopup",
            'Apply Topup correction to a set of images'
        ),
        b0=(
            "mrHARDI.apps.utils.B0Utils",
            'Basic processing on B0 slices of dwi volumes'
        ),
        shells=(
            "mrHARDI.apps.utils.ExtractShells",
            'Extract a subset of shells from a dwi dataset'
        ),
        check=(
            "mrHARDI.apps.utils.AssertDwiDimensions",
            'Basic checks on b-values/b-vectors conformity to an dwi 4D image'
        ),
        concatenate=(
            "mrHARDI.apps.utils.Concatenate",
            'Concatenates images together'
        ),
        convert=(
            "mrHARDI.apps.utils.ConvertImage",
            "Convert attributes of images"
        ),
        csd=(
            "mrHARDI.apps.reconstruct.CSD",
            'Perform constrained spherical deconvolution'
        ),
        diamond=(
            "mrHARDI.apps.reconstruct.Diamond",
            'Perform diamond reconstruction'
        ),
        diamond_metrics=(
            "mrHARDI.apps.measure.DiamondMetrics", 'Compute DTI metrics'
        ),
        dti=(
            "mrHARDI.apps.reconstruct.DTI", 'Perform dti reconstruction'
        ),
        dti_metrics=(
            "mrHARDI.apps.measure.TensorMetrics",
            'Compute DTI metrics'
        ),
        duplicates=(
            "mrHARDI.apps.utils.CheckDuplicatedBvecsInShell",
            'Check and handles duplicated directions in DWI shells'
        ),
        eddy=("mrHARDI.apps.denoise.Eddy", 'Execute eddy correction'),
        eddy_viz=(
            "mrHARDI.apps.visualize.VisualizeEddyParameters",
            "Visualization of eddy's optimization train"
        ),
        even_dimensions=(
            "mrHARDI.apps.utils.FixOddDimensions",
            'Fixes images with a odd number of slices in a space dimension'
        ),
        fitbox=(
          "mrHARDI.apps.utils.FitBox",
          'Fit a bounding box with reference to another image'
        ),
        fit2box=(
            "mrHARDI.apps.utils.FitToBox",
            'Pad or crop an image to a bounding box'
        ),
        flip2ref=(
            "mrHARDI.apps.utils.FlipGradientsOnReference",
            'Flip gradients following reference\'s strides'
        ),
        gif=(
            "mrHARDI.apps.visualize.GifAnimator",
            'Create at gif from a list of images'
        ),
        metadata=(
            "mrHARDI.apps.utils.DwiMetadataUtils",
            'Create metadata file(s) describing one or more dwi datasets'
        ),
        mosaic=(
            "mrHARDI.apps.visualize.Mosaic",
            'Generate a mosaic for a 3D measure or image'
        ),
        n4=(
            "mrHARDI.apps.denoise.N4BiasCorrection",
            'Denoise rician and chi squared noise artifacts from dwi datasets'
        ),
        nlmeans=(
            "mrHARDI.apps.denoise.NonLocalMeans",
            'Run Non-Local Means denoising on 3D MRI data'
        ),
        pft=(
            "mrHARDI.apps.track.PftTracking",
            'Execute particle filtering tracking'
        ),
        replicate=(
            "mrHARDI.apps.utils.ReplicateImage",
            'Replicate an image to fit another one on the last axis'
        ),
        resampling_reference=(
            "mrHARDI.apps.utils.ResamplingReference",
            'Compute a reference image for resampling base on criterias'
        ),
        response=(
            "mrHARDI.apps.reconstruct.FiberResponse",
            'Compute single fiber response (and gm and csf if msmt)'
        ),
        seg2mask=(
            "mrHARDI.apps.utils.Segmentation2Mask",
            'Splits a segmentation image intensities into masks'
        ),
        split=(
            "mrHARDI.apps.utils.SplitImage",
            'Split an image given an axis'
        ),
        topup=("mrHARDI.apps.denoise.Topup", 'Execute topup correction'),
        validate=(
            "mrHARDI.apps.validate.Validate", 'Data validation'
        )
    )


launch_new_instance = mrHARDIApplication.launch_instance


def console_entry_point():
    launch_new_instance()


if __name__ == '__main__':
    console_entry_point()
