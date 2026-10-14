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
| All cases analysed, no § Plan | Cross-checks, status view (both tables), plan |
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

The top of the file is the **status view**: two tables a person can read in one minute without scrolling into
the logs. Everything below them is working memory. Sections in this order. The orchestrator owns every section
except a per-case section during phase 2, which belongs to that item's subagent.

```markdown
# Batch: <parent task name>

- Parent Asana task: <url> (gid <gid>)
- Repo: /Users/playrix/projects/vso-engine-autotests (base: origin/master <sha> at start)
- Product source (read-only): /Users/playrix/projects/perfect-project
- Skill: am_plr/skills/engine-create-autotests-in-batch (per item: engine-create-autotest + batch overrides)
- Host: <macOS/Windows>; author initials: <am>
- Started: <YYYY-MM-DD>
- Current goal: <analysis | waiting for approval | execution | after merges>

## Task table                    ← status view, part 1: one row per case, always current
## Blockers                      ← status view, part 2: one row per blocker (A, B, C, ...), always current
## How to resume                 ← cold-start steps + watchdog prompt (phase 2)
## Plan                          ← phase 1 output; includes "Merge order"
## Known repo facts (origin/master <sha>)
## Batch events
## Shared findings
## VSO-<id>                      ← one per case (framework items: ## F<n> <slug>)
## Research: <topic>             ← optional, one per probe or investigation
```

Do not add other summary sections (bottom line, summary, investigation result, a separate list of Asana
blockers). Their content belongs in the two status tables. When an old summary is superseded, fold what is
still true into the tables and delete it; the history stays in "Batch events".

### Task table

```markdown
## Task table (updated <YYYY-MM-DD>)

Status: 🟢 green PR · 🟡 draft PR · 🔵 in progress · ⚪ not started · 🔴 blocked (data/tests side) ·
⛔ blocked (product/infra) · ✅ merged. Blockers: see § Blockers.
Framework PRs (merge first, in order): #<n> <what> → #<n> <what>.

| Case | Asana | Platforms | Blockers | PRs | Status | Comment |
|---|---|---|---|---|---|---|
| VSO-<id> <title> | [subtask](<url>) | Android, iOS | A, C (Android); D (iOS) | [#<n>](<url>) on [#<n>](<url>) | 🟢 green PR | <one line> |
```

- **Asana**: a short link text (`[subtask](url)`), never a bare URL.
- **Blockers**: only ids from § Blockers, split by platform when they differ; `—` when none.
- **PRs**: the case's own PR and the PRs it stacks on. `—` when none.
- **Status**: one emoji plus a short word. In phase 1, before any PR, use ⚪ with the verdict in the comment
  (e.g. `⚪ not started — automatable with caveats`).
- **Comment**: one line, only what the blocker ids and status don't already say (a substitute check, what a first
  run must prove, a review the PR waits for). Details go to the per-case section.
- Order rows by status: green, draft, in progress, not started, blocked.

### Blockers

```markdown
## Blockers

<one line: how many blockers the tests side can solve alone>

| Id | Blocker | Cases | Python alone? | Who has to act / way out | Asana |
|---|---|---|---|---|---|
| A | <what is missing and the evidence, short> | VSO-<id>, ... | ❌ / ✅ / ✅ done | <team or person, and the concrete steps; then what the tests side adds> | [<short name>](<url>) / none yet |

Not a real blocker: [<short name>](<url>) — <why>.
Next startable work: <blocker id → what it unblocks>.
```

- One row per blocker, whatever its source: an Asana dependency of a subtask, a hidden blocker the analysis
  found, a data source that turned out missing, a product or infra change. Ids are letters, stable once given;
  never reuse a letter.
- **Python alone?**: ✅ when the change fits in vso-engine-autotests (new steps, services, utils, config);
  ❌ when another team must act first (product code, access, infra, a Qase decision); `✅ done` when a batch PR
  solved it (name the PRs). Mixed cases are ❌, with the tests-side part named in the next column.
- **Who has to act / way out**: the owner and the concrete request, numbered when there are several steps; then
  what the tests side adds afterwards.
- **Asana**: link the blocker task with a short text. Blocker tasks the batch creates for framework items go here
  too. An Asana dependency that is not a real blocker goes under the table as "Not a real blocker".

### Keeping the status view current

Update both tables in the same edit as the event that changes them, before you reply to the user: a verdict
arriving or changing, a PR opened, turned draft or green, a merge, a rebase, a probe result, a new blocker or a
solved one. Change the `updated <date>` stamp. Log the change in "Batch events". After every user request that
changes scope or status, re-read both tables and fix anything stale.

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
