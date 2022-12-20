# Top-level RC file to be sourced by the team for interactive sessions.
# Sources other scripts and sets environment variables.

# IAC_* is an abbreviation for infrastructure-as-code.

if [[ $ZSH_NAME ]]; then
    __temp_arg0="$0"
fi
if [[ $BASH ]]; then
    __temp_arg0="${BASH_SOURCE[0]}"
fi

if [[ -z ${IAC_ORIGINAL_PATH:=$PATH} ]]; then
    echo "WARNING: original PATH is empty!"
fi
export IAC_ORIGINAL_PATH

PATH=/usr/local/bin:/opt/local/bin:/usr/bin:/bin
export PATH

__temp_this_script=$(readlink -f "$__temp_arg0")

export IAC_TIER_DIR=$(dirname $(dirname "$__temp_this_script"))
export IAC_DIR=$(dirname "$IAC_TIER_DIR")
export IAC_PARENT=$(dirname "$IAC_DIR")
export IAC_TIER_NAME=$(basename $(dirname $(dirname "$__temp_arg0")))

__CONDA_ENVS_DIR="$IAC_TIER_DIR/conda/envs"

__add_env_if_exists() {
    local env_dir="$__CONDA_ENVS_DIR/$1"
    if [[ -d "$env_dir" ]]; then
        PATH="$env_dir/bin:$PATH"
    fi
}

__add_env_if_exists unix
__add_env_if_exists mac
__add_env_if_exists experimental
__add_env_if_exists bioconda
__add_env_if_exists python

unset CONDA_SHLVL  # starting from scratch
source "$__CONDA_ENVS_DIR/conda/etc/profile.d/conda.sh"
source "$__CONDA_ENVS_DIR/conda/etc/profile.d/mamba.sh"

unset __add_env_if_exists
unset __CONDA_ENVS_DIR

export CONDARC="$IAC_TIER_DIR/etc/condarc"

iac_dump_vars() {
    echo "IAC_TIER_DIR=$IAC_TIER_DIR"
    echo "IAC_TIER_NAME=$IAC_TIER_NAME"
    echo "IAC_DIR=$IAC_DIR"
    echo "IAC_PARENT=$IAC_PARENT"
    echo "IAC_ORIGINAL_PATH=$IAC_ORIGINAL_PATH"
    echo "CONDARC=$CONDARC"
}

if [[ -n $VERBOSE ]]; then
    echo __temp_arg0=$__temp_arg0
    echo __temp_this_script=$__temp_this_script
    iac_dump_vars
fi

unset __temp_arg0 __temp_this_script

PATH=~/bin:"$IAC_DIR/bin":"$IAC_TIER_DIR/bin":"$PATH"

export PATH

for i in "$IAC_TIER_DIR"/etc/profile.d/*.sh ; do
    if [ -r "$i" ]; then
        . "$i"
    fi
done

# Create dedicated "cd" functions for popular directories.
dynamic_cd cdh ~
if [[ $(uname -s) == "Linux" ]]; then
    dynamic_cd cd1 /stornext/snfs130/submissions
    dynamic_cd cdg /groups/submissions
    dynamic_cd cds /hgsc_software/submissions
fi


iac_load() {
    local tier="$1"
    shift
    IAC_TIER_DIR=
    IAC_TIER_NAME=
    source "$IAC_DIR/$tier/etc/profile.sh"
}

iac_releoad() {
    iac_load "$IAC_TIER_NAME"
}

# All files and directories will be group-writeable by default:
umask 0002
