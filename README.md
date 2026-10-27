# am_plr

My personal Claude Code + VS Code + shell setup, applied to all projects at once.
It sits **on top of** team repos (perfect-project, vso-engine-autotests) and never conflicts with them.

- **Skills** ship as a Claude Code plugin, `am`. Use them in any project as `/am:<skill>`.
- **MCP servers** (team and mine) are declared in `upstreams.toml` and generated into `am_plr/.mcp.json`
  with this machine's paths and your tokens. Open `workspaces/vso.code-workspace` (Windows:
  `vso-windows.code-workspace`): am_plr is its first folder, so Claude Code starts there and loads them.
- **Rules, settings, venv** are prepared by one script per OS.

## Setup, step by step

Needs [uv](https://docs.astral.sh/uv/). The team repos must be siblings of am_plr
(`~/projects/<name>` on macOS, `D:\projects\<name>` on Windows).

1. **Run setup** (again any time something changes). It is the same on both machines, just a different entry point:

   | macOS | Windows (PowerShell 5.1+) |
   |---|---|
   | `~/projects/am_plr/scripts/setup.sh` | `D:\projects\am_plr\scripts\setup.ps1` |

2. **Do the "Next steps" it prints at the end.** Only what's still missing is listed, in order:
   - create `mcp/.env` from `mcp/.env.example` and fill in `TEAMCITY_TOKEN` (git-ignored);
   - install the plugin: in Claude Code run `/plugin marketplace add <am_plr>`, then `/plugin install am@am-plr`;
   - review the Claude Code / VS Code settings with the printed diff command, then run the printed copy command.
     On a new machine (no `~/.claude/settings.json`) the blueprint is copied as is: put your token in place of
     `<YOUR_ANTHROPIC_AUTH_TOKEN>`;
   - load the aliases and prompt in every terminal: macOS adds `source .../shell/init.zsh` to `~/.zshrc`,
     Windows adds `. ...\powershell\init.ps1` to `$PROFILE` (setup prints the exact command).
3. **Restart** Claude Code (in VS Code: **Developer: Reload Window**). Check with `/plugin`, `/mcp` and `/skills`.
4. Run setup again: when everything is in place it prints **All set**.

### How MCP servers get their tokens

Setup writes the values from `mcp/.env` straight into the generated `.mcp.json`, so Claude Code does not need
them in its own environment however VS Code was launched. A variable that is **not** set in `mcp/.env` is left
out of the config entirely, and the server falls back to its own `.env` - which is how `qase` already reads
`vso-engine-autotests/.env`. Variables written as `${VAR?}` in `upstreams.toml` are optional overrides: setup
reports them instead of warning.

Both `mcp/.env` and the generated `.mcp.json` hold real tokens and are git-ignored. On Windows they are
protected by the folder's NTFS permissions only (`chmod 0600` has no equivalent there).

### What setup does by itself

| Done automatically | Where |
|---|---|
| My rules (`rules/*.md`) loaded in every project | symlink (macOS) / junction (Windows) `~/.claude/rules/am_plr` |
| The venv every MCP server runs on | `uv sync` -> `.venv` |
| MCP config for all servers, with this machine's paths and tokens | `am_plr/.mcp.json` (git-ignored) |
| Claude Code / VS Code settings generated (yours + am_plr keys) | `artifacts/generated/{claude,vscode}-settings.json` |
| Checks: plugin installed, tokens set, am_plr first in workspaces, skills' MCP servers declared | printed as warnings / next steps |

**Never changed by setup:** plugin install, `~/.claude/settings.json`, VS Code settings, `~/.zshrc`
and any project file. You run those steps yourself from the printed list.

## Using the skills in a project

Open Claude Code in any project. The plugin is enabled for all of them:

```
/am:commit                  split changes into logical commits
/am:describe-work           Asana task + GitHub PR for the changes
/am:engine-create-autotest  new vso-engine-autotests test from a Qase case
/am:engine-create-autotests-in-batch  all Qase cases under an Asana parent task: analyse, plan, implement
/am:engine-fix-autotest     repair a broken autotest from an Asana task
/am:engine-iap-port         port an iOS in-app purchase test to macOS / UWP
/am:prompt-writer           turn a rough idea into a good prompt
/am:plan                    write a plan for a change (plan mode, code/python rules)
/am:plan-review             review a plan: major issues only, as questions with proposed fixes
/am:code-review             review finished changes against the plan and rules: verdict + findings
/am:log                     log this chat's work to work-log/ (commit + push); /am:log info this week for a report
/am:release-check           start release autotests/perf for a minor version, analyse, close the Asana subtasks
/am:update-perf-devices     find BrowserStack perf devices that break the nightly runs, replace them, keep the Asana inventory current
```

Claude also picks them up automatically from their descriptions. Team skills keep their own names
(e.g. `/perf-report`); ours always carry the `am:` prefix, so the two never clash.
Edits to a skill apply in the next session, or right away with `/reload-plugins`.

## What lives where

```
.claude-plugin/                 plugin manifest + local marketplace (this repo is both)
.mcp.json                       GENERATED by setup from upstreams.toml, git-ignored: local paths + real tokens
pyproject.toml, uv.lock         deps of the team MCP servers -> .venv (`uv sync`), used by every server in .mcp.json
skills/<name>/SKILL.md          my skills -> /am:<name> in every project
agents/<name>.md                my subagents -> am:<name>
work-log/YYYY-MM.md             my work log, written and pushed by /am:log
rules/*.md                      my rules, loaded in every session (`paths:` frontmatter to scope)
mcp/<name>/                     code of my own MCP servers (configured in upstreams.toml)
mcp/.env                        tokens for the MCP servers, git-ignored (template: mcp/.env.example)
upstreams.toml                  team repos I follow (paths relative to am_plr's parent) + every MCP server
scripts/setup.sh, sync.py       setup on macOS;  scripts/setup.ps1, sync_win.py  setup on Windows
config/claude/settings.json     Claude Code blueprint: gateway env (token = placeholder), model, permissions, plugin
config/vscode/settings.json     editor settings I want everywhere (autosave, 120 ruler, terminal, Python)
shell/*.zsh                     aliases, functions, prompt on macOS; loaded by shell/init.zsh from ~/.zshrc
powershell/*.ps1                the same on Windows; loaded by powershell/init.ps1 from $PROFILE
workspaces/*.code-workspace     vso (cross-platform) and vso-windows (adds vscode_project, engine-tests)
```

## How conflicts are avoided

- **Team skills/agents/rules stay in their repos** and load from there.
- **am_plr is self-contained:** its skills rely only on rules inside am_plr. Rules they need from a team repo are
  copied into `rules/` (e.g. `code.md`, `python.md` from vso-engine-autotests); refresh the copy when the original changes.
- **Skills**: plugin skills are namespaced (`am:commit`), so they can't hide a team skill.
- **MCP**: declared once in `upstreams.toml`, generated into `am_plr/.mcp.json` per machine. Team servers run
  their repos' code with am_plr's own `.venv` (deps in `pyproject.toml`), so a team repo changing its venv can't
  break them. They keep the names their skills call (`qase`, `cats-mcp-server`, …). The file loads only when
  am_plr is the first workspace folder.
- **Settings**: common settings live in am_plr; project-specific ones (interpreter, pytest args, launch.json)
  stay in each project's `.vscode/`. Generated files add am_plr keys on top of yours and drop nothing.

## Changing things

| I want to… | Do | Then |
|---|---|---|
| edit a skill or rule | just edit it | `/reload-plugins` or new session |
| add / rename / delete a skill | change `skills/<name>/` | `/reload-plugins` |
| change editor / Claude settings | edit `config/` | re-run setup, copy the printed command |
| add an MCP server (mine or another project's) | `[mcp.<name>]` in `upstreams.toml` (use `${VENV_PYTHON}` and `${upstream.<repo>}`); its deps in `pyproject.toml`; my own servers' code in `mcp/<name>/` | re-run setup, reload the window |
| follow another team repo | add `[upstream.<name>]` to `upstreams.toml` | re-run setup |
| add an alias / shell function | `shell/<NN>-name.zsh` (macOS) and/or `powershell/<NN>-name.ps1` (Windows), loaded in name order | new terminal |
| add a token for an MCP server | `mcp/.env` (+ the name in `mcp/.env.example`), use as `${VAR}` in `upstreams.toml` (`${VAR?}` if optional) | re-run setup |
| add a machine-only PATH | `~/.zshrc` / `~/.zprofile` (outside git) | new terminal |

Removing a key from `config/*settings.json` does **not** remove it from your settings. Delete it there by hand.
`<YOUR_...>` placeholders in `config/` never overwrite a real value and never count as a difference.
