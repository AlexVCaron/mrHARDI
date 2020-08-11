import sys
from abc import abstractmethod
from multiprocessing import cpu_count
from os.path import splitext
from typing import Generator
from os import chdir, getcwd, linesep

import nibabel as nib
import numpy as np
from numpy import split, arange, ones, loadtxt, zeros, absolute, ubyte, \
    apply_along_axis, arccos, cross, cos, unique
from scipy.spatial.transform import Rotation

from traitlets import Integer, Undefined, Unicode, Float
from traitlets.config import Application, Unicode, logging, observe, List, \
    default, deepcopy, catch_config_error, indent, wrap_paragraphs, \
    ArgumentError, Instance, Enum, Configurable, Dict, TraitError, Bool, \
    observe_compat, dedent

from magic_monkey.base.ListValuedDict import ListValuedDict

base_aliases = {
    'config': 'MagicMonkeyBaseApplication.base_config_file',
    'out-config': 'MagicMonkeyBaseApplication.output_config'
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

    output_config = Unicode().tag(config=True, ignore_write=True)

    current_config = Unicode()

    required = List()

    @default('config_files')
    def _config_files_default(self):
        return [self.current_config]

    config_file_paths = List(Unicode, [])

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
        if MagicMonkeyConfigurable in (conf_klass,) + conf_klass.__bases__:
            try:
                self.configuration = conf_klass(parent=self)
                self.classes.extend((conf_klass,) + conf_klass.__bases__)
            except AttributeError:
                pass
        super().__init__(**kwargs)

    def load_config_file(self):
        Application.load_config_file(
            self, self.base_config_file, path=self.config_file_paths
        )

        for file_name in self.config_files:
            if not file_name or file_name == self.base_config_file:
                continue

            Application.load_config_file(
                self, file_name, path=self.config_file_paths
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
                    tt.get(self) != self.get_default_value(tt) for tt in t
                ]

            if any(all(t) for t in traits_bools.values()):
                for _, traits in filter(
                    lambda kv: not all(traits_bools[kv[0]]),
                    trait_bundles.items()
                ):
                    for trait in traits:
                        trait.tag(required=False)

    @catch_config_error
    def _validate_configuration(self):
        if self.configuration:
            config = self.traits()["configuration"]
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
        incomplete_exclusives = []
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
                all(t) for t in trait_bundles.values()
            )
            if not (any(i) and not any(i)):
                invalid_exclusives.append((group, traits))

            if any(any(t) and not all(t) for t in trait_bundles.values()):
                incomplete_exclusives.append((group, traits))

        msg = ""
        if len(invalid_exclusives) > 0:
            msg += "{} got invalid exclusive groups :\n{}".format(
                self.__class__.__name__,
                "\n".join(indent(
                    "- {} : {}".format(g, list(tt[0] for tt in t)), 4
                ) for g, t in invalid_exclusives)
            ) + "\n"
        if len(incomplete_exclusives):
            msg += "{} got incomplete exclusive groups :\n{}".format(
                self.__class__.__name__,
                "\n".join(indent(
                    "- {} : {}".format(g, list(tt[0] for tt in t)), 4
                ) for g, t in incomplete_exclusives)
            ) + "\n"

        if len(msg) > 0:
            raise ArgumentError(msg.strip("\n"))

    def get_default_value(self, trait):
        if isinstance(trait, Instance):
            return trait.make_dynamic_default()
        else:
            return trait.get_default_value()

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

        super().initialize(argv)

        if self.subapp is not None:
            # stop here if subapp is taking over
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
            self._start()
            return True

    @abstractmethod
    def _start(self):
        pass

    def _generate_config_file(self, filename):
        traits = self.class_traits(ignore_write=True)
        for k in traits.keys():
            for klass in (self.__class__,) + self.__class__.__bases__:
                try:
                    delattr(klass, k)
                except AttributeError:
                    pass
        with open(filename, 'w+') as f:
            f.writelines([
                "# Configuration file for %s.\n" % self.name,
                self._config_section()
            ])

    def _config_section(self):
        """Get the config class config section"""

        def c(s):
            """return a commented, wrapped block."""
            s = '\n\n'.join(wrap_paragraphs(s, 78))

            return '## ' + s.replace('\n', '\n#  ')

        # section header
        klass = self.__class__
        breaker = '#' + '-' * 78
        parent_classes = ','.join(p.__name__ for p in klass.__bases__)
        s = "# %s(%s) configuration" % (klass.__name__, parent_classes)
        lines = [breaker, s, breaker, '']
        # get the description trait
        desc = klass.class_traits().get('description')
        if desc:
            desc = desc.default_value
        if not desc:
            # no description from trait, use __doc__
            desc = getattr(klass, '__doc__', '')
        if desc:
            lines.append(c(desc))
            lines.append('')

        sub_configurables = []

        for name, trait in sorted(self.traits(
            config=True, ignore_write=None, required=None
        ).items()):
            inst = trait.get(self, klass)
            if isinstance(inst, MagicMonkeyConfigurable):
                sub_configurables.append(inst)
            else:
                lines.append('c.%s.%s = %s' % (
                    klass.__name__,
                    name,
                    '"%s"' % inst if isinstance(inst, str) else inst
                ))
            lines.append('')

        for s_conf in sub_configurables:
            lines.append('%s' % s_conf)
            lines.append('')

        return '\n'.join(lines)

    @catch_config_error
    def _validate(self):
        self._validate_exclusive()
        self._shut_completed_exclusive()
        self._validate_required()
        self._validate_configuration()

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
        for m, (cfg, help) in self.flags.items():
            prefix = '--' if len(m) > 1 else '-'
            if m in base_flags.keys():
                base_helps.extend([prefix+m, indent(dedent(help.strip()))])
            else:
                lines.append(prefix+m)
                lines.append(indent(dedent(help.strip())))

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
            trait, cls = self._trait_from_longname(cd, longname)
            if trait.name in [
                al.split(".")[-1] for al in base_aliases.values()
            ]:
                base_helps.append((alias, cls, trait, longname))
            else:
                lines = self._trait_help(alias, cls, trait, longname, lines)

        for trait_args in base_helps:
            lines = self._trait_help(*trait_args, lines)

        print(linesep.join([
            indent(ln, indentation) for ln in linesep.join(sorted(
                lines, key=lambda k: "REQUIRED" in k, reverse=True
            )).splitlines()
        ]))

    def _trait_help(self, alias, cls, trait, longname, lines):
        help = cls.class_get_trait_help(trait)
        if help is not None:
            help = help.replace(longname, alias) + ' (%s)' % longname
            # reformat first line
            if len(alias) == 1:
                help = help.replace('--%s=' % alias, '-%s ' % alias)
            lines.append(linesep.join([help, ' ']))

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
            trait, _ = self._trait_from_longname(cd, longname)

            if "exclusive_group" in trait.metadata:
                alias_by_group[trait.metadata["exclusive_group"]].append(
                    (alias, longname)
                )
                trait.metadata.pop("exclusive_group")

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

    def _trait_from_longname(self, cd, longname):
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
            except Exception:
                dvr = None  # ignore defaults we can't construct
            try:
                opt = trait.choices
            except Exception:
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

        help = trait.help
        if help != '':
            help = '\n'.join(wrap_paragraphs(help, 76))
            lines.append(indent(help, 4))

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


def convert_enum(enum, default_value):
    return Enum(
        [v.name for v in enum], default_value.name
    )


class BoundedInt(Integer):
    info_text = ""

    def __init__(self, val, lb=None, hb=None, **kwargs):
        super().__init__(default_value=val, **kwargs)
        self.bounds = [lb, hb]
        self.info_text = "between {} and {}".format(lb, hb)

    def validate(self, obj, value):
        value = super().validate(obj, value)
        between = self.bounds[0] and self.bounds[0] <= value
        between &= self.bounds[1] and self.bounds[1] >= value
        if not between:
            self.error(obj, value)

        return value


class MagicMonkeyConfigurable(Configurable):
    app_aliases = Dict({})
    app_flags = Dict({})

    @abstractmethod
    def validate(self):
        pass

    @abstractmethod
    def serialize(self):
        pass

    @classmethod
    def class_config_section(cls):
        """Get the config class config section"""

        def c(s):
            """return a commented, wrapped block."""
            s = '\n\n'.join(wrap_paragraphs(s, 78))

            return '## ' + s.replace('\n', '\n#  ')

        # section header
        breaker = '#' + '-' * 78
        parent_classes = ','.join(p.__name__ for p in cls.__bases__)
        s = "# %s(%s) configuration" % (cls.__name__, parent_classes)
        lines = [breaker, s, breaker, '']
        # get the description trait
        desc = cls.class_traits().get('description')
        if desc:
            desc = desc.default_value
        if not desc:
            # no description from trait, use __doc__
            desc = getattr(cls, '__doc__', '')
        if desc:
            lines.append(c(desc))
            lines.append('')

        for name, trait in sorted(cls.class_own_traits(config=True).items()):
            lines.append('c.%s.%s = %s' % (
                cls.__name__, name, trait.default_value_repr()
            ))
            lines.append('')
        return '\n'.join(lines)

    def _config_section(self):
        """Get the config class config section"""

        def c(s):
            """return a commented, wrapped block."""
            s = '\n\n'.join(wrap_paragraphs(s, 78))

            return '## ' + s.replace('\n', '\n#  ')

        # section header
        klass = self.__class__
        breaker = '#' + '-' * 78
        parent_classes = ','.join(p.__name__ for p in klass.__bases__)
        s = "# %s(%s) configuration" % (klass.__name__, parent_classes)
        lines = [breaker, s, breaker, '']
        # get the description trait
        desc = klass.class_traits().get('description')
        if desc:
            desc = desc.default_value
        if not desc:
            # no description from trait, use __doc__
            desc = getattr(klass, '__doc__', '')
        if desc:
            lines.append(c(desc))
            lines.append('')

        for name, trait in sorted(self.traits(
            config=True, ignore_write=None, required=None
        ).items()):
            inst = trait.get(self, klass)
            if isinstance(inst, MagicMonkeyConfigurable):
                lines.append('%s' % inst)
            else:
                lines.append('c.%s.%s = %s' % (
                    klass.__name__,
                    name,
                    '"%s"' % inst if isinstance(inst, str) else inst
                ))
            lines.append('')
        return '\n'.join(lines)

    def __str__(self):
        return self._config_section()


class DictInstantiatingInstance(Instance):
    def __init__(self, klass, **kwargs):
        super().__init__(klass, **kwargs)

    def validate(self, obj, value):
        if isinstance(value, dict):
            return self.klass(**value)
        elif value is None:
            try:
                try:
                    return self.klass()
                except BaseException:
                    if self.allow_none:
                        return None
                    self.error(obj, value)
            except BaseException:
                self.error(obj, value)

        return super().validate(obj, value)


class SelfInstantiatingInstance(DictInstantiatingInstance):
    def __init__(self, **kwargs):
        super().__init__(klass=self.__class__, **kwargs)


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


class ChoiceList(List):
    def __init__(
        self, choices, trait=None, default_value=None,
        minlen=0, maxlen=sys.maxsize, **kwargs
    ):
        self.choices = choices
        self._base_choices = ["all"]

        if trait and trait is not type:
            trait = trait(extra_choices=self._base_choices)

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


def load_from_cache(cache, keys, alternative=None):
    keys = keys if isinstance(keys, (list, tuple, Generator)) else [keys]
    sub_cache = cache
    try:
        for key in keys:
            sub_cache = sub_cache[key]
        return sub_cache
    except KeyError as e:
        if alternative:
            sub_cache[e.args[0]] = alternative(e.args[0])
            sub_cache = sub_cache[e.args[0]]
        else:
            return None

    return sub_cache


def get_from_metric_cache(keys, metric):
    metric.measure()
    cache = metric.cache
    for key in keys:
        cache = cache[key]
    return cache


def _load_mask(path, shape):
    try:
        return nib.load(path).get_fdata().astype(bool)
    except BaseException:
        return ones(shape)


class BaseMetric:
    def __init__(
        self, prefix, output, cache, affine, mask=None,
        shape=None, colors=False, **kwargs
    ):
        self.prefix = prefix
        self.output = output
        self.cache = cache
        self.affine = affine
        self.mask = mask
        self.shape = shape
        self.colors = colors

    def load_from_cache(self, key, alternative=None):
        return load_from_cache(self.cache, key, alternative)

    def _get_shape(self):
        return self.shape

    def get_mask(self, add_keys=()):
        if self.mask is not None:
            return self.mask

        return self.load_from_cache(
            add_keys + ("mask",),
            lambda _: _load_mask(
                "{}_mask.nii.gz".format(self.prefix), self._get_shape()
            )
        )

    def _get_bvecs(self, add_keys=()):
        return load_from_cache(
            self.cache,
            add_keys + ("bvecs",),
            lambda f: loadtxt("{}.bvecs".format(self.prefix))
        )

    def _get_bvals(self, add_keys=()):
        return load_from_cache(
            self.cache,
            add_keys + ("bvals",),
            lambda f: loadtxt("{}.bvals".format(self.prefix))
        )

    def _color(self, name, evecs, add_keys=()):
        if self.colors:
            self._color_metric(name, evecs, add_keys)

    def _color_metric(self, name, evecs, add_keys=(), prefix=""):
        cname = "color_{}".format(name)
        if prefix:
            cname = "_".join([prefix, cname])
            name = "_".join([prefix, name])

        mask = self.get_mask()
        metric = self.load_from_cache(add_keys + (name,))
        cmetric = zeros(self._get_shape() + (3,))

        cmetric[mask] = absolute(metric[mask, None] * evecs[mask, 0, :])
        self.cache[cname] = cmetric

        nib.save(
            nib.Nifti1Image(
                (cmetric * 255.).astype(ubyte),
                self.affine
            ),
            "{}_{}.nii.gz".format(self.output, cname)
        )

    @abstractmethod
    def measure(self):
        pass


_out_pre_help_line = "Output directory and prefix for files. Directory "\
                     "required, will overwrite files (Anything that can " \
                     "possibly go wrong, does - Murphy's Law)"


_out_file_help_line = "Output filename (with extension, if absent, the file " \
                      "will be declared invalid). Will follow underlying " \
                      "application on overwriting default behavior, which " \
                      "is obliteration of previous data in case of python " \
                      "script from Magic Monkey codebase."


_nthreads_help_line = "Number of threads used by the application. The " \
                      "default value is set by python, so it may be far " \
                      "from the actual available resources"


_mask_help_line = "Computing mask for the algorithm"


def output_prefix_argument(
    default_value=Undefined, help=_out_pre_help_line,
    config=True, required=True, ignore_write=True, **tags
):
    return required_file(
        default_value, help, config, required, ignore_write, **tags
    )


def output_file_argument(
    default_value=Undefined, help=_out_file_help_line,
    config=True, required=True, ignore_write=True, **tags
):
    valid = lambda val: len(str(splitext(val)).split(".")) > 0
    if "extra_valid" in tags:
        and_valid = deepcopy(tags["extra_valid"])
        valid = lambda val: valid(val) & and_valid(val)
        tags["extra_valid"] = valid

    return required_file(
        default_value, help, config, required, ignore_write, **tags
    )


def required_arg(
    trait, default_value=None, help=None,
    config=True, required=True, ignore_write=True,
    traits_args=(), traits_kwargs=None, **tags
):
    if traits_kwargs is None:
        traits_kwargs = {}

    tags.update(dict(
        config=config, required=required, ignore_write=ignore_write
    ))
    return trait(
        *traits_args, default_value=default_value, help=help, **traits_kwargs
    ).tag(**tags)


def nthreads_arg(help=_nthreads_help_line, config=True, **tags):
    tags.update(dict(config=config))
    return Integer(cpu_count(), help=help).tag(**tags)


def mask_arg(
    trait=Unicode, default_value=Undefined, help=_mask_help_line,
    config=True, required=False, ignore_write=True,
    traits_args=(), traits_kwargs=None, **tags
):

    return required_arg(
        trait, default_value, help, config, required,
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
        help="4-D matrix file describing the affine of the "
             "outputs, a txt as per numpy convention "
             "(will be used to save the metrics files)",
        **tags
    )


def required_file(
    default_value=Undefined, help=None,
    config=True, required=True, ignore_write=True,
    **tags
):
    tags.update(dict(
        config=config, required=required, ignore_write=ignore_write
    ))

    return required_arg(
        Unicode, default_value=default_value, help=help
    ).tag(**tags)


def required_number(
    trait=Float, default_value=Undefined, help=None,
    config=True, required=True, ignore_write=True,
    **tags
):
    return required_arg(
        trait, default_value, help, config, required, ignore_write, **tags
    )

