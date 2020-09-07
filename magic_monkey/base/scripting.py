

_args_template = """
POSITIONAL=()
while [ $# -gt 0 ]
do
    key=\"$1\"
    case $key in
        {}
    *)
        POSITIONAL+=(\"$2\")
        shift
        ;;
    esac
    shift
done
"""

_named_template = """
        {})
            {}=\"$2\"
            shift
            shift
            ;;
"""


def build_script(
    script, positional_args, named_args, named_prefix="--", header=""
):
    print(positional_args)
    print(named_args)
    scr = "#!/usr/bin/env bash\n\n"
    scr += header
    scr += _args_template.format("\n".join(
        _named_template.format(named_prefix + arg, arg.upper())
        for arg in named_args
    ))
    for i, arg in enumerate(positional_args):
        scr += "{}=".format(arg) + "\"${POSITIONAL[" + str(i) + "]}\"\n"

    return scr + script
