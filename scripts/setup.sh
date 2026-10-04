#!/usr/bin/env bash
# One-shot setup for am_plr. Safe to re-run any time; every step is idempotent.
#
#   - checks the am-plr plugin (skills) is installed - installing it is your step
#   - rules         -> ~/.claude/rules/am_plr (one symlink)
#   - settings previews + my MCP config -> artifacts/generated/; checks am_plr/.mcp.json and workspaces
#
# Only the ~/.claude/rules/am_plr symlink is created (and old skill symlinks removed); nothing else is written
# outside artifacts/. Honors CLAUDE_CONFIG_DIR (defaults to ~/.claude), same as Claude Code itself.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$REPO"/{skills,agents,rules,mcp} "$REPO/artifacts/generated"

# Same loading as shell/init.zsh, so the token check sees exactly what terminals get.
# Names of non-empty variables before .env is loaded, so sync.py can tell whether this shell (e.g. a
# VS Code terminal) already had the tokens or only gets them from this script.
AM_PLR_ENV_BEFORE="$(env | sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\)=..*/\1/p' | tr '\n' ':')"
export AM_PLR_ENV_BEFORE

if [ -f "$REPO/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    . "$REPO/.env"
    set +a
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is required: https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
fi
exec uv run --quiet --no-project --python 3.13 "$REPO/scripts/sync.py"
