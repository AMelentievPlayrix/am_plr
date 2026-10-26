---
name: engine-create-autotests-in-batch
description: Automate a batch of Qase cases in vso-engine-autotests, where the cases are the subtasks of one Asana parent task. Analyse every case in parallel (read-only), propose a plan with shared framework items and a stacked merge order, then after approval implement the items one at a time through engine-create-autotest. All state lives in a memory file the user supplies. Use for "automate all cases under this Asana task", "/am:engine-create-autotests-in-batch <parent task> <memory file>".
argument-hint: "<Asana parent task link> <memory file path>"
disable-model-invocation: true
allowed-tools: Read Edit Write Bash(git *) Bash(gh pr *) Bash(make *) Bash(grep *) mcp__qase mcp__asana Agent
---

# Automate a batch of Qase cases

You are the orchestrator. Two phases, with the user's approval between them:

1. **Analysis.** Read-only everywhere except the memory file. Ends with a plan.
2. **Execution.** Starts only after explicit approval. One subagent at a time, in merge order.

The per-case work belongs to the single-case skill, [engine-create-autotest](../engine-create-autotest/SKILL.md),
and its reference files. Do not restate its rules here or in briefs (branch naming, run budget, forbidden fixes,
PR template, commit policy). Refer to them by path. Subagents cannot load that skill with the Skill tool
(`disable-model-invocation`), so their briefs tell them to read its files directly.

| Detail | File |
|---|---|
| Memory file: path checks, layout, write discipline | [reference/memory-file.md](reference/memory-file.md) |
| Repo survey, per-case analysis brief, cross-checks, verdicts | [reference/analysis.md](reference/analysis.md) |
| Phase 2 loop, per-item brief with overrides, stacking, Asana, after merges | [reference/execution.md](reference/execution.md) |

Language: chat in English; commits, PRs and Asana in Russian ([writing rule](../../rules/communication.md)).
Batch item ids (`F1`, `T2`) and stage names are internal: never put them in commits, PRs or Asana. Name the test,
case and PR instead ([execution.md](reference/execution.md) § Text for people outside the batch).

## Use this when

- An Asana parent task (a container like «[Engine/SDK] Автоматизация: SDK / Firebase») has subtasks that each
  name one Qase case `VSO-<id>`, and the cases should be automated together.

## Do not use this when

- There is one case. Use `/am:engine-create-autotest`.
- A test is broken. Use `/am:engine-fix-autotest`.

## Inputs

| Input | Rule |
|---|---|
| Asana parent task link | Required. The gid is the last numeric segment. |
| Memory file path | **Required. Never invent one.** If it is missing, ask for it and do nothing else. |

Before the first write, follow [memory-file.md](reference/memory-file.md) § Path checks. If the file already has
content, this is a resume: continue from its recorded stage and never overwrite sections you do not own.

## The memory file is the source of truth

Context gets compacted, and the memory file is what survives. Write every fact into it **as soon as you learn it,
before you reply to the user**: a report arriving, a verdict changing, a branch, a PR, a run, an approval. After a
compaction, re-read it before you do anything. Only the orchestrator edits its tables and shared sections.
Never write secrets or tokens into it.

## Phase 1 — Analysis

1. **Read Asana.** Read the parent task and every subtask: name, Qase id, dependencies (dependencies are
   blockers). Read each blocker task, both description and comments. Asana MCP calls can time out: retry once,
   then go on with what you know and record the gap.
2. **Survey the repo** on `origin/master` of vso-engine-autotests, following [analysis.md](reference/analysis.md)
   § Repo survey. If the tree is dirty, record that and leave it alone. Never modify it in phase 1.
3. **Write the skeleton** of the memory file: header, the status view (Task table + Blockers table, one row per case
   and per Asana blocker), "Known repo facts", "Batch events" ([memory-file.md](reference/memory-file.md) § Layout).
4. **Fill in the analysis brief** from [analysis.md](reference/analysis.md) § Brief, including the "SDK-specific
   hints" slot, which comes from the survey.
5. **Launch one read-only analysis subagent per case**, all in parallel and in the background. Subagents never
   write the memory file.
6. **As each report arrives**, update its row, add its section, and move anything shared into "Shared findings".
   Verify contradictions, and claims that change other cases' verdicts, in source yourself. Record later
   corrections and revise earlier rows ([analysis.md](reference/analysis.md) § Cross-checking).
7. **Bring the status view up to date**: every case row and every blocker row final for phase 1
   ([analysis.md](reference/analysis.md) § Verdicts and the status view).

## Phase 1 output — the plan

Write the plan into the memory file (§ Plan, including the "Merge order" table), then give it to the user:

1. **Understanding of the task**: scope and which cases will be implemented. By default that is only the
   "fully automatable" cases. Say which cases are left out and why.
2. **Framework items**: shared setup or capabilities, plus new steps, services or utils that several tests need.
   Each item gets its own branch.
3. **Test items**, simplest first, each naming the framework items it depends on.
4. **Branch and merge plan**: one branch per item, stacked so the PRs merge one by one
   ([execution.md](reference/execution.md) § Stacking). Stack branches, do not cherry-pick copies of commits.
5. **Validation rule**: a framework item is validated only when the first test that uses it passes on a device. If
   a shared capability fails its first device run, stop the dependent line and report. Do not work around it.
6. **Proposed Asana actions**, posted only after approval: comments on blocker tasks that turn out solvable in
   autotests, and new dependency tasks for product changes the analysis found. Every blocker task this batch
   will fix through a framework item gets assigned to the batch author when phase 2 starts
   ([execution.md](reference/execution.md) § Before the first item). List those blockers in the plan.
   Every framework item that no existing blocker task covers gets a **new blocker task**: a subtask of the
   dependencies container, assigned to the batch author, "what needs to be done to unblock what", set as a
   dependency of the subtasks it blocks ([execution.md](reference/execution.md) § Blocker tasks for framework
   items). List the proposed tasks in the plan.
7. **Open questions** for the user: inconsistent Qase expectations, region or CI needs, product owners.
8. **An explicit request for approval.** Nothing in phase 2 starts without it. Record the approval, and any
   changes the user makes, in "Batch events".

## Phase 2 — Execution

Follow [execution.md](reference/execution.md). In short:

- Run one subagent per item, in merge order, each with the per-item brief. Never run two at once: they share one
  working tree, one `.env` and one BrowserStack account.
- Before a framework item starts, create its blocker task if it has none; its PR links that task. When the PR goes
  green, comment on the task with the PR link and what was in fact done
  ([execution.md](reference/execution.md) § Blocker tasks for framework items). This applies to framework PRs added
  during execution too.
- After each item, verify its report (tree clean on master, `.env` restored, PR state), update the task and
  merge-order tables, then start the next item. Skip any item whose dependency halted, and mark it blocked.
- Watch for hangs, not only for finished subagents: the watchdog checks progress every 10 min
  ([execution.md](reference/execution.md) § Before the first item).
- At the end: post the per-subtask Asana comments from the texts the subagents prepared, and one summary comment
  on the parent task. Request a reviewer on green PRs only. Then give the user the final report.
- After the user merges PRs: rebase the stacked PRs, re-validate them on a device, and record it all
  ([execution.md](reference/execution.md) § After merges).

## Lessons from earlier batches

Each one cost a real batch time. The briefs repeat the ones that apply to subagents.

- **Verify before you propagate.** Check in source any subagent claim that changes another case. Record the
  result as `RESOLVED:` with file:line.
- **Corrections are explicit.** When new evidence overturns an earlier assumption, write `CORRECTS:` in
  "Shared findings", update every affected row, and tell the user.
- **"Absent" needs a positive control.** A "not sent / not logged" check counts only after one uncommitted control
  run, in which the thing is present and the check fails. Revert the control edit afterwards.
- **One-shot events vs auto-retry.** First install, first open and uninstall cannot be reproduced by the in-session
  auto-retry (`tests/conftest_auto_retry.py`). Such tests need an opt-out, and the fresh-install assumption must be
  proven on a device.
- **BrowserStack capabilities and region are per run, not per test** (`browserstack.yml` is generated once per run).
  A test that needs another region or capability needs its own run and CI configuration. Say so in the plan.
- **No fixed sleeps.** Wait on an observable condition. If none exists, record it as a risk instead of sleeping.
- **Record the device with every run.** Results can depend on the device model.
- **Asana MCP is flaky.** Retry once on a timeout. After a write that reported an error, read the task's stories
  before you retry, so you do not post the comment twice.

## Final report to the user

Bring the status view up to date first, then report from it:

1. The **Task table** (same columns as in the memory file).
2. The **Blockers table**, with "Python alone?" and who has to act.
3. Next startable work, merge order, Asana comments posted, and the memory file path.

## Hard prohibitions

- No phase 2 action before explicit approval of the plan.
- No edits outside the memory file in phase 1. No edits to perfect-project, ever.
- Never commit the memory file. Never overwrite another section of it.
- Everything in engine-create-autotest's Hard prohibitions, for every item.
