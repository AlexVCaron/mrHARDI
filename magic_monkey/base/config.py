from ipython_genutils.text import wrap_paragraphs
from traitlets.config import Configurable, HasTraits, Config, \
    PyFileConfigLoader, ConfigFileNotFound


class ConfigurationLoader:
    def __init__(self, target, raise_error=True, log=None):
        self._target = target
        self._loaded_config_files = []
        self.raise_config_file_errors = raise_error
        self.log = log

    def load_configuration(self, filename):
        """Load config files by filename and path."""
        new_config = Config()
        for (config, filename) in self._load_config_files(
            filename, raise_config_file_errors=self.raise_config_file_errors,
        ):
            new_config.merge(config)
            if filename not in self._loaded_config_files:
                self._loaded_config_files.append(filename)
        # add self.cli_config to preserve CLI config priority
        try:
            new_config.merge(self._target.cli_config)
        except AttributeError:
            # We are configuring a cli-less configurable, ignore
            pass

        self._target.update_config(new_config)

    def _load_config_files(self, filename, raise_config_file_errors=False):
        """Load config files (py,json) by filename and path.

        yield each config object in turn.
        """
        pyloader = PyFileConfigLoader(filename, path=None, log=self.log)
        if self.log:
            self.log.debug("Looking for ", filename)

        config = None
        try:
            config = pyloader.load_config()
        except ConfigFileNotFound:
            pass
        except Exception:
            # try to get the full filename, but it will be empty in the
            # unlikely event that the error raised before filefind finished
            filename = pyloader.full_filename or filename
            # problem while running the file
            if raise_config_file_errors:
                raise
            if self.log:
                self.log.error(
                    "Exception while loading config file %s",
                    filename, exc_info=True
                )
        else:
            if self.log:
                self.log.debug("Loaded config file: %s", pyloader.full_filename)
        if config:
            yield config, pyloader.full_filename


class ConfigurationWriter:
    default_ext = "py"

    def __init__(
        self, char_per_line=76,
        section_break='# ' + '-' * 77,
        extension=default_ext
    ):
        self._cpl = char_per_line
        self._sb = section_break
        self._ext = extension

    def write_configuration_file(
        self, filename, configurable,
        base_klass=Configurable, standalone_sub_conf=True
    ):
        traits = configurable.class_traits(
            ignore_write=True, hidden=lambda a: a
        )
        classes = (configurable.__class__,) + configurable.__class__.__bases__

        for k in traits.keys():
            for klass in classes:
                try:
                    delattr(klass, k)
                except AttributeError:
                    pass

        with open(self._with_ext(filename), 'w+') as f:
            f.writelines([
                "# Configuration file for %s.\n\n" % configurable.name,
                "c = get_config()\n\n",
                self.config_section(
                    configurable, base_klass, standalone_sub_conf
                )
            ])

        for k, v in traits.items():
            for klass in classes:
                try:
                    setattr(klass, k, v)
                except AttributeError:
                    pass

    def _with_ext(self, filename):
        return "{}.{}".format(filename, self._ext)

    def _comment_block(self, block):
        """return a commented, wrapped block."""
        block = '\n\n'.join(wrap_paragraphs(block, self._cpl))

        return '#  ' + block.replace('\n', '\n#  ')

    def _description(self, trait_klass):
        lines = []
        desc = trait_klass.class_traits().get('description')

        if desc:
            desc = desc.default_value
        if not desc:
            # no description from trait, use __doc__
            desc = getattr(trait_klass, '__doc__', '')

        if desc:
            lines.append('#')
            lines.append("# Description :")
            lines.append(self._comment_block(desc))

        return lines

    def config_section(
        self, configurable, base_klass=Configurable, standalone_sub_conf=True
    ):
        # section header
        klass = configurable.__class__
        parent_classes = ','.join(p.__name__ for p in klass.__bases__)

        s = "# %s(%s) configuration" % (klass.__name__, parent_classes)
        lines = [self._sb, s]

        # get the description trait
        lines.extend(self._description(klass))

        sub_configurables = []
        # Get base traits, so we put them at the end of this
        # config section, before the sub-configurables
        base_classes = base_klass.__bases__
        base_classes += (base_klass,)
        base_traits = dict()
        for base_class in base_classes:
            if HasTraits in base_class.mro():
                base_traits.update(base_class.class_own_traits(config=True))

        for name, trait in sorted(configurable.traits(
            config=True, ignore_write=None, required=None
        ).items()):
            if name not in base_traits:
                inst = trait.get(configurable, klass)
                if isinstance(inst, base_klass):
                    sub_configurables.append((name, inst))
                else:
                    lines.append('c.%s.%s = %s' % (
                        klass.__name__, name,
                        '"%s"' % inst if isinstance(inst, str) else inst
                    ))

                lines.append('')

        if len(base_traits) > 0:
            lines.append("# Base traits configuration")
            lines.append('')

        for name, trait in base_traits.items():
            inst = trait.get(configurable, klass)
            lines.append('c.%s.%s = %s' % (
                klass.__name__,
                name,
                '"%s"' % inst if isinstance(inst, str) else inst
            ))
            lines.append('')

        lines.append('')

        if standalone_sub_conf:
            for _, s_conf in sub_configurables:
                lines.append('%s' % s_conf)
                lines.append('')
        else:
            for name, inst in sub_configurables:
                lines.append('c.%s.%s = %s' % (
                    klass.__name__,
                    name,
                    '"%s"' % inst if isinstance(inst, str) else repr(inst)
                ))
                # lines.append('%s' % inst)
                lines.append('')

        return '\n'.join(lines)

    def class_config_section(self, klass):
        # section header
        parent_classes = ','.join(p.__name__ for p in klass.__bases__)

        s = "# %s(%s) configuration" % (klass.__name__, parent_classes)
        lines = [self._sb, s, self._sb, '']

        lines.extend(self._description(klass))

        config_item = None
        for name, trait in sorted(klass.class_own_traits(config=True).items()):
            if name == "configuration":
                config_item = (name, trait)
            else:
                lines.append('c.%s.%s = %s' % (
                    klass.__name__, name, trait.default_value_repr()
                ))
                lines.append('')

        if config_item is not None:
            name, trait = config_item
            lines.append('c.%s.%s = %s' % (
                klass.__name__, name, trait.default_value_repr()
            ))
            lines.append('')

        return '\n'.join(lines)
