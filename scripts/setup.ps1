#Requires -Version 5.1
# One-shot setup for am_plr on Windows. Safe to re-run any time; every step is idempotent.
#
#   - checks the am plugin (skills) is installed - installing it is your step
#   - rules      -> %USERPROFILE%\.claude\rules\am_plr (one junction)
#   - uv sync    -> .venv that every MCP server runs on
#   - .mcp.json  -> generated for this machine from upstreams.toml, tokens from mcp\.env
#   - settings previews -> artifacts\generated\; checks the workspaces
#
# Tokens are read from mcp\.env by sync_win.py and written into the generated .mcp.json, so nothing
# has to be in this shell's environment. There is no PowerShell shell layer by design - the zsh one
# in shell/ stays macOS-only. Honors CLAUDE_CONFIG_DIR (defaults to ~\.claude), as Claude Code does.
#
# The macOS twin is scripts/setup.sh + scripts/sync.py.

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot

foreach ($d in 'skills', 'agents', 'rules', 'mcp', 'artifacts\generated') {
    $p = Join-Path $repo $d
    if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
}

$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) {
    Write-Host 'uv is required: https://docs.astral.sh/uv/getting-started/installation/'
    exit 1
}
$env:AM_PLR_UV = $uv

& $uv run --quiet --no-project --python 3.13 (Join-Path $repo 'scripts\sync_win.py')
exit $LASTEXITCODE
