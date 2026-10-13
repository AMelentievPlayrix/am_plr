#!/usr/bin/env bash
# One-shot setup for am_plr. Safe to re-run any time; every step is idempotent.
#
#   - checks the am plugin (skills) is installed - installing it is your step
#   - rules         -> ~/.claude/rules/am_plr (one symlink)
#   - uv sync       -> .venv that every MCP server runs on
#   - .mcp.json     -> generated for this machine from upstreams.toml, tokens from mcp/.env
#   - settings previews -> artifacts/generated/; checks the workspaces
#
# Tokens are read from mcp/.env by sync.py and written into the generated .mcp.json, so Claude Code
# does not need them in its own environment. Nothing else is written outside artifacts/ and
# ~/.claude/rules. Honors CLAUDE_CONFIG_DIR (defaults to ~/.claude), same as Claude Code itself.
#
# The Windows twin is scripts/setup.ps1 + scripts/sync_win.py.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$REPO"/{skills,agents,rules,mcp} "$REPO/artifacts/generated"

# Same loading as shell/init.zsh, so a token already exported in this terminal still works.
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
AM_PLR_UV="$(command -v uv)"
export AM_PLR_UV
exec uv run --quiet --no-project --python 3.13 "$REPO/scripts/sync.py"
