# Starting with just bash, bootstrap our infrastructure.

set -Eeuo pipefail

main() {
    parse_params "$@"
    setup_colors

    trap cleanup SIGINT SIGTERM ERR EXIT

    if [[ -n $verbose ]]; then
        set -x
    fi

    msg "${BLUE}Read parameters:${NOFORMAT}"
    msg "- force: ${force}"
    msg "- target_dir: ${target_dir}"
    msg

    # script logic here

    setup_temp

    ensure_conda
    msg "Haz conda?"
}

usage() {
    cat << EOF
Usage: $(basename "${BASH_SOURCE[0]}") [-h] [-v] [--force] TARGET_DIR

Create TARGET_DIR if it does not already exist, and populated it with  a
subdirectory named "conda_package_cache" and another subdirectory named
"infrastructure". It is an error if "infrastructure" already exists unless
the --force option is applied.

Available options:

-h, --help      Print this help and exit.
-v, --verbose   Print script debug info.
--no-color      Turn off color output.
--force         Force overwriting existing infrastructure!
EOF
    exit
}

parse_params() {
    # Set force and target_dir.

    # default values of variables set from params
    force=
    verbose=

    while :; do
        case "${1-}" in
            -h | --help) usage ;;
            -v | --verbose) verbose=y ;;
            --no-color) NO_COLOR=y ;;
            --force) force=1 ;;
            -?*) die "Unknown option: $1 (-h for help)" ;;
            *) break ;;
        esac
        shift
    done

    [[ $# -eq 0 ]] && die "missing value for TARGET_DIR (-h for help)"
    target_dir="$1"
    shift

    [[ $# -eq 0 ]] || die "unused positional parameters: $@ (-h for help)"

    return 0
}

setup_temp() {
    tmp_root=$(dirname $(mktemp -u))
    echo "tmp_root=$tmp_root"
    user_root=$tmp_root/$USER
    echo "user_root=$user_root"
    mkdir -p $user_root
    template=$tmp_root/$USER/$(date +%Y-%m-%d)-XXXX
    my_tmp_dir=$(mktemp -d $template)
    echo "my_tmp_dir=$my_tmp_dir"
    cd $my_tmp_dir
}

ensure_conda() {
    echo hello
    if [[ ! -x ${CONDA-} ]]; then
        CONDA=$(which conda) || msg "No conda in PATH."
    fi

    echo foo

    if [[ ! -x $CONDA ]]; then
        # What do you do when you have no conda?
        # What do you do when you have no conda?
        # What do you do when you have no conda?
        # Fetch it from the server!
        msg "fetch conda!!!"
    fi
}

cleanup() {
    trap - SIGINT SIGTERM ERR EXIT
    # script cleanup here
    cd
    msg ${BLUE}CLEANUP${NOFORMAT}
    msg "rm -rf $user_root"
    rm -rf "$user_root"
    msg ${BLUE}DONE${NOFORMAT}
}

msg() {
    echo >&2 -e "${1-}"
}

die() {
    local msg=$1
    local code=${2-1} # default exit status 1
    msg "$msg"
    exit "$code"
}

setup_colors() {
    if [[ -t 2 ]] && [[ -z "${NO_COLOR-}" ]] && [[ "${TERM-}" != "dumb" ]]; then
        NOFORMAT='\033[0m' RED='\033[0;31m' GREEN='\033[0;32m' ORANGE='\033[0;33m' BLUE='\033[0;34m' PURPLE='\033[0;35m' CYAN='\033[0;36m' YELLOW='\033[1;33m'
    else
        NOFORMAT='' RED='' GREEN='' ORANGE='' BLUE='' PURPLE='' CYAN='' YELLOW=''
    fi
}

main "$@"
