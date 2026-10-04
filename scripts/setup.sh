#!/usr/bin/env bash
# One-shot setup for am_plr. Safe to re-run any time; every step is idempotent.
#
#   - skills/agents -> ~/.claude/{skills,agents} (symlinks, conflict-checked against upstream repos)
#   - rules         -> ~/.claude/rules/am_plr (one symlink)
#   - MCP config and settings previews -> artifacts/generated/ + copy-paste instructions
#
# Only symlinks under ~/.claude/{skills,agents,rules} are created/removed; nothing else is written
# outside artifacts/. Honors CLAUDE_CONFIG_DIR (defaults to ~/.claude), same as Claude Code itself.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$REPO"/{skills,agents,rules,mcp} "$REPO/artifacts/generated"

# Same loading as shell/init.zsh, so the token check sees exactly what terminals get.
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
