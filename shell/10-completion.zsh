autoload -Uz vcs_info
autoload -Uz compinit
compinit

zstyle ':completion:*:*:make:*' tag-order targets
