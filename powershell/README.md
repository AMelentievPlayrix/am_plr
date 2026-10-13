# powershell/

Aliases, functions and the prompt for Windows PowerShell. The macOS twin is `../shell/*.zsh`.

Load it once, from `$PROFILE` (setup prints the exact command):

```powershell
. D:\projects\am_plr\powershell\init.ps1
```

`init.ps1` exports `../mcp/.env` and then dot-sources every other `*.ps1` here in name order.
Claude Code does **not** need this - setup writes the tokens straight into `../.mcp.json` - so this
is only for running the MCP servers, `curl` and friends by hand in a terminal.

| | |
|---|---|
| `20-git.ps1` | `gco` (checkout), `gb`, `main` (checkout master + fetch), `pull` |
| `20-system.ps1` | `ll` |
| `30-prompt.ps1` | `(.venv) ~\path (branch ↑2 ↓1) $` |

`gco`, not `gc`: `gc` is a ReadOnly alias for `Get-Content` that nothing should shadow.

Keep these files ASCII without a BOM - PowerShell 5.1 reads a BOM-less file as the ANSI codepage,
so a literal non-ASCII character would be corrupted (the prompt's arrows use `[char]0x2191` instead).
