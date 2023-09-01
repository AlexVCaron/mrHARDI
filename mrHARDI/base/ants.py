

BASE_SCRIPT="""
#!/usr/bin/env bash

VERBOSE=0
INTERP="Linear"
DTYPE="default"
IN_DTYPE=0
INTERP_TRANSFORM_LIST=("Linear" "NearestNeighbor" "BSpline" "MultiLabel" "GenericLabel")
ANTS_DTYPES=("char" "uchar" "short" "int" "float" "double" "default")
IN_DTYPES=("0" "1" "2" "3" "4" "5")

USAGE=$(cat <<-END

    Usage: $0 [options] <input> <output>

    Options:

        -h : Show this message
        -v : Verbose

        -i <interp> : Interpolation method (default: $INTERP)

            Methods : ${INTERP_TRANSFORM_LIST[@]}

        -u <dtype> : Output data type (default: $DTYPE)

            Data types : ${ANTS_DTYPES[@]}

        -e <dtype> : Input data type (default: $IN_DTYPE)

            Data types : ${IN_DTYPES[@]}

END
)

while getopts "i:u:e:hv" opt; do
    case $opt in
        i)
            INTERP="$OPTARG"
            ;;
        u)
            DTYPE="$OPTARG"
            ;;
        e)
            IN_DTYPE="$OPTARG"
            ;;
        v)
            VERBOSE=1
            ;;
        h)
            echo "$USAGE"
            exit 0
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            echo "$USAGE"
            exit 1
            ;;
        :)
            echo "Option -$OPTARG requires an argument." >&2
            echo "$USAGE"
            exit 1
            ;;
    esac
done

shift $((OPTIND-1))

if [ $# -ne 2 ]; then
    echo "Invalid number of arguments" >&2
    echo "$USAGE"
    exit 1
fi

IN_DATA="$1"
OUT_DATA="$2"

if [[ ! " ${INTERP_TRANSFORM_LIST[@]} " =~ " ${INTERP} " ]]; then
    echo "Invalid interpolation method: $INTERP" >&2
    echo "$USAGE"
    exit 1
fi

if [[ ! " ${ANTS_DTYPES[@]} " =~ " ${DTYPE} " ]]; then
    echo "Invalid output data type: $DTYPE" >&2
    echo "$USAGE"
    exit 1
fi

if [[ ! " ${IN_DTYPES[@]} " =~ " ${IN_DTYPE} " ]]; then
    echo "Invalid input data type: $IN_DTYPE" >&2
    echo "$USAGE"
    exit 1
fi

"""


def create_ants_transform_script(reference, transforms, inverts):
    def _t_param(_t, _i):
        if _i:
            return "-t [{},1]".format(_t)

        return "-t {}".format(_t)

    trans_params = " ".join([
        _t_param(t, i) for t, i in zip(transforms[::-1], inverts[::-1])
    ])

    static_params = "-d 3"
    script_params = "-i $IN_DATA -o $OUT_DATA -e $IN_DTYPE"
    script_params += " -n $INTERP -u $DTYPE -v $VERBOSE"
    set_params = "-r {reference} {transforms}".format(
        reference=reference,
        transforms=trans_params
    )

    cmd = "antsApplyTransforms {static} {set} {script}".format(
        static=static_params,
        script=script_params,
        set=set_params
    )

    return "{}\n{}\nexit 0\n".format(BASE_SCRIPT, cmd)
