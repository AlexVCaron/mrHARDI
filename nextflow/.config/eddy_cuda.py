# Configuration file for Magic Monkey.

c = get_config()

# -----------------------------------------------------------------------------
# Eddy(MagicMonkeyBaseApplication) configuration
# -----------------------------------------------------------------------------

c.Eddy.rev_bvals = ""

# Application traits configuration

c.Eddy.log_datefmt = "%Y-%m-%d %H:%M:%S"

c.Eddy.log_format = "[%(name)s]%(highlevel)s %(message)s"

c.Eddy.log_level = 30

c.Eddy.base_config_file = ""


# -----------------------------------------------------------------------------
# EddyConfiguration(MagicMonkeyConfigurable) configuration
# -----------------------------------------------------------------------------

c.EddyConfiguration.check_if_shelled = True

c.EddyConfiguration.current_model = "none"

c.EddyConfiguration.enable_cuda = True

c.EddyConfiguration.field_model = "quadratic"

c.EddyConfiguration.fill_empty = False

c.EddyConfiguration.interpolation = "spline"

c.EddyConfiguration.klass = "magic_monkey.config.eddy.EddyConfiguration"

c.EddyConfiguration.n_iter = 5

c.EddyConfiguration.n_voxels_hp = 1000

c.EddyConfiguration.outlier_model = {
    "n_std": 4,
    "n_vox": 250,
    "method": "sw",
    "pos_neg": False,
    "sum_squared": False,
    "mb_factor": 1,
    "mb_offset": 0
}

c.EddyConfiguration.pre_filter_width = 0

c.EddyConfiguration.qspace_smoothing = 10

c.EddyConfiguration.resampling = "jacobian"

c.EddyConfiguration.separate_subject_field = True

c.EddyConfiguration.skip_end_alignment = False

c.EddyConfiguration.slice_to_vol = {
    "t_motion_order": 0,
    "n_iter": 5,
    "w_reg": 1,
    "interpolation": "trilinear"
}

c.EddyConfiguration.susceptibility = {
    "n_iter": 10,
    "w_reg": 10,
    "knot_spacing": 10
}

