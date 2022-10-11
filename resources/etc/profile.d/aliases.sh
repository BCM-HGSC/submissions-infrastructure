alias reload-aliases='. ~/etc/shrc.d/aliases.sh'

alias c-p='cp -p'

alias cdp='cd -P'

alias chmr='chmod -w'
alias chmw='chmod +w'

alias emacs='emacs -nw'

alias envs='env | sort'
alias envsg='env | sort | grep'

alias gd='git diff'
alias git="XDG_CONFIG_HOME='$IAC_TIER_DIR/etc' git"
# assumes lg is a git alias for something similar to:
# log --graph --decorate --date=format:'%F %T' --pretty=tformat:'%C(auto)%cd %h %d %s'
alias gl='git lg'

alias ls='ls --color=auto'
alias ll='ls -l'
alias lld='ls -ld'
alias llh='ls -lh'
alias lal='ls -Al'
alias lalh='ls -Alh'
alias la='ls -A'
alias l.='ls -d .*'
alias l.l='ls -dl .*'
alias l.lh='ls -dlh .*'

alias pc=PAGER=cat

alias rmrf='rm -rf'

alias shlvl='echo $SHLVL'
alias st='echo $?'

if [[ $(uname -s) == "Darwin" ]]; then
    alias excel='open -a "Microsoft Excel"'
    alias pbh='fc -lrn -1 | tr -d \\n | pbcopy'
fi
