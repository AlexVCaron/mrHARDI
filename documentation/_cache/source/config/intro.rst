==========================================
Introduction to Magic Monkey configuration
==========================================

.. important:: This page is a slightly modified copy of the IPython
               documentation fitted to Magic Monkey. It covers the
               configuration system used by Magic Monkey. It will change once
               the modifications made by Magic Monkey to it become documented.

.. _setting_config:

Setting configurable options
============================

Many of Magic Monkey's classes have configurable attributes (see
:doc:`options/index` for the list). These can be
configured in several ways.

Python configuration files
--------------------------

To create the blank configuration files for an application, run::

    magic-monkey <application> --out-config <filename>

By default, configuration files are fully featured Python scripts that can
execute arbitrary code, the main usage is to set value on the configuration
object ``c`` which exist in your configuration file.

You can then configure class attributes like this::

    c.MagicMonkeyApplication.<attribute> = False
    c.Eddy.<attribute> = <Attribute>()
    c.Eddy.configuration.<attribute> = <Attribute>()

Be careful with spelling--incorrect names will simply be ignored, with
no error. 

To add to a collection which may have already been defined elsewhere or have
default values, you can use methods like those found on lists, dicts and
sets: append, extend, :meth:`~traitlets.config.LazyConfigValue.prepend` (like
extend, but at the front), add and update (which works both for dicts and
sets)::

    c.MagicMonkeyApplication.config_files.append('a_config.py')

.. versionadded:: 2.0
   list, dict and set methods for config values

Example configuration file
``````````````````````````

::

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

    # Application traits configuration

    c.PftTracking.log_format = "[%(name)s]%(highlevel)s %(message)s"

    c.PftTracking.log_level = 30

    # -----------------------------------------------------------------------------
    # ParticleFilteringConfiguration(MagicMonkeyConfigurable) configuration
    # -----------------------------------------------------------------------------

    c.ParticleFilteringConfiguration.back_tracking_dist = 2

    c.ParticleFilteringConfiguration.front_tracking_dist = 1

    c.ParticleFilteringConfiguration.max_trials = 20

    c.ParticleFilteringConfiguration.particle_count = 15


JSON Configuration files
------------------------

In case where executability of configuration can be problematic, or
configurations need to be modified programmatically, Magic Monkey also support
a limited set of functionalities via ``.json`` configuration files.

You can defined most of the configuration options via a json object which
hierarchy represent the value you would normally set on the ``c`` object of
``.py`` configuration files. The following ``config.json`` file::

    {
        "PftTracking": {
            "log_level": 30,
        },
        "ParticleFilteringConfiguration": {
            "back_tracking_dist": 2,
            "front_tracking_dist": 1
        },
        "MagicMonkeyBaseApplication": {
            "log_format": "[%(name)s]%(highlevel)s %(message)s"
        }
    }

Is equivalent to the following ``config.py``::

    c.PftTracking.log_level = 30

    c.ParticleFilteringConfiguration.back_tracking_dist = 2
    c.ParticleFilteringConfiguration.front_tracking_dist = 1

    c.MagicMonkeyBaseApplication.log_format = "[%(name)s]%(highlevel)s %(message)s"

Notice that configuration files take into account inheritance. So here, by
the log format on the class MagicMonkeyBaseApplication, the logging mechanism
is configured for all child classes of it (in the example above, to the class
PftTracking).

Command line arguments
----------------------

Every configurable value can be set from the command line, using this
syntax::

    magic-monkey --ClassName.attribute=value

Many frequently used options have short aliases and flags, such as
``--in`` or ``--out`` (when defining input or output files) or
``--config`` (to specify a configuration file).

To see all of these abbreviated options, run::

    magic-monkey --help
    magic-monkey <application> --help
    # etc.

Options specified at the command line, in either format, override
options set in a configuration file.
