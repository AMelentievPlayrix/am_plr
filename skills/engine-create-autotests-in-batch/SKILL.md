---
name: engine-create-autotests-in-batch
description: Automate a batch of Qase cases in vso-engine-autotests, where the cases are the subtasks of one Asana parent task. Blockers first - analyse every case and blocker in parallel, plan and fix the blockers (C++ TestSDK, Python framework, Qase-side) and validate them on devices - then implement the tests one at a time through engine-create-autotest, merge each green PR, close the Asana subtasks, set Qase automation, log the work, and hand off platforms this host cannot run. State lives in a long-term memory folder. Use for "automate all cases under this Asana task", "/am:engine-create-autotests-in-batch <parent task> [memory folder]".
argument-hint: "<Asana parent task link> [memory folder]"
disable-model-invocation: true
allowed-tools: Read Edit Write Bash(git *) Bash(gh pr *) Bash(make *) Bash(grep *) mcp__qase mcp__asana mcp__teamcity Agent Skill Monitor CronCreate CronDelete SendMessage TaskStop
---

# Automate a batch of Qase cases

You are the orchestrator. Blockers are proven and fixed before any test is written. After the user approves the
test plan, the batch runs on its own to the end: tests, merges, Asana, Qase, logging. Anything that needs the user
goes under **Needs you** in `status.md` while the work moves on.

The per-case work belongs to [engine-create-autotest](../engine-create-autotest/SKILL.md) and its reference files.
Do not restate its rules here or in briefs; refer to them by path. Subagents cannot load that skill with the Skill
tool (`disable-model-invocation`), so briefs tell them to read its files.

Language: chat and memory in English; commits, PRs, Asana in Russian ([rules/communication.md](../../rules/communication.md)).
Item ids (`A`, `F1`, `T2`) and phase names stay inside the batch ([execution.md](reference/execution.md) § Text for
people outside the batch).

## Use this when

- An Asana parent task (e.g. «[Engine/SDK] Автоматизация: Marketing») has subtasks that each name one Qase case
  `VSO-<id>`, and the cases should be automated together.

## Do not use this when

- There is one case: `/am:engine-create-autotest`. A test is broken: `/am:engine-fix-autotest`.

## Inputs

| Input | Rule |
|---|---|
| Asana parent task link | Required. The gid is the last numeric segment. |
| Memory folder | Optional. Without it, phase 0 proposes one. With one that has `resume.md`, this is a resume: read it first ([memory.md](reference/memory.md) § Resume). |

## Reference

| Phase or topic | File |
|---|---|
| Memory folder: files, templates, resume, write discipline | [reference/memory.md](reference/memory.md) |
| 1 Analysis: Asana, repo survey, blocker verification, verdicts | [reference/analysis.md](reference/analysis.md) |
| 2-3 Blocker plan and fixes: worktrees, TeamCity build, device validation, merge, close | [reference/blockers.md](reference/blockers.md) |
| 4-6, 8 Test plan, tests loop, follow-ups, close-out | [reference/execution.md](reference/execution.md) |
| Per-PR merge routine and the final link list | [reference/merge-loop.md](reference/merge-loop.md) |
| 7 Separate-platform track and hand-off | [reference/platform-track.md](reference/platform-track.md) |
| Briefs: analysis, blocker fix, test item | [reference/briefs.md](reference/briefs.md) |
| Tool, environment and permission gotchas | [reference/gotchas.md](reference/gotchas.md) |
| Scripts: `run_on_platform.py` (device runs), `qase_case.py` (Qase writes) | [../engine-create-autotest/scripts/](../engine-create-autotest/scripts/run_on_platform.py), [scripts/](scripts/qase_case.py) |

## Phases

| # | Phase | What | Gate |
|---|---|---|---|
| 0 | Memory | Propose `<am_plr>/artifacts/memory/YYYY-MM-DD_<slug>/` or an active folder from INDEX.md, and **ask** ([rules/long-term-memory.md](../../rules/long-term-memory.md)) | the user picks |
| 1 | Analysis | Read-only. One subagent per case, in waves of at most 20. Every blocker verified in source: TRUE / FALSE / PARTLY | - |
| 2 | Blocker plan | Fix type and design per real blocker; shared helpers as framework items; Asana actions naming each task; draft test scope | **approval 1** |
| 3 | Blocker fixes | Worktrees (plan, `am:plan-review`, implement), PRs, TestSDK built, one throwaway device test over all fixes, framework PRs merged, perfect-project PRs reviewed (the merge goes under **Needs you**) | blockers merged, pending a perfect-project merge, or deferred |
| 4 | Test plan | Scope, simplest first, all from master, platforms; the allow rules to add | **approval 2** |
| 5 | Tests | One subagent at a time with a watchdog. Verify, run the merge routine, start the next from fresh master | queue empty |
| 6 | Follow-ups | One task, branch and PR for code follow-ups; the rest under **Needs you** | - |
| 7 | Platform track | "(<Platform>)" subtasks and `handoff-<platform>.md` for another host; fold-back | - |
| 8 | Close-out | Parent summary, `/am:log`, INDEX done, final link list | - |

**What each approval covers.** Record both, quoted, in plan.md and events.md.
- **Approval 1:**
  - the Asana actions listed in the blocker plan, including which blocker tasks may be closed;
  - perfect-project edits for the listed fixes, only in worktrees;
  - merging the validated vso-engine-autotests framework PRs.
- **Approval 2:**
  - implementing the tests;
  - merging each green PR without waiting for review;
  - Asana comments and marking the case subtasks done;
  - Qase automation = automated;
  - follow-ups within scope;
  - the platform-track subtasks.

Without them, nothing in phases 3 and 5-7 starts.

## Memory

The folder is the source of truth: context gets compacted, the folder survives ([memory.md](reference/memory.md)).
- `status.md` is the user's one screen.
- `resume.md` is your entry point after any restart.
- Write every fact as soon as you learn it, before replying: a report, a verdict, a branch, a PR, a run, a merge, an
  approval.
- Only the orchestrator edits the shared files. A running subagent appends only to its own item file.
- Never write secrets, and never commit the folder.

## Lessons that shape the process

Each cost a batch real time. Details are in [gotchas.md](reference/gotchas.md).

- **Blocker text is a claim.** One of four Asana blockers was false, and another was real for 6 of its 15 cases.
  Verify each in product source before planning.
- **Verify before you propagate.** A subagent claim that changes another case is checked in source (`RESOLVED:` with
  file:line). New evidence that overturns an assumption is a `CORRECTS:` entry, and the affected rows are revised.
- **"Absent" needs a positive control.** One uncommitted control run in which the thing is present and the check
  fails.
- **No stacks.** Squash merges broke stacked PRs, force-push is refused, and helpers got copied. Branch from master,
  merge green PRs at once, and make shared helpers framework items early.
- **Never read or print `.env`.** Runs go through `run_on_platform.py`, Qase writes through `qase_case.py`.
- **Flaky tools.** Read the state before any retry: Asana stories, `gh pr view`. A blind retry posted duplicates.
- **A refused command is never worked around.** It goes under **Needs you** with the exact command.
- **State outlives a test** (macOS GlobalVars, SDK settings): shared reset steps clear it
  (authoring-rules.md § State between tests).
- **Capabilities and region are per BrowserStack run**, results can depend on the device (record it every run),
  and one-shot events cannot be retried in-session.

## Hard prohibitions

- No phase 3 action before approval 1; no phase 5-7 action before approval 2.
- No edits outside the memory folder in phases 1-2. perfect-project only for approved blocker fixes, only in
  worktrees, never on the main checkout.
- Never merge perfect-project PRs: the user runs `/am:merge-pp`.
- No stacked branches, cherry-picked copies or force-pushes.
- Never edit, print or commit `.env`. Never put tokens in a shell command.
- Close or re-status only the Asana tasks an approval covers. Everything else is comment-only.
- Everything in engine-create-autotest's Hard prohibitions, for every item.
