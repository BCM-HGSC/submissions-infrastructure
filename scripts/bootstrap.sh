# Starting with just bash, bootstrap our infrastructure.

set -Eeuo pipefail

main() {
    ensure_conda
    # echo params: "$@"

    parse_params "$@"
    setup_colors

    trap cleanup SIGINT SIGTERM ERR EXIT

    # script logic here

    msg "${RED}Read parameters:${NOFORMAT}"
    msg "- force: ${force}"
    msg "- target_dir: ${target_dir}"
}

usage() {
    cat << EOF
Usage: $(basename "${BASH_SOURCE[0]}") [-h] [-v] [--force] TARGET_DIR

Create TARGET_DIR if it does not already exist, and populated it with  a
subdirectory named "conda_package_cache" and another subdirectory named
"infrastructure". It is an error if "infrastructure" already exists unless
the --force option is applied.

Available options:

-h, --help      Print this help and exit
-v, --verbose   Print script debug info
--force         Force overwriting existing infrastructure!
EOF
    exit
}

parse_params() {
    # Set force and target_dir.

    # default values of variables set from params
    force=

    while :; do
        case "${1-}" in
            -h | --help) usage ;;
            -v | --verbose) set -x ;;
            --no-color) NO_COLOR=1 ;;
            --force) force=1 ;;
            -p | --param) # example named parameter
                [[ $# -gt 1 ]] || die "missing value for -p"
                param="${2-}"
                shift
                ;;
            -?*) die "Unknown option: $1" ;;
            *) break ;;
        esac
        shift
    done

    [[ $# -eq 0 ]] && die "missing value for TARGET_DIR"
    target_dir="$1"
    shift

    [[ $# -eq 0 ]] || die "unused positional parameters: $@"

    return 0
}

ensure_conda() {
    if [[ ! -x ${CONDA-} ]]; then
        CONDA=$(which conda)
    fi

    if [[ ! -x $CONDA ]]; then
        # What do you do when you have no conda?
        # What do you do when you have no conda?
        # What do you do when you have no conda?
        # Fetch it from the server!
        msg fetch conda!!!
    fi
}

cleanup() {
    trap - SIGINT SIGTERM ERR EXIT
    # script cleanup here
    msg ${BLUE}CLEANUP
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
