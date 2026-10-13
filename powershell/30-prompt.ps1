# Prompt. The macOS twin is shell/30-prompt.zsh.
#
# PowerShell calls `prompt` before every line, which is what zsh's precmd_functions hook does there.
# Colors are ANSI escapes instead of zsh's %F{...}; the arrows need a UTF-8 console (set below).

[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)  # the up/down arrows are non-ASCII

$script:AmPlrColors = @{
    Reset = "$([char]27)[0m"; Yellow = "$([char]27)[33m"; Cyan = "$([char]27)[36m"
    Green = "$([char]27)[32m"; Red = "$([char]27)[31m"; White = "$([char]27)[37m"
    Dim = "$([char]27)[90m"
}

function Get-AmPlrBranchDiff {
    <#  Ahead/behind vs upstream, e.g. " ^2" " v1" " ^2 v1" (arrows), or "" if in sync / no upstream. #>
    $upstream = git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $upstream) { return '' }
    $counts = git rev-list --left-right --count "HEAD...$upstream" 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $counts) { return '' }
    $ahead, $behind = $counts -split "`t"
    $c = $script:AmPlrColors
    $out = ''
    if ($ahead -and $ahead -ne '0') { $out += " $($c.Green)$([char]0x2191)$ahead$($c.Reset)" }
    if ($behind -and $behind -ne '0') { $out += " $($c.Red)$([char]0x2193)$behind$($c.Reset)" }
    return $out
}

function prompt {
    $lastExit = $global:LASTEXITCODE  # the git calls below would otherwise clobber your command's code
    $c = $script:AmPlrColors

    $cwd = $ExecutionContext.SessionState.Path.CurrentLocation.Path
    $home_ = $HOME.TrimEnd('\')
    if ($cwd -eq $home_) { $cwd = '~' }
    elseif ($cwd.StartsWith("$home_\")) { $cwd = '~' + $cwd.Substring($home_.Length) }
    $cwdPart = "$($c.Yellow)$cwd$($c.Reset)"

    $gitInfo = ''
    git rev-parse --is-inside-work-tree *>$null
    if ($LASTEXITCODE -eq 0) {
        $branch = git rev-parse --abbrev-ref HEAD 2>$null
        if ($branch) { $gitInfo = " ($($c.Cyan)$branch$($c.Reset)$(Get-AmPlrBranchDiff))" }
    }

    $venv = ''
    if ($env:VIRTUAL_ENV) { $venv = "$($c.Dim)($(Split-Path -Leaf $env:VIRTUAL_ENV))$($c.Reset) " }

    $global:LASTEXITCODE = $lastExit
    "$venv$cwdPart$gitInfo $($c.White)`$$($c.Reset)`n"
}
