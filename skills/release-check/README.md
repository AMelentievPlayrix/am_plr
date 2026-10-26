# release-check

Run the release check for a PerfectProject minor version: start the TeamCity builds, wait, analyse,
report, and close the Asana subtasks when everything is good.

```
/am:release-check <minor version> <auto|perf|both> [Asana container or subtask links] [Slack thread link] [existing build links] [assignee]
/am:release-check <X.Y.Z> both <Asana container link> <Slack thread link>
/am:release-check <X.Y.Z> perf, the bundle is already running: <TeamCity build link>
```

**What it does**

1. Finds the release subtasks ([Render], [OSnP/Resources], [GameUI], [Perf]) and the TeamCity builds for
   them (`config/build_mapping.json`), checks those configs and the branch exist.
2. Shows the plan and asks before starting anything. Builds you already started (give their links) are
   taken over instead of started again.
3. Starts the remaining builds and waits for all of them (`scripts/wait_builds.py` under Monitor). A build
   stuck in the queue - no compatible agent, or queued over an hour after its dependencies finished - is
   reported, not waited on forever.
4. Analyses: failed tests and logs for autotests (a red build is not a bug until the cause is known), the
   perf-report scripts for perf.
5. Reports in chat with Russian drafts (Asana comments and the Slack reply), then asks before touching
   Asana or Slack.
6. If all is good: comments on each subtask, assigns it (Anton Melentiev unless you name someone) and
   completes it, then replies in the Slack thread under your name. If not: offers to post the comments
   without completing, rerun builds, or stop. Every write waits for your approval.

It asks whenever something is missing or unclear: no tasks, an unknown build config, an unclear branch,
an ambiguous assignee.

**Needs**

- MCP servers `teamcity`, `asana`, `victoriametrics`, `slack` (declared in `upstreams.toml`). Slack: authorise
  it once in `/mcp` (OAuth as yourself); without it the skill skips the Slack reply.
- `TEAMCITY_TOKEN` in `am_plr/mcp/.env` (the wait script reads it there too).
- VPN for the perf analysis; the perf-report skill in perfect-project.

Intermediate files and run state: `/tmp/release-check-<version>/` (a rerun of the same version offers to continue) and `/tmp/perf-report-<branch>-<date>/`.

Instructions for Claude: [SKILL.md](SKILL.md).
