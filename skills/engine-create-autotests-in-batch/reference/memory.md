# Batch memory

The batch uses long-term memory per [rules/long-term-memory.md](../../../rules/long-term-memory.md): one folder,
`<am_plr>/artifacts/memory/YYYY-MM-DD_<slug>/`, which the user agreed to (phase 0). The rule sets the four generic
files and their limits. This file adds the batch files and their formats.

## Layout

| File | Owner | Holds |
|---|---|---|
| `status.md` | orchestrator, for the user | One screen (40 lines max). Template below |
| `resume.md` | orchestrator | Entry point (60 lines max). Template below |
| `events.md` | orchestrator | Append-only `- YYYY-MM-DD HH:MM: ...`: approvals (quoted, with what they cover), launches, verifications, merges, Asana/Qase writes with ids, mistakes |
| `facts.md` | orchestrator | Repo facts with file:line and base commit, `RESOLVED:` / `CORRECTS:` shared findings, environment facts for briefs (non-secret run settings per platform, build numbers, device ids). 150 lines max |
| `board.md` | orchestrator | Task table, Blockers table, Merge order, Follow-ups (formats below) |
| `plan.md` | orchestrator | Blocker plan (phase 2) and test plan (phase 4), each with its approval line |
| `items/<id>_<slug>.md` | orchestrator; the item's subagent while it runs | One per case, blocker fix or framework item |
| `handoff-<platform>.md` | orchestrator | Self-contained prompt for another host ([platform-track.md](platform-track.md)) |

Item ids are internal (`A`..`Z` for blockers, `F1` for framework items, `T1` for tests). They never appear in
commits, PRs or Asana.

## status.md (for the user)

```markdown
# <batch name> - status (updated YYYY-MM-DD HH:MM)
Phase: <n>/8 <name> - <one line: where we are>
Next: <what the agent does next>

## Needs you
- <approval, decision, merge command, access or refused command, with link>   (or: nothing)

## Left
- <item or group> - <state>          (10 lines max; "+N more in board.md")

## Done
- Tests: <n> of <m> merged; blockers fixed: <k>; <Asana parent link>
- Last merged: [#<n>](url) <what>
```

Update it on every phase change, every change to **Needs you**, and after each merge. Nothing else goes here:
history goes in events.md, detail in board.md.

## resume.md (agent entry point)

```markdown
# Resume: <slug>
Skill: am_plr/skills/engine-create-autotests-in-batch (phase files in reference/)
Read order: this file -> status.md -> `tail -40 events.md` -> the files the current phase needs (below).

## Now
Phase <n> <name>: <next concrete action>. Phase file: reference/<file>.md
Needs: board.md § <table>; items/<id>.md for the running item.

## Live state
- vso-engine-autotests: branch <..>, tree <clean/dirty>; worktrees: <paths>
- Running subagent: <item> (<agent name>, launched HH:MM) | none
- Watchdog cron: <id> | not armed (re-arm after a restart with the prompt below)
- Pending writes: <Asana comment for X, story not confirmed> | none
- Builds in artifacts/app: <TeamCity build numbers>

## Watchdog prompt
<the exact prompt from execution.md § Watchdog, filled in with this folder's path>
```

## board.md

**Task table**, one row per case, ordered by status. Above it, one line defining "fully": every expected result
has an automated check (named substitutes count, commented-out checks do not).

```markdown
Status: ✅ merged · 🟢 green PR · 🟡 draft PR · 🔵 in progress · ⚪ not started · 🔴 blocked (tests side) · ⛔ blocked (product/infra/Qase)

| Case | Asana | Platforms | Blockers | PR | Status | Comment |
|---|---|---|---|---|---|---|
| VSO-<id> <title> | [subtask](<url>) | iOS, Android, macOS | A (Android); — (iOS) | [#<n>](<url>) | ✅ merged <sha> | <one line: substitute, risk> |
```

**Blockers table**, one row per blocker from any source (an Asana dependency, a hidden blocker, a Qase mismatch,
infra). Letters are stable and never reused.

```markdown
| Id | Blocker (evidence) | Real? | Cases | Fix type | Fix / owner | Asana | PR | Status |
|---|---|---|---|---|---|---|---|---|
| A | <what is missing, file:line> | TRUE / FALSE / PARTLY (<which cases>) | 16972, ... | C++ product / Python framework / Qase-side / infra | <design or who acts> | [<short>](url) | [#<n>](url) | <state> |
```

**Merge order**:

```markdown
| # | Item | Repo | Branch | PR | Validated by | Status |
|---|---|---|---|---|---|---|
| F1 | <framework item> | vso-engine-autotests | feature/<initials>/<slug> | [#<n>](url) | device validation <date> | ✅ merged <sha> |
```

**Follow-ups**: one line each, `- <what> - <why> - <owner: agent | user | team> - <state>`.

## items/<id>_<slug>.md

```markdown
# <id> <VSO-id or blocker name>
Status: <one line, kept current>
## Analysis        (phase 1, orchestrator: verdict, platforms, steps and how each is checked, risks)
## Plan            (blocker fixes: the subagent's plan, 60 lines max; review result)
## Log             (append-only "- YYYY-MM-DD HH:MM: ...": branch, commits, runs with device and build link, PR)
## Prepared Asana comment   (Russian, html_text; posted by the orchestrator at merge)
```

The subagent appends only to its own item file while it runs. The orchestrator adds `(orchestrator): Verified - ...`
lines.

## Resume

Read resume.md first. Then check the real state against it: `git -C <repo> status`, branches and worktrees,
`gh pr list --author @me --state all`, and the Asana stories of pending writes. Trust the repo, GitHub and Asana
over the memory, fix the memory, and log the correction in events.md.

| What the memory shows | Continue with |
|---|---|
| No plan.md, some items lack § Analysis | Phase 1: launch analysis only for the missing cases |
| All analysed, no blocker plan | Phase 2: write the blocker plan |
| Blocker plan without its approval line | Present it again and ask |
| Approval 1, blockers not all merged or validated | Phase 3, from board.md § Merge order |
| Blockers done, no test plan or no approval 2 | Phase 4 |
| Approval 2 | Phase 5: the first Merge-order row not merged, draft or blocked |
| Queue empty | Phases 6-8 |

A subagent killed with the session leaves its branch checked out and work uncommitted. Do not reset it. Resume
the agent (SendMessage) or brief a fresh one with exactly that state and the runs already used. Re-arm the
watchdog.

## Write discipline

- Write first, then reply. A fact that exists only in the chat is lost at the next compaction.
- Use Edit with unique anchors. Re-read a file before editing it, because a subagent may have appended to it.
- Facts, not intentions. No secrets, `.env` values or tokens.
- Never commit the folder (`artifacts/` is git-ignored).
