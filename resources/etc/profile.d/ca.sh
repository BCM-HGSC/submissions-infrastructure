# Local support for conda                                                                                                                                                                                  

if [[ $BASH ]]; then
    _local_conda_ca() { COMPREPLY=($(cenvs | egrep "^$2")); }
    complete -o nospace -F _local_conda_ca -o plusdirs ca
fi

if [[ $ZSH_NAME ]]; then
    function _local_conda_ca {
        _values $(echo environments; cenvs)
    }
    compdef _local_conda_ca ca
fi

alias cda='conda deactivate'

# alias ca='conda activate'
ca() {
    if type conda | fgrep -q function; then
        conda deactivate
    fi
    __SAVE_PS1="$PS1"
    if type conda | fgrep -q function; then
        conda activate "$@"
    else
        _insure_conda_root
        # Tell conda activate to start fresh.
        unset CONDA_SHLVL
        # Trim extraneous bin or condabin directories.
        if [[ $PATH == "$__CONDA_ROOT"/bin:* ]]; then
            PATH=$(echo $PATH | cut -d: -f2-)
        fi
        if [[ $PATH == "$__CONDA_ROOT"/condabin:* ]]; then
            PATH=$(echo $PATH | cut -d: -f2-)
        fi
        # Load conda, which will set and export PATH.
        source "$__CONDA_ROOT"/bin/activate "$@"
    fi
    if [[ $? == 0 ]]; then
        if [[ "$CONDA_DEFAULT_ENV" =~ .*/.* ]]; then
            local new_mod="(.../$(basename "$CONDA_DEFAULT_ENV")) "
            PS1="$new_mod$__SAVE_PS1"
            export CONDA_PROMPT_MODIFIER="$new_mod"
        fi
    else
        PS1="$__SAVE_PS1"
    fi
}

cenvs() {
    _insure_conda_envs
    if [[ "$__CONDA_ENVS" ]]; then
        command ls "$__CONDA_ENVS"/
    fi
}

_insure_conda_envs() {
    :
}

_insure_conda_root() {
    if [[ "$__CONDA_ROOT" ]]; then
        return
    fi
    _insure_conda_exe
    if [[ -x "$__CONDA_EXE" ]]; then
        __CONDA_ROOT=$("$__CONDA_EXE" info --base)
    fi
}

_insure_conda_exe() {
    if [[ "$__CONDA_EXE" ]]; then
        return
    fi
    __CONDA_EXE="$CONDA_EXE"
    if [[ -z "$__CONDA_EXE" ]]; then
        __CONDA_EXE=$(/usr/bin/env which conda)
    fi
}

if [[ "$__CONDA_ENVS" ]]; then
    return
fi
_insure_conda_exe
if [[ -x "$__CONDA_EXE" ]]; then
    __CONDA_ENVS=$($__CONDA_EXE info | fgrep 'envs directories' | cut -d: -f2 | cut -d' ' -f2)
    export __CONDA_ENVS
    if [[ "$VERBOSE" ]]; then
        env | fgrep __CONDA_ENVS
    fi
fi
