# Top-level RC file to be sourced by the team for interactive sessions.
# Sources other scripts and sets environment variables.

# IAC_* is an abbreviation for infrastructure-as-code.

if [[ -n $ZSH_NAME ]]; then
    __temp_arg0="$0"
fi
if [[ -n $BASH ]]; then
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

export CONDARC="$IAC_TIER_DIR/etc/condarc"
# Beside each user's conda packages rather than in a home directory, which
# on the clusters has a small quota.
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$IAC_PARENT/users/$USER/pip_cache}"
export MAMBA_NO_BANNER=1
export MAMBA_ROOT_PREFIX="$IAC_TIER_DIR/conda/envs/conda"

__CONDA_ENVS_DIR="$IAC_TIER_DIR/conda/envs"

__add_env_if_exists() {
    local env_dir="$__CONDA_ENVS_DIR/$1"
    if [[ -d "$env_dir" ]]; then
        PATH="$env_dir/bin:$PATH"
    fi
}

__add_env_if_exists experimental
__add_env_if_exists unix
__add_env_if_exists mac
__add_env_if_exists linux
__add_env_if_exists python

unset CONDA_SHLVL  # starting from scratch
source "$__CONDA_ENVS_DIR/conda/etc/profile.d/conda.sh"
source "$__CONDA_ENVS_DIR/conda/etc/profile.d/mamba.sh"

unset __add_env_if_exists
unset __CONDA_ENVS_DIR

iac_dump_vars() {
    echo "IAC_TIER_DIR=$IAC_TIER_DIR"
    echo "IAC_TIER_NAME=$IAC_TIER_NAME"
    echo "IAC_DIR=$IAC_DIR"
    echo "IAC_PARENT=$IAC_PARENT"
    echo "IAC_ORIGINAL_PATH=$IAC_ORIGINAL_PATH"
    echo "CONDARC=$CONDARC"
    echo "PIP_CACHE_DIR=$PIP_CACHE_DIR"
}

if [[ -n $VERBOSE ]]; then
    echo __temp_arg0=$__temp_arg0
    echo __temp_this_script=$__temp_this_script
    iac_dump_vars
fi

unset __temp_arg0 __temp_this_script

PATH=~/bin:"$IAC_DIR/bin":"$IAC_TIER_DIR/bin":"$PATH"

# Everything the caller had on PATH comes back, after the tier, so the
# tier's tools win and nothing else disappears (Homebrew, /usr/sbin,
# whatever "module load" added). Written to work in both bash and zsh.
__iac_append_original_path() {
    local entry rest="$IAC_ORIGINAL_PATH:"
    while [[ -n $rest ]]; do
        entry=${rest%%:*}
        rest=${rest#*:}
        [[ -z $entry ]] && continue
        case ":$PATH:" in
            *":$entry:"*) ;;
            *) PATH="$PATH:$entry" ;;
        esac
    done
}
__iac_append_original_path
unset -f __iac_append_original_path

export PATH

if [[ -n $ZSH_NAME ]]; then
    # The completers in profile.d call compdef, which exists only after
    # compinit has run. Oh My Zsh and similar run it; a plain zsh does not.
    # -i skips insecure directories without asking, since a team tier is
    # group-writable.
    whence compdef &>/dev/null || {
        autoload -Uz compinit
        compinit -i
    }
fi

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

iac_reload() {
    iac_load "$IAC_TIER_NAME"
}

# All files and directories will be group-writeable by default:
umask 0002
