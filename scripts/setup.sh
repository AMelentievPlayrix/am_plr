#!/usr/bin/env bash
# One-shot setup for am_plr. Safe to re-run any time; every step is idempotent.
#
#   1. .venv              shared Python venv: requirements.txt + mcp/*/requirements.txt
#   2. scripts/sync.py    skills/agents -> ~/.claude/{skills,agents} (symlinks, conflict-checked
#                         against upstream repos in upstreams.toml), rules -> ~/.claude/rules/am_plr,
#                         MCP config -> artifacts/generated/mcp.json + copy-paste instructions.
#
# Only symlinks under ~/.claude/{skills,agents,rules} are created/removed; MCP config is never written.
# Honors CLAUDE_CONFIG_DIR (defaults to ~/.claude), same as Claude Code itself.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO/.venv"
VENV_PY="$VENV/bin/python"
GEN_DIR="$REPO/artifacts/generated"
PY_VERSION="3.13"  # sync.py needs >= 3.11 (tomllib)

if [ -t 1 ]; then B=$'\033[1m'; G=$'\033[32m'; Y=$'\033[33m'; D=$'\033[2m'; N=$'\033[0m'; else B=""; G=""; Y=""; D=""; N=""; fi
step() { printf '\n%s==> %s%s\n' "$B" "$1" "$N"; }
ok()   { printf '  %s+%s %s\n' "$G" "$N" "$1"; }
warn() { printf '  %s!%s %s\n' "$Y" "$N" "$1"; }
info() { printf '  %s%s%s\n' "$D" "$1" "$N"; }

step "Preparing directories"
mkdir -p "$REPO"/{skills,agents,rules,mcp} "$GEN_DIR"
info "repo:   $REPO"
info "claude: ${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

step "Python venv ($VENV)"
REQ_FILES=()
[ -f "$REPO/requirements.txt" ] && REQ_FILES+=("$REPO/requirements.txt")
for f in "$REPO"/mcp/*/requirements.txt; do
    [ -f "$f" ] && REQ_FILES+=("$f")
done

if [ -d "$VENV" ] && ! "$VENV_PY" -c 'import sys; assert sys.version_info >= (3, 11)' >/dev/null 2>&1; then
    warn "existing venv is broken or older than Python 3.11, recreating"
    rm -rf "$VENV"
fi

if command -v uv >/dev/null 2>&1; then
    [ -d "$VENV" ] || { uv venv --quiet --python "$PY_VERSION" "$VENV"; ok "venv created (uv)"; }
    LOCK="$GEN_DIR/requirements.lock"
    if [ ${#REQ_FILES[@]} -gt 0 ]; then
        uv pip compile --quiet --python "$VENV_PY" "${REQ_FILES[@]}" -o "$LOCK"
    else
        : > "$LOCK"
    fi
    # sync = venv exactly matches requirements (deps removed from requirements get uninstalled)
    uv pip sync --quiet --allow-empty-requirements --python "$VENV_PY" "$LOCK"
else
    [ -d "$VENV" ] || { python3 -m venv "$VENV"; ok "venv created (python3 -m venv)"; }
    "$VENV_PY" -m pip install --quiet --upgrade pip
    for f in "${REQ_FILES[@]+"${REQ_FILES[@]}"}"; do
        "$VENV_PY" -m pip install --quiet -r "$f"
    done
    warn "uv not found: deps removed from requirements stay installed (rm -rf .venv to clean)"
fi
for f in "${REQ_FILES[@]+"${REQ_FILES[@]}"}"; do info "deps: ${f#"$REPO"/}"; done
ok "$("$VENV_PY" --version), $("$VENV_PY" -c 'import importlib.metadata as m; print(len(list(m.distributions())))') packages"

exec "$VENV_PY" "$REPO/scripts/sync.py"
