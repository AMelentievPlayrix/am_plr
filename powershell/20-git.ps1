# Git shortcuts. The macOS twin is shell/20-git.zsh.
#
# `gco`, not `gc`: gc is a ReadOnly, AllScope alias for Get-Content and overriding it would break
# anything that expects it. `main` and `pull` are functions, which take precedence over the
# main.cpl application and over any same-named alias.

Set-Alias -Name gco -Value git-checkout -Scope Global
Set-Alias -Name gb -Value git-branch -Scope Global

function git-checkout { git checkout @args }

function git-branch { git branch @args }

function main {
    git checkout master
    git fetch
}

function pull { git pull @args }
