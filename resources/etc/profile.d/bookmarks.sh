# Directory Alias Management
# See also sd & lsd.
export DIR_ALIAS_STORE=~/.sd
function go {
    cd "$(cat "$DIR_ALIAS_STORE/$1")"
}

if [[ -n $BASH ]]; then
    complete -o nospace -C list-alias-store go
    complete -o nospace -C list-alias-store dsd
fi

if [[ -n $ZSH_NAME ]]; then
    _list_alias_store() { _values $(list-alias-store); }
    compdef _list_alias_store go
    compdef _list_alias_store dsd
fi
