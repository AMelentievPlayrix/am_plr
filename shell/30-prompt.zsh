
# Ahead/behind counts vs upstream, e.g. " ↑2" " ↓1" " ↑2 ↓1" or "" if in sync/no upstream
git_branch_diff() {
    local upstream
    upstream=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null) || return
    local counts ahead behind
    counts=$(git rev-list --left-right --count HEAD..."$upstream" 2>/dev/null) || return
    ahead=${counts%%$'\t'*}
    behind=${counts##*$'\t'}
    local out=""
    [[ -n "$ahead" && "$ahead" != "0" ]] && out+=" %F{green}↑${ahead}%f"
    [[ -n "$behind" && "$behind" != "0" ]] && out+=" %F{red}↓${behind}%f"
    echo "$out"
}

update_prompt() {
    local cwd_part="%F{yellow}%~%f"

    local git_info=""
    if git rev-parse --is-inside-work-tree &>/dev/null; then
        local branch_name
        branch_name=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
        local diff
        diff=$(git_branch_diff)
        git_info=" (%F{cyan}${branch_name}%f${diff})"
    fi

    local venv=""
    if [[ -n "$VIRTUAL_ENV" ]]; then
        venv="%F{8}(${VIRTUAL_ENV##*/})%f "
    fi

    PROMPT="${venv}${cwd_part}${git_info} %F{white}\$%f"$'\n'
}

precmd_functions+=(update_prompt)
