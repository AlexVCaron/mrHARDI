# Configuration file for Magic Monkey.

c = get_config()

# -----------------------------------------------------------------------------
# Topup(MagicMonkeyBaseApplication) configuration
# -----------------------------------------------------------------------------

c.Topup.extra_arguments = ""

# Application traits configuration

c.Topup.log_datefmt = "%Y-%m-%d %H:%M:%S"

c.Topup.log_format = "[%(name)s]%(highlevel)s %(message)s"

c.Topup.log_level = 30

c.Topup.base_config_file = ""


# -----------------------------------------------------------------------------
# TopupConfiguration(MagicMonkeyConfigurable) configuration
# -----------------------------------------------------------------------------

c.TopupConfiguration.interpolation = "linear"

c.TopupConfiguration.klass = "magic_monkey.config.topup.TopupConfiguration"

c.TopupConfiguration.passes = [{
    "warp_resolution": 20,
    "subsampling": 2,
    "blur_fwhm": 8,
    "n_iter": 5,
    "estimate_motion": 1,
    "minimizer": 0,
    "w_reg": 0.005
}, {
    "warp_resolution": 16,
    "subsampling": 2,
    "blur_fwhm": 6,
    "n_iter": 5,
    "estimate_motion": 1,
    "minimizer": 0,
    "w_reg": 0.001
}, {
    "warp_resolution": 14,
    "subsampling": 2,
    "blur_fwhm": 4,
    "n_iter": 5,
    "estimate_motion": 1,
    "minimizer": 0,
    "w_reg": 0.0001
}, {
    "warp_resolution": 12,
    "subsampling": 2,
    "blur_fwhm": 3,
    "n_iter": 5,
    "estimate_motion": 1,
    "minimizer": 0,
    "w_reg": 1.5e-05
}, {
    "warp_resolution": 10,
    "subsampling": 2,
    "blur_fwhm": 3,
    "n_iter": 5,
    "estimate_motion": 1,
    "minimizer": 0,
    "w_reg": 5e-07
}, {
    "warp_resolution": 6,
    "subsampling": 1,
    "blur_fwhm": 2,
    "n_iter": 10,
    "estimate_motion": 0,
    "minimizer": 1,
    "w_reg": 5e-07
}, {
    "warp_resolution": 4,
    "subsampling": 1,
    "blur_fwhm": 1,
    "n_iter": 10,
    "estimate_motion": 0,
    "minimizer": 1,
    "w_reg": 5e-08
}, {
    "warp_resolution": 4,
    "subsampling": 1,
    "blur_fwhm": 0,
    "n_iter": 20,
    "estimate_motion": 0,
    "minimizer": 1,
    "w_reg": 5e-10
}, {
    "warp_resolution": 4,
    "subsampling": 1,
    "blur_fwhm": 0,
    "n_iter": 20,
    "estimate_motion": 0,
    "minimizer": 1,
    "w_reg": 5e-11
}]

c.TopupConfiguration.precision = "double"

c.TopupConfiguration.reg_model = "bending_energy"

c.TopupConfiguration.scale_intensities = True

c.TopupConfiguration.spl_order = "quadratic"

c.TopupConfiguration.ssq_scale_lambda = True

