# am_plr

My personal Claude Code + VS Code + shell setup, applied to all projects at once.
It sits **on top of** team repos (perfect-project, vso-engine-autotests) and never conflicts with them.

- **Skills** ship as a Claude Code plugin, `am-plr`. Use them in any project as `/am-plr:<skill>`.
- **Rules, my own MCP servers, settings, shell** are prepared by `scripts/setup.sh`.

## Setup, step by step

Needs [uv](https://docs.astral.sh/uv/) and `jq`.

1. **Run setup** (again any time something changes):
   ```bash
   ~/projects/am_plr/scripts/setup.sh
   ```
2. **Do the "Next steps" it prints at the end.** Only what's still missing is listed, in order:
   - create `.env` from `.env.example` and fill in the tokens (git-ignored);
   - add `source ~/projects/am_plr/shell/init.zsh` to `~/.zshrc` (loads tokens, aliases, prompt);
   - install the plugin: in Claude Code run `/plugin marketplace add ~/projects/am_plr`, then `/plugin install am-plr@am-plr`;
   - copy my MCP servers from `artifacts/generated/mcp.json` into `"mcpServers"` of `~/.claude.json`
     (keep your existing entries; close Claude Code first);
   - review the Claude Code / VS Code settings with the printed `diff`, then run the printed `cp`;
   - optional: add team MCP servers (qase, cats-mcp-server, …) to the same `"mcpServers"` as their repos' docs
     describe (`perfect-project/cats2/docs/mcp-setup.md`). The engine skills need `qase` and `cats-mcp-server`.
3. **Restart** the terminal, VS Code and Claude Code. Check with `/plugin`, `/mcp` and `/skills`.
4. Run setup again: when everything is in place it prints **All set**.

### What setup does by itself

| Done automatically | Where |
|---|---|
| My rules (`rules/*.md`) loaded in every project | symlink `~/.claude/rules/am_plr` |
| Config for my own MCP servers generated | `artifacts/generated/mcp.json` |
| Claude Code / VS Code settings generated (yours + am_plr keys) | `artifacts/generated/{claude,vscode}-settings.json` |
| Checks: plugin installed, tokens set, `~/.zshrc` sources am_plr, skills call only configured MCP servers | printed as warnings / next steps |

**Never changed by setup:** plugin install, MCP config, `~/.claude/settings.json`, VS Code settings, `~/.zshrc`
and any project file. You run those steps yourself from the printed list.

## Using the skills in a project

Open Claude Code in any project. The plugin is enabled for all of them:

```
/am-plr:commit                  split changes into logical commits
/am-plr:describe-work           Asana task + GitHub PR for the changes
/am-plr:engine-create-autotest  new vso-engine-autotests test from a Qase case
/am-plr:engine-fix-autotest     repair a broken autotest from an Asana task
/am-plr:engine-iap-port         port an iOS in-app purchase test to macOS / UWP
/am-plr:prompt-writer           turn a rough idea into a good prompt
```

Claude also picks them up automatically from their descriptions. Team skills keep their own names
(e.g. `/perf-report`); ours always carry the `am-plr:` prefix, so the two never clash.
Edits to a skill apply in the next session, or right away with `/reload-plugins`.

## What lives where

```
.claude-plugin/                 plugin manifest + local marketplace (this repo is both)
skills/<name>/SKILL.md          my skills -> /am-plr:<name> in every project
agents/<name>.md                my subagents -> am-plr:<name>
rules/*.md                      my rules, loaded in every session (`paths:` frontmatter to scope)
mcp/<name>/                     code of my own MCP servers (configured in upstreams.toml)
upstreams.toml                  team repos I follow, my own MCP servers, links to team MCP docs
config/claude/settings.json     model, effort, permissions I want everywhere
config/vscode/settings.json     editor settings I want everywhere (autosave, 120 ruler, terminal, Python)
shell/*.zsh                     aliases, functions, prompt; loaded by shell/init.zsh (sourced from ~/.zshrc)
.env                            all tokens, git-ignored (template: .env.example); loaded by shell/init.zsh
workspaces/*.code-workspace     VS Code multi-folder workspaces
```

## How conflicts are avoided

- **Team skills/agents/rules stay in their repos** and load from there. am_plr never copies them.
- **Skills**: plugin skills are namespaced (`am-plr:commit`), so they can't hide a team skill.
- **MCP**: am_plr prepares only my own servers. Team servers stay owned by their repos; you add them to the same
  user config from their docs, under the names their skills call (`qase`, `cats-mcp-server`, …).
- **Settings**: common settings live in am_plr; project-specific ones (interpreter, pytest args, launch.json)
  stay in each project's `.vscode/`. Generated files add am_plr keys on top of yours and drop nothing.

## Changing things

| I want to… | Do | Then |
|---|---|---|
| edit a skill or rule | just edit it | `/reload-plugins` or new session |
| add / rename / delete a skill | change `skills/<name>/` | `/reload-plugins` |
| change editor / Claude settings | edit `config/` | re-run setup, copy the printed command |
| add my own MCP server | code in `mcp/<name>/` (deps inline, `uv run --script`) + `[mcp.<name>]` in `upstreams.toml` | re-run setup, copy it from `mcp.json` |
| use a team repo's MCP server | add it to `"mcpServers"` of `~/.claude.json` from that repo's docs | restart Claude Code |
| follow another team repo | add `[upstream.<name>]` to `upstreams.toml` | re-run setup |
| add an alias / shell function | new or existing `shell/<NN>-name.zsh` (loaded in name order) | new terminal |
| add a token for my MCP server | `.env` (+ the name in `.env.example`), use as `${VAR}` in `upstreams.toml` | new terminal, re-run setup |
| add a machine-only PATH | `~/.zshrc` / `~/.zprofile` (outside git) | new terminal |

Removing a key from `config/*settings.json` does **not** remove it from your settings. Delete it there by hand.
