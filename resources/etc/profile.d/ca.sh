# Local support for conda
# Add two commands:
#
# cda: a wrapper for "conda deactivate"
#
# ca: a wrapper function for "conda activate" that simplifies the PS1 prompt
# when the environment is specified by path, as indicated by a slash.
#
# The ca function supports tab-completion using the contents of the directory
# "${IAC_PARENT}/users/${USER}/conda/envs"
#
# Additional the alias "reload-ca" will reload this file.

alias reload-ca="source '$0'"

alias cda='conda deactivate'

ca() {
    local __SAVE_PS1="$PS1"
    conda activate "$@"
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

if [[ $ZSH_NAME ]]; then
    # Define the zsh completer function
    _ca_complete() {
        local envs
        if [[ $words[2] == */* ]]; then
            _files -W -g "$words[2]*(-/)" -/ -o nosort
        else
            envs=( $(ls "${IAC_PARENT}/users/${USER}/conda/envs") )
            _arguments "1: :($(echo $envs))"
            # _files -W -g "${IAC_PARENT}/users/${USER}/conda/envs/$words[2]*(-/)" -/ -o nosort
        fi
    }

    # Register the completer function for the "ca" function
    compdef _ca_complete ca
fi

if [[ $BASH ]]; then
    # Define the bash completer function
    _ca_complete() {
        local envs
        if [[ $COMP_WORDS[COMP_CWORD] == */* ]]; then
            COMPREPLY=( $(compgen -d "$COMP_WORDS[COMP_CWORD]" ) )
        else
            envs=( $(ls "${IAC_PARENT}/users/${USER}/conda/envs") )
            COMPREPLY=( $(compgen -W "$(echo ${envs[*]})" -- "${COMP_WORDS[COMP_CWORD]}" ) )
        fi
    }

    # Register the completer function for the "ca" function
    complete -F _ca_complete ca
fi
