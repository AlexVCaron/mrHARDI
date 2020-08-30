#!/usr/bin/env python

from os.path import join, dirname, abspath
import inspect

from magic_monkey.base.application import MagicMonkeyConfigurable
from magic_monkey.main_app import MagicMonkeyApplication
from traitlets import Instance, Undefined, import_item
from collections import defaultdict

here = abspath(dirname(__file__))
options = join(here, 'source', 'config', 'options')
generated = join(options, 'config-generated.txt')

import textwrap
indent = lambda text,n: textwrap.indent(text,n*' ')


def interesting_default_value(dv):
    if (dv is None) or (dv is Undefined):
        return False
    if isinstance(dv, (str, list, tuple, dict, set)):
        return bool(dv)
    return True


def format_aliases(aliases):
    fmted = []
    for a in aliases:
        dashes = '-' if len(a) == 1 else '--'
        fmted.append('``%s%s``' % (dashes, a))
    return ', '.join(fmted)


def class_config_rst_doc(
    cls, trait_aliases, include_parents=True, whole_traits=False
):
    """Generate rST documentation for this class' config options.

    Excludes traits defined on parent classes.
    """
    lines = []
    remaining_configurables = []
    classname = cls.__name__

    metadata = dict() if whole_traits else dict(config=True)

    if include_parents:
        traits = cls.class_traits(**metadata)
    else:
        traits = cls.class_own_traits(**metadata)

    for k, trait in sorted(traits.items()):
        ttype = trait.__class__.__name__

        fullname = classname + '.' + trait.name
        lines += ['.. configtrait:: ' + fullname,
                  ''
                 ]

        if isinstance(trait, Instance) and \
                isinstance(trait.klass(), MagicMonkeyConfigurable):
            help = (
                "Trait holding further configuration for the application. "
                "See :doc:`/config/options/{}{}` for further details".format(
                    cls.__name__.lower(), trait.name
                )
            )
            lines.append(indent(inspect.cleandoc(help), 4) + '\n')
            remaining_configurables.append(trait)
        else:
            help = trait.help.rstrip() or 'No description'
            lines.append(indent(inspect.cleandoc(help), 4) + '\n')

            # Choices or type
            if 'Enum' in ttype:
                # include Enum choices
                lines.append(indent(
                    ':options: ' + ', '.join('``%r``' % x for x in trait.values), 4))
            else:
                lines.append(indent(':trait type: ' + ttype, 4))

            # Default value
            # Ignore boring default values like None, [] or ''
            if interesting_default_value(trait.default_value):
                try:
                    dvr = trait.default_value_repr()
                except Exception:
                    dvr = None  # ignore defaults we can't construct
                if dvr is not None:
                    if len(dvr) > 64:
                        dvr = dvr[:61] + '...'
                    # Double up backslashes, so they get to the rendered docs
                    dvr = dvr.replace('\\n', '\\\\n')
                    lines.append(indent(':default: ``%s``' % dvr, 4))

            # Command line aliases
            if trait_aliases[fullname]:
                fmt_aliases = format_aliases(trait_aliases[fullname])
                lines.append(indent(':CLI option: ' + fmt_aliases, 4))

            # Blank line
            lines.append('')

    return '\n'.join(lines), remaining_configurables


def reverse_aliases(app):
    """Produce a mapping of trait names to lists of command line aliases.
    """
    res = defaultdict(list)
    for alias, trait in app.aliases.items():
        res[trait].append(alias)

    # Flags also often act as aliases for a boolean trait.
    # Treat flags which set one trait to True as aliases.
    for flag, (cfg, _) in app.flags.items():
        if len(cfg) == 1:
            classname = list(cfg)[0]
            cls_cfg = cfg[classname]
            if len(cls_cfg) == 1:
                traitname = list(cls_cfg)[0]
                if cls_cfg[traitname] is True:
                    res[classname+'.'+traitname].append(flag)

    return res


def write_doc(name, title, item, aliases, preamble=None, parents=True):
    filename = join(options, name + '.rst')
    rm = []
    with open(filename, 'w') as f:
        f.write(title + '\n')
        f.write(('=' * len(title)) + '\n')
        f.write('\n')
        if preamble is not None:
            f.write(preamble + '\n\n')
        #f.write(app.document_config_options())

        if parents:
            for c in item._classes_inc_parents():
                s, rme = class_config_rst_doc(c, aliases, parents)
                f.write(s)
                f.write('\n')
                rm.extend(rme)
        else:
            s, rm = class_config_rst_doc(item.__class__, aliases, parents)
            f.write(s)
            f.write('\n')

    conf_opts = ["{}{}".format(name, r.name) for r in rm]

    for r in rm:
        conf_opts.extend(write_doc(
            "{}{}".format(name, r.name),
            "{} holder for {}".format(r.name.capitalize(), name.capitalize()),
            r.klass(), aliases, parents=parents
        ))

    return conf_opts


_index_header = """
====================
Magic Monkey options
====================

Any of the options listed here can be set in config files, at the
command line, or from inside Magic Monkey. See :ref:`setting_config` for
details.
"""

_spec_descr = """
The following configuration options are specific to each sub-application
"""

_glob_descr = """
The configuration options below apply to all applications
"""

_conf_descr = """
Some application have additional configuration options. Those are listed here
"""

def write_options_index(specific_opts=(), global_opts=(), conf_opts=()):
    lines = [_index_header, '', _spec_descr, '', ".. toctree::"]
    lines.extend("   {}\n".format(opt) for opt in specific_opts)
    lines.extend(['', _glob_descr, '', ".. toctree::"])
    lines.extend("   {}\n".format(opt) for opt in global_opts)
    lines.extend(['', _conf_descr, '', ".. toctree::"])
    lines.extend("   {}\n".format(opt) for opt in conf_opts)
    with open(join(options, "index.rst"), "w+") as f:
        f.write("\n".join(lines))


if __name__ == '__main__':
    # Touch this file for the make target
    with open(generated, 'w'):
        pass

    write_doc(
        'main_app', 'Magic Monkey base options',
        MagicMonkeyApplication.instance(),
        reverse_aliases(MagicMonkeyApplication.instance()),
        parents=False
    )

    MagicMonkeyApplication.clear_instance()

    spec_opts, conf_opts = [], []
    for name, command in MagicMonkeyApplication.subcommands.items():
        klass = import_item(command[0])

        conf_opts.extend(write_doc(
            klass.__name__.lower(),
            '{} sub-command options'.format(klass.__name__),
            klass.instance(), reverse_aliases(klass.instance()),
            preamble=command[1], parents=False
        ))

        klass.clear_instance()
        spec_opts.append(klass.__name__.lower())

    write_options_index(spec_opts, ['main_app'], conf_opts)
