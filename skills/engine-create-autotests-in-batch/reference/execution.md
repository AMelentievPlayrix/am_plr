# Phases 4-6 and 8: test plan, tests, follow-ups, close-out

## Phase 4: test plan

Write it into plan.md and show it to the user:

1. **Scope**: the cases now unblocked, split into fully and partly automatable; cases left out and why; cases
   waiting for a perfect-project merge (queued last).
2. **Order**: simplest first. One row per test in board.md § Merge order, branch
   `feature/<initials>/test_<id>_<slug>` from `origin/master`. No stacks.
3. **Platforms per case**: what this host runs (macOS host: iOS and Android on BrowserStack, macOS locally;
   Windows host: Windows, UWP). Platforms this host cannot run go to the platform track
   ([platform-track.md](platform-track.md)).
4. **Request for approval 2**, saying what it covers:
   - implementing the tests and opening PRs;
   - **merging each green PR** without waiting for review (the reviewer is still requested);
   - posting the Asana comment and **marking each case subtask done**;
   - Qase automation = automated;
   - code follow-ups within this scope.
5. **Allow rules the user adds** (the agent never edits settings). These are commands the auto-mode classifier
   refused before:

   ```
   Bash(gh pr merge:*)  Bash(gh pr ready:*)  Bash(gh pr edit:*)
   Bash(<am_plr>/.venv/bin/python -I <am_plr>/skills/engine-create-autotests-in-batch/scripts/qase_case.py:*)
   ```

Record approval 2, quoted, in plan.md and events.md. After it, the batch runs without questions until close-out.
Anything that needs the user goes under **Needs you**, and the queue moves on.

## Before the first item

1. vso-engine-autotests is on `master` with an empty `git status --porcelain`; run `git fetch origin`. If the tree is
   dirty, stop and tell the user. Never stash or clean their work.
2. The builds in `artifacts/app` are the ones facts.md names (they must contain every merged blocker fix).
3. Record the `.env` modification time in resume.md (`stat -f %m .env` on macOS), never its content.
4. **Arm the watchdog**: `CronCreate`, every 10 minutes on off-minutes (`3,13,23,33,43,53 * * * *`). Record the job id
   in resume.md. Cron jobs live only as long as the session: re-arm after a restart. Prompt:

   ```text
   Batch watchdog: read <folder>/resume.md and status.md. If a subagent is running: check its newest log line in
   its item file, the newest file change under vso-engine-autotests tests/ framework/ artifacts/, and whether pytest
   runs. Silent 30 min with no pytest -> SendMessage a status request and log it; still silent next tick -> TaskStop,
   record its state (branch, uncommitted files, runs used) and brief a fresh subagent with it. Otherwise one line.
   If none is running: verify the last item, run the merge-loop routine for it if green, launch the next item.
   Queue empty -> phases 6-8 of the skill, then CronDelete this job.
   ```

## The loop

For each row of board.md § Merge order, top to bottom:

1. **Wait or skip.** An item that needs an unmerged perfect-project fix waits for the master TestSDK build. Move on
   to the next row and come back to it.
2. **Launch.** Set the row to `in progress` and log it. Launch one general-purpose subagent in the background with
   the test-item brief ([briefs.md](briefs.md) § Test item). Only one at a time: the items share one tree and one
   BrowserStack account. While it runs, do not touch the repo, and answer the user from the memory.
3. **Verify** its final message before trusting it:
   - `git status --porcelain` is empty and the branch is `master`;
   - the `.env` modification time is unchanged;
   - `gh pr view <n> --json state,isDraft,baseRefName,title` shows base `master` and the expected draft state;
   - the item file has the runs, the PR and the prepared Asana comment;
   - the PR text and prepared comment pass § Text for people outside the batch.

   Add a `(orchestrator): Verified - ...` line to the item file. Fix any mismatch before going on.
4. **Green PR**: run the [merge-loop.md](merge-loop.md) routine. **Draft [WIP]**: record the reason. If a decision is
   needed, put it under **Needs you**. Items that do not depend on it continue.
5. **Update** board.md, status.md and events.md, then launch the next row.

**No partial implementations.** A test counts as green only when every expected result has an automated check (an
agreed substitute counts; a commented-out expectation does not). If a finding breaks the plan for several items,
probe it first with an uncommitted diagnostic run on a small budget, then re-plan and tell the user.

## Branching and shared code

- Every item branches from fresh `origin/master`. The previous green PR is already merged, so its helpers are there.
  This replaces stacking: squash merges made stacked PRs conflict, needed force-pushes the classifier refuses, and
  led to helpers being copied between tests.
- Never cherry-pick or copy code from an open PR. If an item needs code from an unmerged PR, merge that PR first
  (merge-loop), or wait.
- A test PR that changes shared framework code puts the change in its own commit. If the change alters a step that
  merged tests use, those tests are rerun on one platform each, and the runs go into the PR's «Проверка».
- A refused or blocked merge stalls only the items that need its code. The rest continue from master.

## Text for people outside the batch

Item ids (`A`, `F1`, `T2`), phase names and the memory folder exist only inside the batch. Every commit, PR title
and body, Asana task and comment must read on its own.

| Do not write | Write instead |
|---|---|
| `Будет проверено в T1` | `Будет проверено автотестом VSO-17597 (#365)` |
| `Зависит от F1` | `Зависит от #363` |
| `для батча Amplitude`, `оркестратор`, `memory`, `бюджет прогонов` | omit |
| `/tmp/<batch>/…`, throwaway test names | the real test or command, or omit |

The orchestrator reads every text once for these before posting.

## Phase 6: follow-ups

Collect follow-ups in board.md § Follow-ups as they appear: helpers to switch to, tests to rerun, Qase text issues,
flaky neighbours, duplicate Asana comments.

- Code follow-ups within this scope: create one Asana task (Russian, «Нужно ...»), use one branch from master and
  one PR, validate on every affected platform, and merge with the routine.
- Qase text issues: comment on the case's Asana subtask, or tell the case owner. Edit Qase steps only after the
  owner's or user's decision.
- Anything else (another team's code, scope changes, cleanup the MCP cannot do) goes under **Needs you**.

## Phase 8: close-out

1. Every board.md row is final, and status.md shows the end state.
2. One Russian summary comment (`html_text`) on the parent task:
   - automated cases and platforms;
   - PRs;
   - blockers fixed and the tasks created;
   - follow-ups;
   - what is still open, and who owns it.
3. Run `/am:log` for anything not logged yet.
4. Delete the watchdog cron. Mark the folder `done` in INDEX.md, and mark the auto-memory pointer done.
5. Send the final reply ([merge-loop.md](merge-loop.md) § Final reply), then **Needs you**.
