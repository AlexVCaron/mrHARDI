# Configuration file for Magic Monkey.

c = get_config()

# -----------------------------------------------------------------------------
# PftTracking(MagicMonkeyBaseApplication) configuration
#
# Description :
#  Magic Monkey configuration manager
# -----------------------------------------------------------------------------

c.PftTracking.pve_threshold = 0.5

c.PftTracking.save_seeds = False

c.PftTracking.seed_density = 2.0

c.PftTracking.seed_list = None

c.PftTracking.sphere_vertices = ""

c.PftTracking.white_matter_mask = ""

# Application traits configuration

c.PftTracking.log_datefmt = "%Y-%m-%d %H:%M:%S"

c.PftTracking.log_format = "[%(name)s]%(highlevel)s %(message)s"

c.PftTracking.log_level = 30

c.PftTracking.base_config_file = ""


# -----------------------------------------------------------------------------
# ParticleFilteringConfiguration(MagicMonkeyConfigurable) configuration
# -----------------------------------------------------------------------------

c.ParticleFilteringConfiguration.back_tracking_dist = 2

c.ParticleFilteringConfiguration.front_tracking_dist = 1

c.ParticleFilteringConfiguration.klass = "magic_monkey.config.pft_tracking.ParticleFilteringConfiguration"

c.ParticleFilteringConfiguration.max_crossing = None

c.ParticleFilteringConfiguration.max_trials = 20

c.ParticleFilteringConfiguration.particle_count = 15

