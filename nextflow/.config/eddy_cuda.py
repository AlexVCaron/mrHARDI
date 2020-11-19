# Configuration file for Magic Monkey.

c = get_config()

# -----------------------------------------------------------------------------
# Eddy(MagicMonkeyBaseApplication) configuration
# -----------------------------------------------------------------------------

# Application traits configuration

c.Eddy.log_datefmt = "%Y-%m-%d %H:%M:%S"

c.Eddy.log_format = "[%(name)s]%(highlevel)s %(message)s"

c.Eddy.log_level = 30

c.Eddy.base_config_file = ""


# -----------------------------------------------------------------------------
# EddyConfiguration(MagicMonkeyConfigurable) configuration
# -----------------------------------------------------------------------------

c.EddyConfiguration.check_if_shelled = False

c.EddyConfiguration.current_model = "linear"

c.EddyConfiguration.enable_cuda = True

c.EddyConfiguration.field_model = "cubic"

c.EddyConfiguration.fill_empty = True

c.EddyConfiguration.interpolation = "spline"

c.EddyConfiguration.klass = "magic_monkey.config.eddy.EddyConfiguration"

c.EddyConfiguration.n_iter = 5

c.EddyConfiguration.n_voxels_hp = 4000

c.EddyConfiguration.outlier_model = {
    "n_std": 3,
    "n_vox": 250,
    "method": "both",
    "pos_neg": False,
    "sum_squared": False
}

c.EddyConfiguration.pre_filter_width = [0]

c.EddyConfiguration.qspace_smoothing = 5

c.EddyConfiguration.resampling = "jacobian"

c.EddyConfiguration.separate_subject_field = True

c.EddyConfiguration.skip_end_alignment = False

# c.EddyConfiguration.slice_to_vol = {
#     "t_motion_fraction": 2,
#     "n_iter": 8,
#     "w_reg": 5,
#     "interpolation": "trilinear"
# }

c.EddyConfiguration.use_b0_peas = False

c.EddyConfiguration.susceptibility = None
