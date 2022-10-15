# Starting with just bash, bootstrap our infrastructure.

set -Eeuo pipefail

usage() {
    cat << EOF
Usage: $(basename "${BASH_SOURCE[0]}") [-h] [-v] [--force] TARGET_DIR

Create TARGET_DIR if it does not already exist, and populated it with  a
subdirectory named "conda_package_cache" and another subdirectory named
"infrastructure". It is an error if "infrastructure" already exists unless
the --force option is applied.

Following the creation of the infrastructure directory, this script will create
engine_home if it does not already exist and then install or update the engine.

Available options:

-h, --help          Print this help and exit.
-v, --verbose       Print script debug info.
--no-color          Turn off color output.
--force             Force overwriting existing infrastructure!
--offline           No internet usage
-k, --keep          Keep and use current deployment engine
-n, --no-installs   No conda or pip installs, just skeleton and condarc

Environment:
CONDA: optional path to a conda executable
PATH: will be searched for "conda" if CONDA is not set

If a conda executable is not set by either PATH or CONDA, this script will
download the latest version of Miniconda3 into a temporary directory and use that.
EOF
    exit
}

main() {
    setup_colors
    parse_params "$@"
    setup_colors

    trap cleanup SIGINT SIGTERM ERR EXIT

    if [[ ${#VERBOSE} -gt 2 ]]; then
        set -x
    fi

    info "${BLUE}Read parameters:${NOFORMAT}"
    dump_vars VERBOSE FORCE OFFLINE KEEP NO_INSTALLS TARGET_DIR
    msg

    SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd -P)
    RESOURCES_DIR=$(cd $SCRIPT_DIR/../resources && pwd -P)
    mkdir -p "$TARGET_DIR"
    RESOLVED_TARGET=$(cd -P "$TARGET_DIR"; pwd)
    dump_vars SCRIPT_DIR RESOURCES_DIR RESOLVED_TARGET

    setup_target
    get_conda

    # Environment variables used by conda when creating the engine.
    export CONDA_ENVS_DIRS="$RESOLVED_TARGET/infrastructure/production/conda/envs"
    export CONDA_PKGS_DIRS="$RESOLVED_TARGET"/conda_package_cache
    export HOME="$RESOLVED_TARGET"/engine_home
    export CONDARC="$RESOLVED_TARGET"/infrastructure/staging/condarc

    use_miniconda3_in_temp_for_conda_if_necessary

    if [[ -z $KEEP ]]; then
        deploy_engine
    fi

    msg
    info "New values"
    CONDA="$HOME"/engine/bin/conda
    PYTHON="$HOME"/engine/bin/python3
    dump_vars CONDA PYTHON

    if [[ ${#VERBOSE} -gt 1 && -x $CONDA ]]; then
        ls -ld "$CONDA"
        "$CONDA" info
    fi

    if [[ -n $NO_INSTALLS ]]; then
        exit
    fi
} >&2

parse_params() {
    # default values of variables set from params
    VERBOSE=
    FORCE=
    OFFLINE=
    KEEP=
    NO_INSTALLS=

    while :; do
        case "${1-}" in
            -h | --help) usage ;;
            -v | --verbose) VERBOSE=${VERBOSE}y ;;
            --no-color) NO_COLOR=y ;;
            --force) FORCE=y ;;
            --offline) OFFLINE=y ;;
            -k | --keep) KEEP=y ;;
            -n | --no-installs) NO_INSTALLS=y ;;
            -?*) die "Unknown option: $1 (-h for help)" ;;
            *) break ;;
        esac
        shift
    done

    [[ $# -eq 0 ]] && die "missing value for TARGET_DIR (-h for help)"
    TARGET_DIR="$1"
    shift

    [[ $# -eq 0 ]] || die "unused positional parameters: $@ (-h for help)"

    return
}

setup_target() {
    cd "$RESOLVED_TARGET"
    if [[ -e infrastructure ]]; then
        if [[ -z $FORCE ]]; then
            die "$TARGET_DIR/infrastructure already exists"
        else
            warning "overwriting $RESOLVED_TARGET/infrastructure"
            rm -rf infrastructure
        fi
    fi
    mkdir -p conda_package_cache engine_home infrastructure user_envs
    if ! ls $RESOLVED_TARGET/condarc &> /dev/null; then
        info 'Creating condarc symlink'
        ln -s infrastructure/production/condarc
    fi
    cd infrastructure
    mkdir -p blue green testing blue/{bin,etc} blue/conda/{def,envs}
    ln -s blue staging
    touch staging/condarc
    write_condarc
}

write_condarc() {
    local condarc_template=$RESOURCES_DIR/condarc.m4
    m4 -D RESOLVED_TARGET=$RESOLVED_TARGET \
       -D ENVIRONMENT_NAME=blue $condarc_template > staging/condarc
}

get_conda() {
    # Set CONDA if not set and available in PATH.
    if [[ ! -x "${CONDA:=}" ]]; then
        if [[ -n "$CONDA" ]]; then
            warning "CONDA=$CONDA"
            warning "Supplied vaule of CONDA is not executable."
        fi
        CONDA=$(command -v conda || :)  # will be "" if not found in PATH
        if [[ -n "$CONDA" ]]; then
            if [[ ! -x "$CONDA" ]]; then
                warning "CONDA from PATH is not executable."
                warning "CONDA=$CONDA (bad value in PATH)"
            else
                dump_var CONDA
            fi
        else
            warning "No conda in PATH."
            warning "PATH=$PATH"
        fi
    fi
}

use_miniconda3_in_temp_for_conda_if_necessary() {
    # If CONDA is unset, ownload and install Miniconda3 in order to set CONDA.
    if [[ ! -x ${CONDA-} ]]; then
        if [[ -n $OFFLINE ]]; then
            error "CONDA is not set, and we are offline"
            return
        fi
        # What do you do when you have no conda?
        # What do you do when you have no conda?
        # What do you do when you have no conda?
        # Fetch it from the server!
        setup_temp
        check_os
        info "Fetching conda..."
        cd $my_tmp_dir
        url="https://repo.anaconda.com/miniconda/Miniconda3-latest-$plat-x86_64.sh"
        info "fetching $url"
        curl "$url" -o installer.sh
        bash installer.sh -bp ./miniconda
        CONDA=$my_tmp_dir/miniconda/condabin/conda
        dump_var CONDA
    fi
}

setup_temp() {
    tmp_root=$(dirname $(mktemp -u))
    debug "tmp_root=$tmp_root"
    user_root=$tmp_root/$USER
    debug "user_root=$user_root"
    mkdir -p $user_root
    template=$tmp_root/$USER/$(date +%Y-%m-%d)-XXXX
    my_tmp_dir=$(mktemp -d $template)
    debug "my_tmp_dir=$my_tmp_dir"
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
    [[ -x $CONDA ]] || die "Cannot deploy engine, because there is no conda"
    dump_var HOME
    PYTHON="$($CONDA info --base)"/bin/python3
    dump_var PYTHON
    export CONDA OFFLINE VERBOSE
    cd "$HOME"
    msg
    run_python bootstrap_engine.py
}

run_python() {
    info "run_python $@"
    local script_name=$1
    shift
    "$PYTHON" "$SCRIPT_DIR"/$script_name "$@"
}

cleanup() {
    trap - SIGINT SIGTERM ERR EXIT
    # script cleanup here
    cd
    info ${BLUE}CLEANUP${NOFORMAT}
    if [[ -e ${my_tmp_dir-} ]]; then
        info "rm -rf $my_tmp_dir"
        rm -rf "$my_tmp_dir"
    fi
    info ${BLUE}DONE${NOFORMAT}
} >&2

dump_vars() {
    for name in $@; do dump_var $name; done
}

dump_var() {
    local var_name=$1
    local value="${!var_name}"
    info "$var_name=$value"
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

info() {
    msg "${BLUE}INFO${NOFORMAT}: $1"
}

debug() {
    if [[ -n $VERBOSE ]]; then
        msg "${GREEN}DEBUG${NOFORMAT}: $1"
    fi
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
