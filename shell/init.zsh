# am_plr shell entry point. Source it from ~/.zshrc:
#   source ~/projects/am_plr/shell/init.zsh
#
# Exports am_plr/.env (tokens, git-ignored), then loads every shell/*.zsh (except this file) in name order.
# Machine-specific PATHs stay in ~/.zshrc / ~/.zprofile.

export AM_PLR="${${(%):-%x}:A:h:h}"

if [[ -f "$AM_PLR/.env" ]]; then
    set -a
    source "$AM_PLR/.env"
    set +a
fi

for _am_plr_f in "$AM_PLR"/shell/*.zsh(N); do
    [[ "${_am_plr_f:t}" == init.zsh ]] || source "$_am_plr_f"
done
unset _am_plr_f
