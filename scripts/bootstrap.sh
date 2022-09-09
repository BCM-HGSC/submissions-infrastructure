# Starting with just bash, bootstrap our infrastructure.

set -Eeuo pipefail

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

main() {
    setup_colors
    parse_params "$@"
    setup_colors

    trap cleanup SIGINT SIGTERM ERR EXIT

    if [[ $verbose == 'yy' ]]; then
        set -x
    fi

    msg "${BLUE}Read parameters:${NOFORMAT}"
    dump_var verbose '- ' y
    dump_var force '- ' y
    dump_var target_dir '- '
    msg

    script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd -P)
    dump_var script_dir

    # script logic here

    mkdir -p "$target_dir"
    resolved_target=$(cd -P "$target_dir"; pwd)
    dump_var resolved_target

    setup_target

    ensure_conda
} >&2

parse_params() {
    # Set force and target_dir.

    # default values of variables set from params
    force=
    verbose=

    while :; do
        case "${1-}" in
            -h | --help) usage ;;
            -v | --verbose) verbose=${verbose}y ;;
            --no-color) NO_COLOR=y ;;
            --force) force=y ;;
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

setup_target() {
    cd "$resolved_target"
    if [[ -e infrastructure ]]; then
        if [[ -z $force ]]; then
            die "$target_dir/infrastructure already exists"
        else
            msg "overwriting $resolved_target/infrastructure"
            rm -rf infrastructure
        fi
    fi
    mkdir -p conda_package_cache infrastructure user_envs
    if ! ls -ld $resolved_target/condarc; then
        msg 'Creating condarc symlink'
        ln -s infrastructure/current/condarc
    fi
    cd infrastructure
    mkdir -p blue green staging testing blue/{bin,etc} blue/conda/{def,envs}
    ln -s blue current
    touch current/condarc
    write_condarc
}

write_condarc() {
    local condarc_template=$script_dir/../resources/condarc.m4
    m4 -D RESOLVED_TARGET=$resolved_target $condarc_template > current/condarc
}

ensure_conda() {
    if [[ ! -x ${CONDA-} ]]; then
        msg '$CONDA not set.'
        CONDA=$(which conda) || msg "No conda in PATH."
        if [[ -x $CONDA ]]; then
            msg "Using conda at $CONDA"
        else
            # What do you do when you have no conda?
            # What do you do when you have no conda?
            # What do you do when you have no conda?
            # Fetch it from the server!
            setup_temp
            check_os
            msg "fetch conda!!!"
            cd $my_tmp_dir
            url="https://repo.anaconda.com/miniconda/Miniconda3-latest-$plat-x86_64.sh"
            msg "fetching $url"
            curl "$url" -o installer.sh
            bash installer.sh -bp ./miniconda
            CONDA=$my_tmp_dir/miniconda/condabin/conda
        fi
    fi
    dump_var CONDA
    if [[ $verbose == 'y' ]]; then
        CONDA_ENVS_DIRS="$resolved_target/infrastructure/current/conda/envs" \
        CONDA_PKGS_DIRS=$resolved_target/conda_package_cache \
        HOME=$resolved_target CONDARC=$resolved_target/condarc "$CONDA" info
    fi
}

setup_temp() {
    tmp_root=$(dirname $(mktemp -u))
    # msg "tmp_root=$tmp_root"
    user_root=$tmp_root/$USER
    # msg "user_root=$user_root"
    mkdir -p $user_root
    template=$tmp_root/$USER/$(date +%Y-%m-%d)-XXXX
    my_tmp_dir=$(mktemp -d $template)
    # msg "my_tmp_dir=$my_tmp_dir"
}

check_os() {
    local u=$(uname)
    case "$u" in
        Darwin) plat=MacOSX ;;
        Linux) plat=Linux ;;
        *) die "unknown platform $u"
    esac
}

cleanup() {
    trap - SIGINT SIGTERM ERR EXIT
    # script cleanup here
    cd
    msg ${BLUE}CLEANUP${NOFORMAT}
    if [[ -e ${my_tmp_dir-} ]]; then
        msg "rm -rf $my_tmp_dir"
        rm -rf "$my_tmp_dir"
    fi
    msg ${BLUE}DONE${NOFORMAT}
} >&2

dump_var() {
    local var_name=$1
    local prefix=${2-}
    local quoting=${3-}
    local quote=
    [[ -n $quoting ]] && quote="'"
    local value="${!var_name}"
    msg "$prefix$var_name: $quote$value$quote"
}

die() {
    local msg="${RED-}ERROR:${NOFORMAT-} $1"
    local code=${2-1} # default exit status 1
    msg "$msg"
    exit "$code"
}

msg() {
    echo -e "${1-}"
}

setup_colors() {
    if [[ -t 2 ]] && [[ -z "${NO_COLOR-}" ]] && [[ "${TERM-}" != "dumb" ]]; then
        NOFORMAT='\033[0m' RED='\033[0;31m' GREEN='\033[0;32m' ORANGE='\033[0;33m' BLUE='\033[0;34m' PURPLE='\033[0;35m' CYAN='\033[0;36m' YELLOW='\033[1;33m'
    else
        NOFORMAT='' RED='' GREEN='' ORANGE='' BLUE='' PURPLE='' CYAN='' YELLOW=''
    fi
}

main "$@"
