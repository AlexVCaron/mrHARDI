import json
import sys
from abc import abstractmethod
from copy import copy
from importlib import import_module
from multiprocessing import cpu_count
from os import getcwd, linesep
from os.path import splitext

import numpy as np
from numpy import arange, split
from traitlets import Float, Integer, TraitType, Undefined
from traitlets.config import (Application,
                              ArgumentError,
                              Configurable,
                              Dict,
                              Enum,
                              Instance,
                              List,
                              TraitError,
                              Unicode,
                              catch_config_error,
                              dedent,
                              deepcopy,
                              default,
                              indent,
                              logging,
                              observe,
                              observe_compat,
                              wrap_paragraphs)

from magic_monkey.base.ListValuedDict import ListValuedDict
from magic_monkey.base.config import ConfigurationWriter
from magic_monkey.base.encoding import MagicConfigEncoder

base_aliases = {
    'config': 'MagicMonkeyBaseApplication.base_config_file',
    'out-config': 'MagicMonkeyBaseApplication.output_config',
    'metadata': 'MagicMonkeyBaseApplication.metadata'
}

base_flags = dict(
    debug=({'Application': {'log_level': logging.DEBUG}},
           "set log level to logging.DEBUG (maximize logging output)"),
    quiet=({'Application': {'log_level': logging.CRITICAL}},
           "set log level to logging.CRITICAL (minimize logging output)")
)


class MagicMonkeyBaseApplication(Application):
    name = u'Magic Monkey'
    description = Unicode(u'Magic Monkey configuration manager')

    # Todo: Change when scm versioning is implemented
    version = Unicode(u'0.1.0')

    aliases = Dict()
    flags = Dict()

    config_files = List(Unicode, [])
    configuration = Instance(Configurable, allow_none=True)

    output_config = Unicode(
        help="File path. If set, the application will output the current "
             "state of the application to the specified file"
    ).tag(config=True, ignore_write=True)

    current_config = Unicode()

    required = List()

    @default('config_files')
    def _config_files_default(self):
        return [self.current_config]

    config_file_paths = List(Unicode, [])

    metadata = Unicode("").tag(config=True)

    @observe('config')
    @observe_compat
    def _config_changed(self, change):
        self._load_config(change.new, [self.configuration])
        super()._config_changed(change)

    @default('config_file_paths')
    def _config_file_paths_default(self):
        return [getcwd()]

    def update_config(self, config):
        super().update_config(config)
        try:
            self.configuration.update_config(config)
        except AttributeError:
            pass

    base_config_file = Unicode(
        help="Base configuration file for the application",
        allow_none=True
    ).tag(config=True)

    @observe('base_config_file')
    def _base_config_file_changed(self, change):
        old = change['old']
        new = change['new']
        try:
            self.config_files.remove(old)
        except ValueError:
            pass
        self.config_files.append(new)

    _delayed_help_traits = []

    @default('classes')
    def _classes_default(self):
        return (self.__class__,) + self.__class__.__bases__

    def __init__(self, **kwargs):
        conf_klass = self.__class__.configuration.klass
        if MagicMonkeyConfigurable in conf_klass.mro():
            try:
                self.configuration = conf_klass(parent=self)
                self.classes.extend((conf_klass,) + conf_klass.__bases__)
            except AttributeError:
                pass
        super().__init__(**kwargs)

    def load_config_file(self, **kwargs):
        Application.load_config_file(
            self, self.base_config_file, path=self.config_file_paths, **kwargs
        )

        for file_name in self.config_files:
            if not file_name or file_name == self.base_config_file:
                continue

            Application.load_config_file(
                self, file_name, path=self.config_file_paths, **kwargs
            )

    @catch_config_error
    def _validate_required(self):
        missing_required = []
        for trait in self.class_traits(required=True).values():
            if trait.get(self) == self.get_default_value(trait):
                missing_required.append(trait.name)

        if len(missing_required) > 0:
            raise ArgumentError(
                "{} is missing required parameters : {}".format(
                    self.__class__.__name__,
                    ", ".join(m for m in missing_required)
                )
            )

    def _shut_completed_exclusive(self):
        exclusive_traits = self.class_traits(
            exclusive_group=lambda t: t is not None
        )

        trait_groups = {
            k: [] for k in np.unique(list(
                t.get_metadata("exclusive_group")
                for t in exclusive_traits.values()
            ))
        }

        for n, t in exclusive_traits.items():
            trait_groups[t.get_metadata("exclusive_group")].append(t)

        for group, traits in trait_groups.items():
            trait_bundles = {
                k: [] for k in np.unique(
                    list(t.get_metadata("group_index", 0) for t in traits)
                )
            }
            for t in traits:
                trait_bundles[t.get_metadata("group_index", 0)].append(t)

            traits_bools = {}
            for k, t in trait_bundles.items():
                traits_bools[k] = [
                    tt.get(self) != self.get_default_value(tt) or not ("required" in tt.metadata and tt.metadata["required"]) for tt in t
                ]

            if any(all(t) for t in traits_bools.values()):
                for _, b_traits in filter(
                    lambda kv: not all(traits_bools[kv[0]]),
                    trait_bundles.items()
                ):
                    for trait in b_traits:
                        trait.tag(required=False)

    @catch_config_error
    def _validate_configuration(self):
        if self.configuration:
            config = self.traits()["configuration"].get(self)
            config.validate()

    @catch_config_error
    def _validate_extra(self):
        for trait in self.traits().values():
            if "extra_valid" in trait.metadata:
                if not trait.metadata["extra_valid"](trait.get(self)):
                    raise TraitError(trait)

    @catch_config_error
    def _validate_exclusive(self):
        invalid_exclusives = []
        # incomplete_exclusives = []
        exclusive_traits = self.class_traits(
            exclusive_group=lambda t: t is not None
        )

        trait_groups = {
            k: [] for k in np.unique(list(
                t.get_metadata("exclusive_group")
                for t in exclusive_traits.values()
            ))
        }

        for n, t in exclusive_traits.items():
            trait_groups[t.get_metadata("exclusive_group")].append((n, t))

        for group, traits in trait_groups.items():
            trait_bundles = {
                k: [] for k in np.unique(
                    list(t[1].get_metadata("group_index", 0) for t in traits)
                )
            }
            for t in traits:
                trait_bundles[t[1].get_metadata("group_index", 0)].append(t[1])

            for k, t in trait_bundles.items():
                trait_bundles[k] = [
                    tt.get(self) != self.get_default_value(tt) for tt in t
                ]

            i = iter(
                any(t) for t in trait_bundles.values()
            )
            if not (any(i) and not any(i)):
                invalid_exclusives.append((group, traits))

            # if any(any(t) and not all(t) for t in trait_bundles.values()):
            #     incomplete_exclusives.append((group, traits))

        msg = ""
        if len(invalid_exclusives) > 0:
            msg += "{} got invalid exclusive groups :\n{}".format(
                self.__class__.__name__,
                "\n".join(indent(
                    "- {} : {}".format(g, list(tt[0] for tt in t)), 4
                ) for g, t in invalid_exclusives)
            ) + "\n"
        # if len(incomplete_exclusives):
        #     msg += "{} got incomplete exclusive groups :\n{}".format(
        #         self.__class__.__name__,
        #         "\n".join(indent(
        #             "- {} : {}".format(g, list(tt[0] for tt in t)), 4
        #         ) for g, t in incomplete_exclusives)
        #     ) + "\n"

        if len(msg) > 0:
            raise ArgumentError(msg.strip("\n"))

    @staticmethod
    def get_default_value(trait):
        if isinstance(trait, Instance):
            return trait.make_dynamic_default()
        else:
            return trait.get_default_value()

    @catch_config_error
    def initialize_subcommand(self, subc, argv=None):
        if argv is None or len(argv) == 0:
            argv = ["help"]
        super().initialize_subcommand(subc, argv)

    @catch_config_error
    def parse_command_line(self, argv=None):
        argv = sys.argv[1:] if argv is None else argv
        if len(argv) == 0:
            argv = ["help"]
        super().parse_command_line(argv)

    @catch_config_error
    def initialize(self, argv=None):
        aliases = deepcopy(base_aliases)
        flags = deepcopy(base_flags)

        aliases.update(self.aliases)
        aliases.update(self._config_aliases())
        self.aliases = aliases

        flags.update(self.flags)
        flags.update(self._config_flags())
        self.flags = flags

        if argv is None or (argv and "--safe" not in argv):
            super().initialize(argv)

        if self.subapp is not None:
            # stop here if sub-app is taking over
            return

        cl_config = deepcopy(self.config)
        self.load_config_file()
        # enforce cl-opts override configfile opts:
        self.update_config(cl_config)

    def start(self):
        if self.output_config:
            self._generate_config_file(self.output_config)
            return False
        else:
            self._validate()
            self.execute()
            return True

    def document_config_options(self):
        """Generate rST format documentation for the config options this application

        Returns a multiline string.
        """
        return '\n'.join(c.class_config_rst_doc()
                         for c in self._classes_inc_parents())

    @abstractmethod
    def execute(self):
        pass

    def _generate_config_file(self, filename):
        ConfigurationWriter().write_configuration_file(filename, self)

    @catch_config_error
    def _validate(self):
        self._validate_exclusive()
        self._shut_completed_exclusive()
        self._validate_required()
        self._validate_configuration()

    def _example_command(self, sub_command=""):
        return "magic_monkey {} <args> <flags>".format(sub_command)

    def print_options(self):
        if not self.flags and not self.aliases:
            return

        lines = ["Welcome To Magic Monkey"]

        if not self.subapp:
            lines[0] += " : {} sub-command".format(self.__class__.__name__)

        separator = '-' * 2 * len(lines[0])

        lines.append(separator)
        lines.insert(0, separator)
        lines.append('')

        if self.subapp:
            lines.append("command format : {}".format(
                self._example_command(self.parent.argv[0])
            ))
        else:
            lines.append("command format : {}".format(self._example_command()))

        lines.append('')

        for p in wrap_paragraphs(self.option_description):
            lines.append(p)
            lines.append('')

        lines.append(separator)
        lines.append(
            "Arguments | format : < --name <value> > or < --name=<value> > | :"
        )
        lines.append('')

        print(linesep.join(lines))
        lines.clear()

        self.print_alias_help()
        self.print_exclusive_groups()

        lines.append('')
        lines.append(separator)

        lines.append("Boolean flags | format : < --name > or <-c> | :")
        lines.append('')

        print(linesep.join(lines))
        lines.clear()

        self.print_flag_help()

        lines.append('')
        lines.append(separator)

        print(linesep.join(lines))

    def print_flag_help(self):
        """Print the flag part of the help."""
        if not self.flags:
            return

        lines, base_helps = [], []
        for m, (cfg, hlp) in self.flags.items():
            prefix = '--' if len(m) > 1 else '-'
            if m in base_flags.keys():
                base_helps.extend([prefix+m, indent(dedent(hlp.strip()))])
            else:
                lines.append(prefix+m)
                lines.append(indent(dedent(hlp.strip())))

        lines.extend(base_helps)

        print(linesep.join(lines))

    def print_alias_help(self):
        """Print the alias part of the help."""
        if not self.aliases:
            return

        aliases = self.aliases

        self._print_alias_category(aliases)

    def _print_alias_category(self, aliases, indentation=0):
        lines = []
        cd = self._get_class_dict()

        base_helps = []

        for alias, longname in aliases.items():
            try:
                trait, cls = self._trait_from_longname(cd, longname)
                if trait.name in [
                    al.split(".")[-1] for al in base_aliases.values()
                ]:
                    base_helps.append((alias, cls, trait, longname))
                else:
                    lines = self._trait_help(
                        alias, cls, trait, longname, lines
                    )
            except KeyError:
                pass

        for trait_args in base_helps:
            lines = self._trait_help(*trait_args, lines)

        print(linesep.join([
            indent(ln, indentation) for ln in linesep.join(sorted(
                lines, key=lambda k: "REQUIRED" in k, reverse=True
            )).splitlines()
        ]))

    @staticmethod
    def _trait_help(alias, cls, trait, longname, lines):
        hlp = cls.class_get_trait_help(trait)
        if hlp is not None:
            hlp = hlp.replace(longname, alias) + ' (%s)' % longname
            # reformat first line
            if len(alias) == 1:
                hlp = hlp.replace('--%s=' % alias, '-%s ' % alias)
            lines.append(linesep.join([hlp, ' ']))

        return lines

    def _get_class_dict(self):
        classdict = {}
        for cls in self.classes:
            # include all parents (up to, but excluding Configurable) in
            # available names
            for c in cls.mro()[:-3]:
                classdict[c.__name__] = c
        return classdict

    def print_exclusive_groups(self):
        alias_by_group = ListValuedDict()
        cd = self._get_class_dict()

        for alias, longname in self.aliases.items():
            try:
                trait, _ = self._trait_from_longname(cd, longname)

                if "exclusive_group" in trait.metadata:
                    alias_by_group[trait.metadata["exclusive_group"]].append(
                        (alias, longname)
                    )
                    trait.metadata.pop("exclusive_group")
            except KeyError:
                pass

        lines = []
        for group, aliases in alias_by_group.items():
            aliases_by_index = ListValuedDict({0: []})
            for alias, longname in aliases:
                trait, _ = self._trait_from_longname(cd, longname)

                if "group_index" in trait.metadata:
                    aliases_by_index[trait.metadata["group_index"]].append(
                        (alias, longname)
                    )
                else:
                    aliases_by_index[0].append(
                        (alias, longname)
                    )

            lines.append("> Exclusive group {} : ".format(group))
            lines.append('')
            print(linesep.join(lines))
            lines.clear()

            if len(list(aliases_by_index.values())) == 0:
                self._print_alias_category(aliases_by_index[0])
            else:
                for idx, opt_aliases in aliases_by_index.items():
                    lines.append(indent("> Option {} : ".format(idx), 2))
                    lines.append('')
                    print(linesep.join(lines))
                    lines.clear()

                    self._print_alias_category(dict(opt_aliases), 4)

    @staticmethod
    def _trait_from_longname(cd, longname):
        classname, trait_name = longname.split('.', 1)
        cls = cd[classname]
        trait = cls.class_traits(config=True)[trait_name]
        return trait, cls

    @classmethod
    def class_get_trait_help(cls, trait, inst=None):
        """Get the help string for a single trait.

        If `inst` is given, it's current trait values will be used in place of
        the class default.
        """
        assert inst is None or isinstance(inst, cls)

        if "exclusive_group" in trait.metadata:
            return None

        required = "required" in trait.metadata and trait.metadata["required"]

        lines = []

        if isinstance(trait, MultipleArguments):
            name = "{}<{}>".format(
                trait.__class__.__name__, trait.item_trait.__name__
            )
        elif isinstance(trait, ChoiceList):
            name = "{}<{}>".format(
                "Choices", trait.item_trait.__name__
            )
        else:
            name = trait.__class__.__name__

        header = "--{}.{}=<{}>".format(cls.__name__, trait.name, name)

        if required:
            header += " [ REQUIRED ]"

        lines.append(header)

        if inst is not None:
            lines.append(indent('Current: %r' % getattr(inst, trait.name), 4))
        else:
            try:
                dvr = trait.default_value_repr()
            except AttributeError:
                dvr = None  # ignore defaults we can't construct
            except TypeError:
                dvr = None  # ignore defaults we can't construct
            try:
                opt = trait.choices
            except AttributeError:
                opt = None  # ignore options we can't construct

            if not required and dvr is not None:
                if len(dvr) > 64:
                    dvr = dvr[:61] + '...'
                lines.append(indent('Default: %s' % dvr, 4))

            if opt is not None:
                opts_lines = split(opt, arange(5, len(opt), 5))
                if len(opts_lines) > 1:
                    lines.append(indent('Options: [', 4))
                    for opt_line in opts_lines:
                        lines.append(indent(",".join(
                            "'{}'".format(op) for op in opt_line
                        ) + ",", 8))
                    lines[-1] = lines[-1].rstrip(",")
                    lines.append(indent(']', 4))
                else:
                    lines.append(indent('Options: {}'.format(opt), 4))

        if 'Enum' in trait.__class__.__name__:
            # include Enum choices
            lines.append(indent('Choices: %r' % (trait.values,)))

        hlp = trait.help
        if hlp != '':
            hlp = '\n'.join(wrap_paragraphs(hlp, 76))
            lines.append(indent(hlp, 4))

        return '\n'.join(lines)

    def _config_aliases(self):
        aliases = {}
        for name, trait in self.traits().items():
            try:
                if isinstance(trait.get(self), MagicMonkeyConfigurable):
                    for alias, linked in trait.get(self).app_aliases.items():
                        aliases[alias] = linked
            except TraitError:
                pass

        return aliases

    def _config_flags(self):
        flags = {}
        for name, trait in self.traits().items():
            try:
                if isinstance(trait.get(self), MagicMonkeyConfigurable):
                    for flag, linked in trait.get(self).app_flags.items():
                        flags[flag] = linked
            except TraitError:
                pass

        return flags


def convert_enum(enum, default_value=None, allow_none=False):
    return Enum(
        [v.name for v in enum], default_value.name if default_value else None,
        allow_none=allow_none or default_value is None
    )


class Resolution(TraitType):
    default_value = (1200, 1200)

    def get(self, obj, cls=None):
        return super().get(obj, cls)

    def validate(self, obj, value):
        if value is not None:
            if isinstance(value, (list, tuple, np.array, np.ndarray)):
                if len(value) == 2:
                    return value

        if value is not None:
            self.error(obj, value)


class BoundedInt(Integer):
    info_text = ""

    def __init__(self, val, lb=None, hb=None, **kwargs):
        super().__init__(default_value=val, **kwargs)
        self.bounds = [lb if lb else -sys.maxsize, hb if hb else sys.maxsize]
        self.info_text = "between {} and {}".format(lb, hb)

    def validate(self, obj, value):
        value = super().validate(obj, value)
        between = self.bounds[0] and self.bounds[0] <= value
        between &= self.bounds[1] and self.bounds[1] >= value
        if not between:
            self.error(obj, value)

        return value


class MagicMonkeyConfigurable(Configurable):
    name = Unicode()
    app_aliases = Dict({})
    app_flags = Dict({})
    klass = Unicode().tag(config=True)

    @default('klass')
    def _klass_default(self):
        return ".".join([self.__module__, self.__class__.__name__])

    @abstractmethod
    def _validate(self):
        pass

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = self.__class__.__name__


    @catch_config_error
    def validate(self):
        self._validate()

        for name, trait in self.traits().items():
            value = trait.get(self)
            if isinstance(value, MagicMonkeyConfigurable):
                value.validate()
            elif isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, MagicMonkeyConfigurable):
                        item.validate()

    @abstractmethod
    def serialize(self, *args, **kwargs):
        pass

    def generate_config_file(self, filename):
        ConfigurationWriter().write_configuration_file(filename, self)

    @classmethod
    def class_config_section(cls):
        return ConfigurationWriter().class_config_section(cls)

    def _config_section(self):
        return ConfigurationWriter().config_section(
            self, MagicMonkeyConfigurable, False
        )

    def __str__(self):
        return self._config_section()

    def __repr__(self):
        return json.dumps({
            k: t.get(self) for k, t in self.traits(config=True).items()
        }, cls=MagicConfigEncoder, indent=4)


class DictInstantiatingInstance(Instance):
    def __init__(self, klass=None, allow_none=False, add_init=None, **kwargs):
        self._add_init = add_init
        if "args" not in kwargs and not allow_none:
            kwargs["args"] = ()
        super().__init__(klass, **{**kwargs, **{"allow_none": allow_none}})

    def validate(self, obj, value):
        if isinstance(value, dict):
            klass = value["klass"] if "klass" in value else self.klass
            if isinstance(klass, str):
                klass = klass.split(".")
                module, klass = ".".join(klass[:-1]), klass[-1]
                klass = getattr(import_module(module), klass)
            if self._add_init:
                value = {**self._add_init, **value}
            return klass(**value)
        elif value is None:
            if self.allow_none:
                return None
            try:
                return self.klass()
            except Exception:
                self.error(obj, value)

        return super().validate(obj, value)


class SelfInstantiatingInstance(DictInstantiatingInstance):
    def __init__(self, **kwargs):
        super().__init__(klass=self.__class__, **kwargs)


class AnyInt(Integer):
    def validate(self, obj, value):
        if isinstance(value, np.integer):
            return value

        return super().validate(obj, value)


class MultipleArguments(List):
    def __init__(self, trait, default_value=None, **kwargs):
        self.item_trait = trait
        super().__init__(trait=trait, default_value=default_value, **kwargs)

    def validate(self, obj, value):
        if isinstance(value, str):
            value = value.split(",")

        return super().validate(obj, value)


class ChoiceEnum(Enum):
    def __init__(self, values, **kwargs):
        super().__init__(values, **kwargs)

    def validate(self, obj, value):
        if "extra_choices" in self.metadata and self.metadata["extra_choices"]:
            self.values += self.metadata["extra_choices"]
            value = super().validate(obj, value)
            self.values = self.values[:-len(self.metadata["extra_choices"])]
        else:
            value = super().validate(obj, value)

        return value


class WorldBoundingBox(TraitType):
    default_value = None

    def get(self, obj, cls=None):
        value = super().get(obj, cls)

        if value is not None:
            return ",".join(str(v) for v in value)

        return value

    def validate(self, obj, value):
        if isinstance(value, tuple):
            if len(value) == 6:
                if all(isinstance(v, float) for v in value):
                    return value

        if isinstance(value, str):
            if len(value.split(",")) == 6:
                return value.split(",")

        if value is not None:
            self.error(obj, value)


class ChoiceList(List):
    def __init__(
        self, choices, trait=None, default_value=None,
        allow_all=False, minlen=0, maxlen=sys.maxsize, **kwargs
    ):
        self.choices = choices
        self._base_choices = ["all"] if allow_all else []

        if trait and isinstance(trait, type):
            trait = trait()
        if isinstance(trait, TraitType):
            trait.tag(extra_choices=self._base_choices)

        if trait:
            if isinstance(trait, Enum):
                try:
                    self.item_trait = type(trait.default_value)()
                except TypeError:
                    self.item_trait = Unicode
            else:
                self.item_trait = trait
        else:
            self.item_trait = Unicode

        super().__init__(
            trait=trait,
            default_value=default_value,
            minlen=minlen, maxlen=maxlen,
            **kwargs
        )

    def validate(self, obj, value):
        trait = self._trait if self._trait is type else type(self._trait)
        if isinstance(value, trait) \
           or isinstance(value, type(trait.default_value)) or (
                isinstance(value, str) and isinstance(self._trait, Enum)
        ):
            return super().validate(obj, self.klass(value.split(",")))

        return super().validate(obj, value)

    def validate_elements(self, obj, value):
        bad_choices = list(
            filter(lambda v: v not in self.choices + self._base_choices, value)
        )
        if len(bad_choices) > 0:
            raise TraitError(
                "Elements in list not in available choices : {}".format(
                    bad_choices
                )
            )

        return super().validate_elements(obj, value)

    def get(self, obj, cls=None):
        value = super().get(obj, cls)

        if "all" in value:
            return copy(self.choices)

        return value


class Vector3D(List):
    def __init__(self, **kwargs):
        super().__init__(trait=Float, minlen=3, maxlen=3, **kwargs)


_out_pre_help_line = "Output directory and prefix for files. Directory "\
                     "required, will overwrite files (Anything that can " \
                     "possibly go wrong, does - Murphy's Law)"

_out_suf_help_line = "Output suffix to append to file names."

_out_file_help_line = "Output filename (with extension, if absent, the file " \
                      "will be declared invalid). Will follow underlying " \
                      "application on overwriting default behavior, which " \
                      "is obliteration of previous data in case of python " \
                      "script from Magic Monkey codebase."

_dwi_pre_help_line = "Input DWI dataset prefix (for image/bval/bvec/metadata)"


_nthreads_help_line = "Number of threads used by the application. The " \
                      "default value is set by python, so it may be far " \
                      "from the actual available resources"


_mask_help_line = "Computing mask for the algorithm"


def input_dwi_prefix(
    default_value=Undefined, description=_dwi_pre_help_line,
    config=True, required=True, ignore_write=True, **tags
):
    return required_file(
        default_value, description, config, required, ignore_write, **tags
    )


def prefix_argument(
    description, default_value=Undefined, config=True,
    required=True, ignore_write=True, **tags
):
    return required_file(
        default_value, description, config, required, ignore_write, **tags
    )


def output_prefix_argument(
    default_value=Undefined, description=_out_pre_help_line,
    config=True, required=True, ignore_write=True, **tags
):
    return prefix_argument(
        description, default_value, config, required, ignore_write, **tags
    )


def output_suffix_argument(
    default_value=Undefined, description=_out_suf_help_line,
    config=True, required=True, ignore_write=True, **tags
):
    return required_file(
        default_value, description, config, required, ignore_write, **tags
    )


def output_file_argument(
    default_value=Undefined, description=_out_file_help_line,
    config=True, required=True, ignore_write=True, **tags
):
    valid = lambda val: len(str(splitext(val)).split(".")) > 0
    if "extra_valid" in tags:
        and_valid = deepcopy(tags["extra_valid"])
        valid = lambda val: valid(val) & and_valid(val)
        tags["extra_valid"] = valid

    return required_file(
        default_value, description, config, required, ignore_write, **tags
    )


def required_arg(
    trait, default_value=Undefined, description=None,
    config=True, required=True, ignore_write=True,
    traits_args=(), traits_kwargs=None, **tags
):
    if traits_kwargs is None:
        traits_kwargs = {}

    tags.update(dict(
        config=config, required=required, ignore_write=ignore_write
    ))
    return trait(
        *traits_args, default_value=default_value,
        help=description, **traits_kwargs
    ).tag(**tags)


def nthreads_arg(
    description=_nthreads_help_line,
    default_value=cpu_count(),
    config=True, **tags
):
    tags.update(dict(config=config))
    return Integer(default_value, help=description).tag(**tags)


def mask_arg(
    trait=Unicode, default_value=Undefined, description=_mask_help_line,
    config=True, required=False, ignore_write=True,
    traits_args=(), traits_kwargs=None, **tags
):

    return required_arg(
        trait, default_value, description, config, required,
        ignore_write, traits_args, traits_kwargs, **tags
    )


def affine_file(
    default_value=Undefined, config=True,
    required=True, ignore_write=True,
    **tags
):
    return required_file(
        default_value=default_value,
        config=config,
        required=required,
        ignore_write=ignore_write,
        description="4-D matrix file describing the affine of the "
                    "outputs, a txt as per numpy convention "
                    "(will be used to save the metrics files)",
        **tags
    )


def required_file(
    default_value=Undefined, description=None,
    config=True, required=True, ignore_write=True,
    **tags
):
    tags.update(dict(
        config=config, required=required, ignore_write=ignore_write
    ))

    return required_arg(
        Unicode, default_value=default_value, description=description
    ).tag(**tags)


def required_number(
    trait=Float, default_value=Undefined, description=None,
    config=True, required=True, ignore_write=True,
    **tags
):
    return required_arg(
        trait, default_value, description, config,
        required, ignore_write, **tags
    )

