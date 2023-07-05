# Source this file to activate the HGSC aws toolkit.

__HGSC_AWS_TOOLS_OLD_PATH=$PATH
__HGSC_AWS_TOOLS_OLD_PS1=$PS1

export PATH="PREFIX_DIRS:$PATH"
PS1="(aws) $PS1"

__aws_tools_deactivate() {
    export PATH="$__HGSC_AWS_TOOLS_OLD_PATH"
    PS1="$__HGSC_AWS_TOOLS_OLD_PS1"
    unset __HGSC_AWS_TOOLS_OLD_PATH __HGSC_AWS_TOOLS_OLD_PS1
    unalias deactivate
    unset -f __aws_tools_deactivate
}

alias deactivate="__aws_tools_deactivate"
