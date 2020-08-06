from magic_monkey.apps import *

from magic_monkey.base.application import MagicMonkeyBaseApplication


class MagicMonkeyApplication(MagicMonkeyBaseApplication):
    subcommands = dict(
        ants_registration=(AntsRegistration, 'Register images via ants'),
        ants_transform=(AntsTransform, 'Apply a registration transform'),
        apply_mask=(ApplyMask, 'Apply mask to image'),
        b0=(B0Utils, 'Basic processing on B0 slices of dwi volumes'),
        concatenate=(Concatenate, 'Concatenates images together'),
        csd=(CSD, 'Perform constrained spherical deconvolution'),
        diamond=(Diamond, 'Perform diamond reconstruction'),
        diamond_metrics=(DiamondMetrics, 'Compute DTI metrics'),
        dti=(DTI, 'Perform dti reconstruction'),
        dti_metrics=(DTIMetrics, 'Compute DTI metrics'),
        eddy=(Eddy, 'Execute eddy correction'),
        response=(
            FiberResponse,
            'Compute single fiber response (and gm and csf if msmt)'
        ),
        topup=(Topup, 'Execute topup correction')
    )


launch_new_instance = MagicMonkeyApplication.launch_instance


if __name__ == '__main__':
    launch_new_instance()
