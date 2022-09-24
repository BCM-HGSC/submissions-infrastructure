ranger() {
    if [ -z "$RANGER_LEVEL" ]; then
        $(/usr/bin/env which ranger) "$@"
    else
        exit
    fi
}

# From https://github.com/ranger/ranger/blob/master/examples/shell_automatic_cd.sh
ranger_cd() {
    temp_file="$(mktemp -t "ranger_cd.XXXXXXXXXX")"
    ranger --choosedir="$temp_file" -- "${@:-$PWD}"
    if chosen_dir="$(cat -- "$temp_file")" && [ -n "$chosen_dir" ] && [ "$chosen_dir" != "$PWD" ]; then
        cd -- "$chosen_dir"
    fi
    rm -f -- "$temp_file"
}

alias rcd=ranger_cd

# From https://github.com/ranger/ranger/blob/master/examples/shell_subshell_notice.sh
[ -n "$RANGER_LEVEL" ] && PS1="$PS1"'(in ranger) '
