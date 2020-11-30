# Configuration file for ANTs Motion Correction.

c = get_config()

# -----------------------------------------------------------------------------
# AntsMotionCorrection(MagicMonkeyBaseApplication) configuration
c.AntsMotionCorrection.base_config_file = ""


c.AntsMotionCorrection.log_datefmt = "%Y-%m-%d %H:%M:%S"

c.AntsMotionCorrection.log_format = "[%(name)s]%(highlevel)s %(message)s"

c.AntsMotionCorrection.log_level = 30

c.AntsMotionCorrection.metadata = ""

c.AntsMotionCorrection.verbose = True


# -----------------------------------------------------------------------------
# AntsMotionCorrectionConfiguration(MagicMonkeyConfigurable) configuration
c.AntsMotionCorrectionConfiguration.average = False

c.AntsMotionCorrectionConfiguration.dimension = 3

c.AntsMotionCorrectionConfiguration.learn_once = False

c.AntsMotionCorrectionConfiguration.n_template_points = 10

c.AntsMotionCorrectionConfiguration.passes = [{
    "conv_max_iter": [100, 50, 20, 10],
    "grad_step": 0.1,
    "klass": "magic_monkey.traits.ants.AntsRigid",
    "metrics": [
        {
            "target_index": 0,
            "moving_index": 0,
            "args": [
                1.0,
                32,
                "Regular",
                0.25
            ],
            "klass": "magic_monkey.traits.ants.MetricMI"
        }
    ],
    "shrinks": [
        8,
        4,
        2,
        1
    ],
    "smoothing": [
        3,
        2,
        1,
        0
    ]
}, {
    "conv_max_iter": [100, 50, 20, 10],
    "grad_step": 0.1,
    "klass": "magic_monkey.traits.ants.AntsAffine",
    "metrics": [
        {
            "target_index": 0,
            "moving_index": 0,
            "args": [
                1.0,
                32,
                "Regular",
                0.25
            ],
            "klass": "magic_monkey.traits.ants.MetricMI"
        }
    ],
    "shrinks": [
        8,
        4,
        2,
        1
    ],
    "smoothing": [
        3,
        2,
        1,
        0
    ]
}]

c.AntsMotionCorrectionConfiguration.register_to_prior = True

c.AntsMotionCorrectionConfiguration.scale_estimator = False

c.AntsMotionCorrectionConfiguration.to_field = False

# Base traits configuration

c.AntsMotionCorrectionConfiguration.klass = "magic_monkey.config.ants.AntsMotionCorrectionConfiguration"


