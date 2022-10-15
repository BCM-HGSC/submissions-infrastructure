# Functions for getting around quickly

up() { cd $(python -c "print('../'*${1:-1})"); }

function mgo() {
    mkdir -p "$1"
    cd "$1"
}

function dynamic_cd {
    name=$1
    dest=$2
    [[ -d $dest ]] || return
    eval "function $name { cd '$dest'/\$1; }"
    if [[ $BASH ]]; then
        eval "function _${name} { COMPREPLY=(\$(cd '$dest'; ls -d \"\$2\"*/)); }"
        complete -o nospace -F _${name} ${name}
    fi
    if [[ $ZSH_NAME ]]; then
        eval "function _${name} { _path_files -/ -W '$dest'; }"
        compdef _${name} ${name}
    fi
}
