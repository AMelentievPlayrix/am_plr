#Requires -Version 5.1
# am_plr PowerShell entry point. Load it from $PROFILE:
#   . D:\projects\am_plr\powershell\init.ps1
#
# Exports am_plr/mcp/.env, then loads every powershell/*.ps1 (except this file) in name order.
# Machine-specific PATHs stay in $PROFILE itself.
#
# The macOS twin is shell/init.zsh. Claude Code does NOT depend on the tokens exported here - setup
# writes them straight into the generated .mcp.json - so this is only for running the MCP servers,
# curl and other tools by hand in a terminal.

$env:AM_PLR = Split-Path -Parent $PSScriptRoot

$amPlrEnvFile = Join-Path $env:AM_PLR 'mcp\.env'
if (Test-Path -LiteralPath $amPlrEnvFile) {
    foreach ($amPlrLine in Get-Content -LiteralPath $amPlrEnvFile) {
        $amPlrTrimmed = $amPlrLine.Trim()
        if (-not $amPlrTrimmed -or $amPlrTrimmed.StartsWith('#') -or $amPlrTrimmed -notmatch '=') { continue }
        $amPlrPair = ($amPlrTrimmed -replace '^export\s+', '') -split '=', 2
        $amPlrKey = $amPlrPair[0].Trim()
        $amPlrValue = $amPlrPair[1].Trim()
        if ($amPlrValue.Length -ge 2 -and $amPlrValue[0] -eq $amPlrValue[-1] -and
            ($amPlrValue[0] -eq '"' -or $amPlrValue[0] -eq "'")) {
            $amPlrValue = $amPlrValue.Substring(1, $amPlrValue.Length - 2)
        }
        else {  # unquoted: a trailing ` # comment` is not part of the value, same as sync_win.py
            $amPlrValue = ($amPlrValue -split '\s+#', 2)[0].TrimEnd()
        }
        if ($amPlrKey) { Set-Item -Path "Env:$amPlrKey" -Value $amPlrValue }
    }
}
Remove-Variable amPlrEnvFile, amPlrLine, amPlrTrimmed, amPlrPair, amPlrKey, amPlrValue `
    -ErrorAction SilentlyContinue

Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.ps1' |
    Where-Object { $_.Name -ne 'init.ps1' } |
    Sort-Object Name |
    ForEach-Object { . $_.FullName }
