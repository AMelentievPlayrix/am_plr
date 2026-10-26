# release-check

Run the release check for a PerfectProject minor version: start the TeamCity builds, wait, analyse,
report, and close the Asana subtasks when everything is good.

```
/am:release-check <minor version> <auto|perf|both> [Asana container or subtask links] [Slack thread link] [assignee]
/am:release-check 2026.2.7 both https://app.asana.com/.../<container task> https://playrix.slack.com/archives/C0CB6H4N672/p1793004591268139
/am:release-check 2026.2.7 perf
```

**What it does**

1. Finds the release subtasks ([Render], [OSnP/Resources], [GameUI], [Perf]) and the TeamCity builds for
   them (`config/build_mapping.json`), checks those configs and the branch exist.
2. Shows the plan and asks before starting anything.
3. Starts the builds itself and waits for them (`scripts/wait_builds.py` under Monitor).
4. Analyses: failed tests and logs for autotests (a red build is not a bug until the cause is known), the
   perf-report scripts for perf.
5. Reports in chat with Russian drafts (Asana comments and the Slack reply), then asks before touching
   Asana or Slack.
6. If all is good: comments on each subtask, assigns it (Anton Melentiev unless you name someone) and
   completes it, then replies in the Slack thread under your name. If not: shows what is wrong and asks.

It asks whenever something is missing or unclear: no tasks, an unknown build config, an unclear branch,
an ambiguous assignee.

**Needs**

- MCP servers `teamcity`, `asana`, `victoriametrics`, `slack` (declared in `upstreams.toml`). Slack: authorise
  it once in `/mcp` (OAuth as yourself); without it the skill skips the Slack reply.
- `TEAMCITY_TOKEN` in `am_plr/mcp/.env` (the wait script reads it there too).
- VPN for the perf analysis; the perf-report skill in perfect-project.

Intermediate files: `/tmp/release-check-<version>-<date>/` and `/tmp/perf-report-<branch>-<date>/`.

Instructions for Claude: [SKILL.md](SKILL.md).
