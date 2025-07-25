up() { cd $(python -c "print('../'*${1:-1})"); }


lll() { ls -l "$@" | sed 's/ -.*/@/'; }


va() {  # TODO fix
    local d=$(pwd)
    while [[ "$d" != / ]]; do
        echo "$d" >&2
        if [[ -d "$d"/venv ]]; then
            conda deactivate
            source "$d"/venv/bin/activate
            return
        fi
        d="$(dirname "$d")"
    done
    echo "venv not found" >&2
    return 1
}


function cdn {
    cd -P $(path | sed -n "${1:-1}"p); pwd
}

function clc { "$@" --color | cat; }


function cttl() { csv2tsv < "$1" | tttl; }
function ctt() { csv2tsv < "$1" | ttt; }


function locka() { chmod -R -w ${1:-.}; }
function unlocka() { chmod -R +w ${1:-.}; }
function unlockd() { chmod +w ${1:-.}; }


if [[ $(uname -s) == "Darwin" ]]; then
    _list_volumes() { ls /Volumes | egrep "^$2"; }
    eject() { diskutil unmount "$1"; }
    [[ -n $BASH ]] && complete -o nospace -C _list_volumes eject
    if [[ -n $ZSH_NAME ]]; then
        _list_volumes_zsh() { _values $(_list_volumes); }
        compdef _list_volumes_zsh eject
    fi
fi
