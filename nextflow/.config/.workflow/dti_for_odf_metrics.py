# Configuration file for Magic Monkey.

c = get_config()

# -----------------------------------------------------------------------------
# TensorMetrics(MagicMonkeyBaseApplication) configuration
# -----------------------------------------------------------------------------
c.TensorMetrics.metrics = ['fa', 'md']

c.TensorMetrics.output_colors = False

c.TensorMetrics.save_eigs = False

# Application traits configuration

c.TensorMetrics.log_datefmt = "%Y-%m-%d %H:%M:%S"

c.TensorMetrics.log_format = "[%(name)s]%(highlevel)s %(message)s"

c.TensorMetrics.log_level = 30

c.TensorMetrics.base_config_file = ""

