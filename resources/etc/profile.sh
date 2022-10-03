# Top-level RC file to be sourced by the team for interactive sessions.
# Sources other scripts and sets environment variables.


if [[ -z $TIER_DIR ]]; then
    if [[ $ZSH_NAME ]]; then
        __temp_arg0="$0"
    fi
    if [[ $BASH ]]; then
        __temp_arg0="${BASH_SOURCE[0]}"
    fi
    # echo __temp_arg0=$__temp_arg0
    __temp_this_script=$(/usr/bin/readlink -f "$__temp_arg0")
    # echo __temp_this_script=$__temp_this_script
    TIER_DIR=$(/usr/bin/dirname $(/usr/bin/dirname "$__temp_this_script"))
    unset __temp_arg0 __temp_this_script
fi
export TIER_DIR

echo "TIER_DIR=$TIER_DIR"

for i in "$TIER_DIR"/etc/profile.d/*.sh ; do
    if [ -r "$i" ]; then
        . "$i"
    fi
done
