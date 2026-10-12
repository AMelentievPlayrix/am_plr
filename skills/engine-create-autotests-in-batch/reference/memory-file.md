# Memory file

The batch's long-term memory. It survives context compaction, so it must hold everything the orchestrator
would need to continue from a cold start. Real examples: `am_plr/artifacts/log/firebase.md` (analysis stage)
and `am_plr/artifacts/log/sentry.md` (execution stage).

## Path checks — before the first write

1. **No path given:** ask the user for one and do nothing else. Never pick a path yourself.
2. **Inside a git repo:** run `git -C <dir> rev-parse --show-toplevel`, then `git check-ignore -q <path>`.
   - Ignored (e.g. `am_plr/artifacts/`, `vso-engine-autotests/artifacts/`), or not in a repo: fine.
   - Tracked or untracked-but-visible in **another** repo (product docs, perfect-project, a team repo): it would
     show up in that repo's `git status`. Warn the user, ask whether to keep that path or choose another, and
     wait for the answer.
   - Inside vso-engine-autotests but not ignored: same warning. A batch subagent switching branches would
     carry the file around, and `am:commit` could sweep it up.
3. **Never commit it**, in any repo.
4. **Existing content:** read the whole file. If it holds an earlier run of this batch, resume (see below).
   If it holds something else, stop and ask: do not append a batch to an unrelated file.

## Resume

Find the stage from the file:

| What the file shows | Continue with |
|---|---|
| Skeleton, some per-case sections missing | Launch analysis subagents only for the missing cases |
| All cases analysed, no § Plan | Cross-checks, bottom line, plan |
| § Plan present, no approval in "Batch events" | Present the plan again and ask for approval |
| Approval recorded | The first item in "Merge order" that is not `green PR` / `draft PR` / `blocked` / `merged` |

A subagent killed with the session leaves its branch checked out, uncommitted work and a switched `.env`, and
often nothing in its log section. Do not reset any of it: resume the agent (SendMessage) or brief a fresh one with
exactly that state and the runs already used (read its run logs). Re-arm the watchdog ([execution.md](execution.md)
§ Before the first item).

Before resuming phase 2, check the actual state: branches on origin, PRs (`gh pr list --author @me`),
and `git status` of vso-engine-autotests. If they disagree with the file, trust the repo and GitHub. Record
the correction as a batch event.

## Layout

Sections in this order. The orchestrator owns every section except a per-case section during phase 2,
which belongs to that item's subagent.

```markdown
# Batch: <parent task name>

- Parent Asana task: <url> (gid <gid>)
- Repo: /Users/playrix/projects/vso-engine-autotests (base: origin/master <sha> at start)
- Product source (read-only): /Users/playrix/projects/perfect-project
- Skill: am_plr/skills/engine-create-autotests-in-batch (per item: engine-create-autotest + batch overrides)
- Host: <macOS/Windows>; author initials: <am>
- Started: <YYYY-MM-DD>
- Current goal: <analysis | waiting for approval | execution | after merges>

## Bottom line (<date>)          ← added at the end of phase 1, kept at the top
## Blockers
## Task table
## Plan                          ← phase 1 output; includes "Merge order"
## Known repo facts (origin/master <sha>)
## Batch events
## Shared findings
## VSO-<id>                      ← one per case (framework items: ## F<n> <slug>)
## Summary (<date>)              ← end of phase 1: verdict groups, blockers, shared work, open questions
## Asana summary                 ← at the end: what was posted, story gids
```

### Blockers

The Asana dependencies of the subtasks. Link the blocker task itself. Quote a comment only when it changes
the meaning.

| Blocker | Description | Blocks (this batch) |
|---|---|---|
| [<gid>](<url>) | <blocker task name> | VSO-<id>, VSO-<id> |

### Task table

| Case | Asana subtask | Blocker | Solvable in autotests only | Status | Comments |
|---|---|---|---|---|---|

- *Solvable in autotests only*: `yes` / `partly` / `no` / `n/a` (no blocker).
- *Status*, phase 1: `not analysed` → `analysed: automatable` / `analysed: automatable with caveats` /
  `analysed: not automatable` (+ `without product change` or `manual`).
- *Status*, phase 2: `in progress` → `green PR` / `draft PR` / `blocked by <item>` / `out of scope` → `merged`.
- *Comments*: platforms, the substitute checks, what a first run must prove. In phase 2 add the branch, the
  PR, runs used and the device, and replace the analysis text only if it is no longer true.

### Plan and Merge order

The approved plan in short form (scope, framework items, test items, proposed Asana actions, open
questions), then:

| # | Item | Branch | Base | Depends on | PR | Status |
|---|---|---|---|---|---|---|
| F1 | <framework item> | feature/<initials>/<slug> | master | — | | planned |
| T1 | VSO-<id> <title> | feature/<initials>/test_<id>_<slug> | F1 branch | F1 | | planned |

`Base` is the branch the item's branch and PR are based on. Update `Base` when GitHub retargets a PR after a merge.

### Known repo facts

The verified results of the repo survey: paths with line numbers, on the base commit. Facts only.

### Batch events

Timestamped list (`- YYYY-MM-DD HH:MM (orchestrator): ...`): initialisation, subagents launched,
approval (quote what the user approved or changed), each item finished and verified, Asana posts with story
gids, user merges, rebases with new head SHAs, reruns with BrowserStack build links, and your own mistakes
and how you fixed them.

### Shared findings

Anything that matters to more than one case. Tag each entry with its source (`Source: VSO-<id> analysis`).
Use `RESOLVED:` for a disagreement you settled in source, with file:line and the commit you read. Use
`CORRECTS:` when new evidence overturns an earlier entry, and say which rows changed.

### Per-case section `## VSO-<id>`

- Phase 1, written by the orchestrator: the analysis summary. Date, verdict, platforms, each step and how
  it is checked, blocker assessment, needed changes, what a first run must prove.
- Phase 2, written by the item's subagent: append only, `- YYYY-MM-DD HH:MM: ...`. Branch, each commit
  (sha + subject), each run (platform, n/5, device, result, failing step, build link), diagnosis and change,
  `.env` restore, push, PR, and the prepared Asana comment text. The orchestrator adds verification lines
  marked `(orchestrator)`.

Framework items get the same kind of section, headed `## F<n> <slug>`.

## Write discipline

- Write first, then reply. A fact that only exists in the chat is lost at the next compaction.
- Edit only your own sections. Use Edit with unique anchors and never rewrite the whole file. Re-read the
  section before you edit it, because a subagent may have appended to it.
- Facts, not intentions: "Run Android 2/5 FAILED at <step>", not "will try X".
- No secrets, tokens, `.env` contents or personal data. Device ids, build links and SHAs are fine.
