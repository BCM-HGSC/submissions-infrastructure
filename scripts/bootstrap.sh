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

-h, --help          Print this help and exit.
-v, --verbose       Print script debug info.
--no-color          Turn off color output.
--force             Force overwriting existing infrastructure!
--offline           No internet usage
-n, --no-installs   No conda or pip installs, just skeleton and condarc
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
    dump_var verbose
    dump_var force
    dump_var offline
    dump_var no_installs
    dump_var target_dir
    msg

    script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd -P)
    dump_var script_dir

    # script logic here
    get_conda
    export PATH=/usr/bin:/bin

    mkdir -p "$target_dir"
    resolved_target=$(cd -P "$target_dir"; pwd)
    dump_var resolved_target

    setup_target

    export CONDA_ENVS_DIRS="$resolved_target/infrastructure/current/conda/envs"
    export CONDA_PKGS_DIRS=$resolved_target/conda_package_cache
    export HOME=$resolved_target
    export CONDARC=$resolved_target/condarc
    if [[ $verbose == 'y' && -n $CONDA ]]; then
        "$CONDA" info
    fi

    if [[ -n $no_installs ]]; then
        exit
    fi

    use_miniconda3_in_temp_for_conda_if_necessary
    deploy_engine
} >&2

parse_params() {
    # Set force and target_dir.

    # default values of variables set from params
    verbose=
    force=
    offline=
    no_installs=

    while :; do
        case "${1-}" in
            -h | --help) usage ;;
            -v | --verbose) verbose=${verbose}y ;;
            --no-color) NO_COLOR=y ;;
            --force) force=y ;;
            --offline) offline=y ;;
            -n | --no-installs) no_installs=y ;;
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

get_conda() {
    # Set CONDA if not set and available in PATH.
    : ${CONDA:=$(which conda)}  # Set CONDA if not set to conda in PATH
    if [[ ! -x $CONDA ]]; then
        warning "CONDA is not set, and no conda executable found in PATH."
    fi
    dump_var CONDA
}

use_miniconda3_in_temp_for_conda_if_necessary() {
    # If CONDA is unset, ownload and install Miniconda3 in order to set CONDA.
    if [[ ! -x ${CONDA-} ]]; then
        if [[ -n $offline ]]; then
            error "CONDA is not set, and we are offline"
            return
        fi
        # What do you do when you have no conda?
        # What do you do when you have no conda?
        # What do you do when you have no conda?
        # Fetch it from the server!
        setup_temp
        check_os
        msg "Fetching conda..."
        cd $my_tmp_dir
        url="https://repo.anaconda.com/miniconda/Miniconda3-latest-$plat-x86_64.sh"
        msg "fetching $url"
        curl "$url" -o installer.sh
        bash installer.sh -bp ./miniconda
        CONDA=$my_tmp_dir/miniconda/condabin/conda
        dump_var CONDA
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

deploy_engine() {
    if [[ ! -x $CONDA ]]; then
        error "Cannot deploy engine, because there is no conda"
        return
    fi
    msg deploy_engine
    engine_path=$resolved_target/engine
    rm -rf $engine_path
    local offline_opt=
    [[ -n $offline ]] && offline_opt='--offline'
    $CONDA create $offline_opt -y -p $engine_path conda pip
    export PATH=$engine_path/bin:$PATH
    dump_var PATH
    which conda
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
    local value="${!var_name}"
    msg "$var_name=$value"
}

die() {
    local msg="$1"
    local code=${2-1} # default exit status 1
    critical "$msg"
    exit "$code"
}

critical() {
    msg "${RED}CRITICAL${NOFORMAT}: $1"
}

error() {
    msg "${RED}ERROR${NOFORMAT}: $1"
}

warning() {
    msg "${ORANGE}WARNING${NOFORMAT}: $1"
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
