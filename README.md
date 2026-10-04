# am_plr

My personal Claude Code + VS Code setup, applied to all projects at once.
It sits **on top of** team repos (perfect-project, vso-engine-autotests) and never conflicts with them.

## Setup, step by step

1. **Tokens and shell** (first time on a machine; needs [uv](https://docs.astral.sh/uv/)):
   ```bash
   cp ~/projects/am_plr/.env.example ~/projects/am_plr/.env      # fill in tokens; .env is git-ignored
   echo 'source ~/projects/am_plr/shell/init.zsh' >> ~/.zshrc   # exports .env + loads aliases/prompt
   ```
   Open a new terminal (and restart VS Code) so the tokens are in the environment.
2. **Run setup** (again any time something changes):
   ```bash
   ~/projects/am_plr/scripts/setup.sh
   ```
   It warns about any token the MCP config needs that is still empty in `.env`.
3. **MCP servers**: paste the `claude mcp add-json ...` commands setup prints. Only Asana needs a one-time
   manual OAuth step (also printed). The config holds `${QASE_API_TOKEN}`-style references, not tokens.
4. **Settings** (only if setup shows `~ Claude Code` / `~ VS Code`): review each with the printed `diff`,
   then run the printed `cp`.
5. **Restart** Claude Code. Check with `/mcp` and `/skills`.

### What "all done" means after step 2

| Done automatically                                                        | Where                                        |
|---------------------------------------------------------------------------|----------------------------------------------|
| My skills / agents available in every project                             | symlinks in `~/.claude/skills`, `~/.claude/agents` |
| My rules (`rules/*.md`) loaded in every project                            | symlink `~/.claude/rules/am_plr`             |
| MCP config generated                                                      | `artifacts/generated/mcp.json`               |
| Claude Code / VS Code user settings generated (yours + am_plr keys)       | `artifacts/generated/{claude,vscode}-settings.json` |

**Never changed by setup:** your MCP config, `~/.claude/settings.json`, VS Code user settings and any project file.
Setup only generates files in `artifacts/generated/` and prints how to apply them (steps 3–4).

## What lives where

```
skills/am-<name>/SKILL.md       my skills (always am- prefix) -> every project
agents/<name>.md                my subagents           -> every project
rules/*.md                      my rules, loaded in every session (`paths:` frontmatter to scope)
mcp/<name>/                     code of my own MCP servers (configured in upstreams.toml)
config/claude/settings.json     model, effort, permissions I want everywhere
config/vscode/settings.json     editor settings I want everywhere (autosave, 120 ruler, terminal, Python)
shell/*.zsh                     aliases, functions, prompt; all loaded by shell/init.zsh (sourced from ~/.zshrc)
.env                            all tokens, git-ignored (template: .env.example); exported by shell/init.zsh
upstreams.toml                  team repos I follow + all MCP servers (theirs and mine)
```

## How conflicts are avoided

- **Team skills/agents/rules stay in their repos** and load from there. am_plr never copies them.
- **Our skills are named `am-<name>`**, so they don't collide with team ones. If one still does (it would hide
  the team version in every project), setup reports it and asks to rename ours. It's never linked as-is.
- **MCP**: a repo's own `.mcp.json` always wins over user-level config, so team config can't break.
- **Settings**: common settings live in am_plr; project-specific ones (interpreter, pytest args, launch.json)
  stay in each project's `.vscode/`. Generated files add am_plr keys on top of yours and drop nothing.

## Changing things

| I want to…                         | Do                                                       | Re-run setup? |
|------------------------------------|----------------------------------------------------------|---------------|
| edit a skill / rule               | just edit it                                             | no            |
| add / rename / delete a skill or agent | change `skills/am-<name>/` or `agents/`           | yes           |
| change editor / Claude settings    | edit `config/`                                           | yes, then copy the printed command |
| add my own MCP server              | code in `mcp/<name>/` (deps inline, run with `uv run --script`) + `[mcp.<name>]` in `upstreams.toml` | yes, then copy the printed command |
| use a team repo's MCP server       | add `[mcp.<name>]` to `upstreams.toml`                   | yes, then copy the printed command |
| follow another team repo           | add `[upstream.<name>]` to `upstreams.toml`              | yes           |
| add an alias / shell function      | new or existing `shell/<NN>-name.zsh` (loaded in name order) | no, open a new terminal |
| add a token                        | `.env` (+ the name in `.env.example`), use as `${VAR}` in MCP config | yes, new terminal |
| add a machine-only PATH            | `~/.zshrc` / `~/.zprofile` (outside git)                 | no            |

Removing a key from `config/*settings.json` does **not** remove it from your settings. Delete it there by hand.
