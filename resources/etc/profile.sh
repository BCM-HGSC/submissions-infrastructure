# Top-level RC file to be sourced by the team for interactive sessions.
# Sources other scripts and sets environment variables.

# IAC_* is an abbreviation for infrastructure-as-code.

if [[ -z $IAC_TIER_DIR ]]; then
    if [[ $ZSH_NAME ]]; then
        __temp_arg0="$0"
    fi
    if [[ $BASH ]]; then
        __temp_arg0="${BASH_SOURCE[0]}"
    fi
    # echo __temp_arg0=$__temp_arg0
    __temp_this_script=$(/usr/bin/readlink -f "$__temp_arg0")
    # echo __temp_this_script=$__temp_this_script
    IAC_TIER_DIR=$(/usr/bin/dirname $(/usr/bin/dirname "$__temp_this_script"))
    unset __temp_arg0 __temp_this_script
fi
export IAC_TIER_DIR

if [[ -z ${IAC_ORIGINAL_PATH:=$PATH} ]]; then
    echo "WARNING: original PATH is empty!"
fi
export IAC_ORIGINAL_PATH

PATH=/usr/local/bin:/opt/local/bin:/usr/bin:/bin

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

export IAC_DIR=$(/usr/bin/dirname "$IAC_TIER_DIR")

if [[ -n $VERBOSE ]]; then
    echo "IAC_TIER_DIR=$IAC_TIER_DIR"
    echo "IAC_DIR=$IAC_DIR"
fi

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
    source "$IAC_DIR/$tier/etc/profile.sh"
}

iac_releoad() {
    iac_load "$IAC_TIER_NAME"
}
