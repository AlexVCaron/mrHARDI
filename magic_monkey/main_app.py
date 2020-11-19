from magic_monkey.base.application import MagicMonkeyBaseApplication


class MagicMonkeyApplication(MagicMonkeyBaseApplication):
    def execute(self):
        if self.subapp:
            self.subapp.start()

    def _example_command(self, *args):
        return "magic_monkey command <args> <flags>"

    subcommands = dict(
        ants_motion=(
            "magic_monkey.apps.AntsMotionCorrection", '4D motion correction'
        ),
        ants_registration=(
            "magic_monkey.apps.AntsRegistration", 'Register images via ants'
        ),
        ants_transform=(
            "magic_monkey.apps.AntsTransform", 'Apply a registration transform'
        ),
        apply_mask=("magic_monkey.apps.ApplyMask", 'Apply mask to image'),
        apply_topup=(
            "magic_monkey.apps.ApplyTopup",
            'Apply Topup correction to a set of images'
        ),
        b0=(
            "magic_monkey.apps.B0Utils",
            'Basic processing on B0 slices of dwi volumes'
        ),
        check=(
            "magic_monkey.apps.AssertDwiDimensions",
            'Basic checks on b-values/b-vectors conformity to an dwi 4D image'
        ),
        concatenate=(
            "magic_monkey.apps.Concatenate", 'Concatenates images together'
        ),
        convert=(
            "magic_monkey.apps.ConvertImage", "Convert attributes of images"
        ),
        csd=(
            "magic_monkey.apps.CSD",
            'Perform constrained spherical deconvolution'
        ),
        diamond=(
            "magic_monkey.apps.Diamond", 'Perform diamond reconstruction'
        ),
        diamond_metrics=(
            "magic_monkey.apps.DiamondMetrics", 'Compute DTI metrics'
        ),
        dti=("magic_monkey.apps.DTI", 'Perform dti reconstruction'),
        dti_metrics=("magic_monkey.apps.TensorMetrics", 'Compute DTI metrics'),
        eddy=("magic_monkey.apps.Eddy", 'Execute eddy correction'),
        eddy_viz=(
            "magic_monkey.apps.VisualizeEddyParameters",
            "Visualization of eddy's optimization train"
        ),
        gif=(
            "magic_monkey.apps.GifAnimator",
            'Create at gif from a list of images'
        ),
        metadata=(
            "magic_monkey.apps.DwiMetadataUtils",
            'Create metadata file(s) describing one or more dwi datasets'
        ),
        n4=(
            "magic_monkey.apps.N4BiasCorrection",
            'Denoise rician and chi squared noise artifacts from dwi datasets'
        ),
        pft=(
            "magic_monkey.apps.PftTracking",
            'Execute particle filtering tracking'
        ),
        replicate=(
            "magic_monkey.apps.ReplicateImage",
            'Replicate an image to fit another one on the last axis'
        ),
        response=(
            "magic_monkey.apps.FiberResponse",
            'Compute single fiber response (and gm and csf if msmt)'
        ),
        topup=("magic_monkey.apps.Topup", 'Execute topup correction'),
        split=("magic_monkey.apps.SplitImage", 'Split an image given an axis'),
        eddy_viz=(
            "magic_monkey.apps.VisualizeEddyParameters",
            "Visualization of eddy's optimization train"
        )
    )


launch_new_instance = MagicMonkeyApplication.launch_instance


def console_entry_point():
    launch_new_instance()


if __name__ == '__main__':
    console_entry_point()



