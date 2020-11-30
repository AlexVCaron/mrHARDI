# Configuration file for Magic Monkey.

c = get_config()

# -----------------------------------------------------------------------------
# AntsTransform(MagicMonkeyBaseApplication) configuration
# -----------------------------------------------------------------------------

# Application traits configuration

c.AntsTransform.log_datefmt = "%Y-%m-%d %H:%M:%S"

c.AntsTransform.log_format = "[%(name)s]%(highlevel)s %(message)s"

c.AntsTransform.log_level = 30

c.AntsTransform.base_config_file = ""


# -----------------------------------------------------------------------------
# AntsTransformConfiguration(MagicMonkeyConfigurable) configuration
# -----------------------------------------------------------------------------

c.AntsTransformConfiguration.dimension = 3

c.AntsTransformConfiguration.fill_value = 0

c.AntsTransformConfiguration.input_type = 0

c.AntsTransformConfiguration.interpolation = "Linear"

c.AntsTransformConfiguration.klass = "magic_monkey.config.ants.AntsTransformConfiguration"

