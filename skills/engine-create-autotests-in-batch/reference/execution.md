# Phase 2: execution

Starts only after the user explicitly approves the plan. Record the approval as a batch event, with what the
user approved or changed.

## Before the first item

1. Check vso-engine-autotests: on `master`, `git status --porcelain` empty, `git fetch origin`. If the tree is
   dirty, stop and tell the user. Do not stash or clean their work.
2. Save a batch backup of `.env` **outside any git repo** (e.g. `/tmp/<batch>/env.orig`) and record its path,
   but never its contents, in the memory file. Every item's restore is checked against it. Delete it when the
   batch ends.
3. Post the approved Asana actions from the plan: comments on blocker tasks that are solvable in autotests, and
   new dependency tasks for product changes. Create each new task in the dependencies container (§ Blocker tasks
   for framework items), and set it as a dependency of its subtask. Read the dependency back in both directions.
   Record the story and task gids.
4. **Assign the blockers this batch fixes.** Every blocker task that a framework item in the plan resolves
   (fully or for the platforms in scope) is assigned to the batch author, the Asana user `me` (Anton Melentiev).
   Assign only; do not close or re-status it. Read the assignee back and record it as a batch event. Blockers the
   batch does not fix stay as they are.
5. **Create a blocker task for every framework item that has no Asana task**, per § Blocker tasks for framework
   items, before its subagent starts. The item's brief gets the task link, so the PR links it from the start.

6. **Arm a watchdog.** Background subagents die with the Claude Code session, and nothing restarts them, and a live
   subagent can also hang for hours (one waited 4 h on nothing). Create a recurring cron job (`CronCreate`, every
   10 min on off-minutes, e.g. `3,13,23,33,43,53 * * * *`) whose prompt reads the memory file and:
   - if a subagent is running, checks progress: its newest log line, the newest file change under the batch
     scratch dir and the repo (`artifacts`, `tests`, `framework`), and whether pytest is running. With no pytest
     and nothing new for 30 min, it sends the subagent a status request (SendMessage) and records it; still silent
     on the next tick, it stops the subagent (TaskStop), records the state (branch, uncommitted files, runs used)
     and briefs a fresh one with that state. Otherwise it replies one line;
   - otherwise verifies and processes the last item and launches the next; at the end runs § At the end of the
     batch and deletes itself.
   Write a "How to resume" section at the top of the memory file with the same steps and the watchdog prompt,
   because cron jobs are session-only: after a restart, re-arm it from there. Record the job id as a batch event.
   Every brief tells its subagent to log at least every 15 min and to put a timeout on every command.

## The loop

For each row of "Merge order", top to bottom:

1. **Skip if blocked.** If an item it depends on ended as `draft PR` or `blocked`, mark this one
   `blocked by <item>`, record why, and go to the next row.
2. **Set the row to `in progress`**, and record "subagent launched" as a batch event.
3. **Launch one subagent** with the brief below (general-purpose agent, `run_in_background: true`). Run only one
   at a time. While it runs, do not touch the repo or `.env`. Answer the user from the memory file.
4. **Verify its final message** before you trust it:
   - `git -C <repo> status --porcelain` is empty and `git branch --show-current` is `master`;
   - `git diff --no-index <batch backup> <repo>/.env` shows no difference;
   - `gh pr view <n> --json state,isDraft,baseRefName,headRefName,title` matches the plan (base = the item's
     `Base`);
   - its memory-file section has the runs, the PR and a prepared Asana comment.
   Record a `(orchestrator): Verified — ...` line in its section. Fix any mismatch before the next item, or stop
   and report.
5. **Update** the Task table row, the Blockers rows it touches and the merge-order row (branch, PR, status, runs
   and device) — [memory-file.md](memory-file.md) § Keeping the status view current — then continue.

**No partial implementations.** A test counts as green only when every expected result of the case has an
automated check (an agreed substitute counts; a commented-out expectation does not). If an item can't be fully
covered, it ends as a draft PR with the reason and the batch moves on to the next item. If a finding breaks the
plan for several items, probe it first (an uncommitted diagnostic run with a small budget), then re-plan.

A framework item and the first test that uses it form one validation unit:

- The framework subagent implements and commits the item, pushes it, and opens a **draft** PR. There is no test of
  its own yet, so the PR's "Проверка" says it will be confirmed by the first dependent test.
- When the first dependent test passes on a device, mark the framework PR ready (`gh pr ready <n>`), add that run
  to its "Проверка", and record the item as `green PR`. Then comment on the item's blocker task (§ Blocker tasks
  for framework items, step 5).
- If that first device run shows the capability itself does not work (e.g. a capability is ignored, a channel does
  not carry the data), **stop the dependent line**. Mark the dependants `blocked by <item>` and report to the
  user. Do not let a test work around a broken shared capability.

## Text for people outside the batch

Item ids (`F1`, `T2`), stage names and the memory file exist only inside the batch. Reviewers and Asana readers
never see the plan, so every PR title and body, commit message, Asana task description and Asana comment must be
understandable on its own.

| Do not write | Write instead |
|---|---|
| `Будет проверено в T1` | `Будет проверено автотестом VSO-17597 (#365)` |
| `Зависит от F1` / `стоит на F2` | `Зависит от #363` / `мержится после #364` |
| `Первым потребителем станет T1` | `Шаг используют автотесты VSO-17597 и VSO-7684` |
| `для батча Amplitude`, `оркестратор`, `memory file`, `бюджет прогонов` | omit; say only what matters to the reader |
| `key=f2_app_log_proof`, `/tmp/<batch>/…` | the real test or command a reader can run, or omit |

Before posting or opening anything, the orchestrator reads the text once for these and fixes them. After a merge
pass (§ After merges), the same applies to lines that became stale, such as "зависит от #363" once #363 is merged.

## Blocker tasks for framework items

A framework item with its own PR unblocks one or more cases, so it needs its own Asana task: otherwise the PR is
linked to nothing, and the cases show no dependency on it. This applies to every framework item that no existing
blocker task already covers, whether the plan named it or it came up during execution (a follow-up fix, a split).
Product-change tasks from the plan follow the same container, dependency and assignee rules.

Dependencies container (parent of all blocker tasks):
<https://app.asana.com/1/656176460444/project/1212459666284359/task/1218516934688376> (gid `1218516934688376`).

1. **Create** the task before the item's subagent starts, as a subtask of the container (`parent` = the container
   gid). Assignee: the batch author (`me`, Anton Melentiev). Russian, written before the work, per the writing
   rule's Asana section:
   - title: `[Engine/SDK] Автоматизация: <что нужно сделать>`;
   - description: what needs to be done, to unblock what: `Нужно <сделать X>, чтобы <автоматизировать VSO-<id>
     (<что именно сейчас невозможно>)>.` Then a short "Почему" (the gap, with file:line), "Что блокирует" (each
     blocked subtask as a link), and "Готово, когда" (e.g. "автотест VSO-<id> проходит на <платформа>").
     No batch item ids or stage names (§ Text for people outside the batch).
2. **Link it** as a dependency of every subtask it blocks (`set_task_dependencies` on each subtask, or
   `set_task_dependents` on the new task). Read the links back in both directions.
3. **Record** the task in the memory file's Blockers table (a new id, Cases = the blocked cases, Asana link) and in the item's Merge order
   row, and as a batch event.
4. **Brief**: the item's brief carries the task link, so the PR's "Ссылки" names it as the Asana task. The cases'
   PRs keep their own subtasks.
5. **When the PR is green** (validated by the first dependent test), comment on the task, html_text, Russian:
   the PR link and a short summary of what was in fact done (two or three sentences: what was added, how it was
   validated, on which device). Comment only; do not close or re-status the task.

If Asana MCP is unavailable, record the pending task or comment in the memory file and tell the user. Do not start
the item's subagent without the task link unless the user says so.

## Per-item brief

Fill in the `{...}` slots. Drop the "Framework item" block for a test item, and the "Test item" block for a
framework item.

```text
You are implementing ONE item of an unattended batch in /Users/playrix/projects/vso-engine-autotests.
Nobody will answer questions: never use AskUserQuestion.

## Item
- {ITEM_ID}: {ITEM_TITLE}
- Qase case: VSO-{CASE_ID} (project code VSO), or "none" for a framework item
- Asana task: {ASANA_LINK} — the case's subtask, or for a framework item its blocker task (§ Blocker tasks for
  framework items). Link it in the PR's "Ссылки". Read-only for you: do NOT comment, close, reassign or re-status it.
- Branch: {BRANCH}; base: {BASE_BRANCH} (master, or the branch of the item this one depends on)
- Depends on: {DEPENDENCIES with PR links, or "none"}
- What the analysis found: {CASE_SECTION_SUMMARY: platforms, substitutes, needed changes, what a first run must prove}

## Procedure
Read and follow /Users/playrix/projects/am_plr/skills/engine-create-autotest/SKILL.md and its reference files
reference/authoring-rules.md, reference/delivery.md, reference/mcp-tools.md, before writing any code. The
skill can't be loaded with the Skill tool, so read the files directly. Also obey
/Users/playrix/projects/am_plr/rules/code.md, python.md and communication.md. Commit ONLY through the
`am:commit` skill (Skill tool), with the paths and delivery.md's split order.

## Overrides to the skill (these win over the skill)
1. Never stop to ask. Wherever the skill says halt and ask (budget spent, BLOCKED or contradictory case, likely
   product defect, missing step or element), instead: commit what is worth keeping, push, open a DRAFT PR
   (`gh pr create --draft --base {BASE_BRANCH}`) in Russian, titled "[WIP] ...", with the halt report as the
   body. Log it and finish. The batch continues with the items that do not depend on this one.
2. Branch: if `git status --porcelain` is not empty, STOP without touching anything and report "not started:
   dirty tree" with the file list. Otherwise: `git fetch origin && git switch -c {BRANCH} origin/{BASE_BRANCH}`.
   Do not ask about the current branch. Initials are fixed by the plan: {INITIALS}.
3. The PR targets {BASE_BRANCH} (`--base`), so it shows only this item's commits. If it is not master, say in
   "Ссылки" and in "Риски и ограничения" that it depends on that PR and must be merged after it.
4. Do NOT post Asana comments (skip the skill's Asana step). Instead write the comment you would have posted
   (Russian, delivery.md § Asana comment) into your memory-file section, under "Prepared Asana comment".
   Everything you write for others (commits, PR title and body, the prepared Asana comment) must read without
   this batch's context: no item ids (`T1`, `F2`), no "batch", "orchestrator", "memory file", "run budget",
   throwaway test names or scratch paths. Name things by what they are: "проверено автотестом VSO-17597 (#365)",
   not "проверено в T1"; "зависит от #363", not "зависит от F1" (§ Text for people outside the batch).
5. Do NOT request a reviewer. The orchestrator does that.
6. Host is {HOST}. Platforms: as delivery.md § Validation. Narrow them only where the Qase case, its tags or the
   step decorators exclude a platform, and record why in the log and the PR.
7. Restore `.env` when validation ends, including on an early stop. Verify it with
   `git diff --no-index {ENV_BACKUP} .env` (the batch backup). Never print .env contents.
8. Finish on master with a clean tree: `git switch master`. Don't merge the PR.

## Framework item
- Implement the item, split into commits per delivery.md § Commits. `make code-style-check` must pass.
- There is no test to run yet. Prove what you can without a device: `pytest --collect-only` on the tests that will
  use the item, and an offline check of parsers/schemas against real samples when samples exist.
- Push and open a DRAFT PR (not "[WIP]") whose "Проверка" says it will be validated by {FIRST_DEPENDENT_TEST}
  (named as "автотест VSO-<id>", never by its batch item id).

## Test item
- The framework items you depend on are already in your base branch. Do not reimplement or cherry-pick them.
- If a run shows a bug in a framework item's code: fix it on THAT item's branch (switch to it, commit via
  am:commit, push), then rebase your still-unpushed branch onto it. Record the fix in both memory-file sections.
  If your branch is already pushed, stop and report instead.
- If you need something that is not in your base chain, do not copy it. Halt per override 1 and name the missing
  dependency, so the orchestrator can fix the merge order.

## Traps from earlier batches
- A "not sent / absent" check needs a positive control: one uncommitted control run in which the thing IS present
  and the check FAILS. Then revert the control edit. A "0 found" that was never shown to be able to find 1 is blind.
- One-shot events (first install, first open, uninstall) can't be reproduced by the in-session auto-retry
  (tests/conftest_auto_retry.py). A retry that passes after a failure here proves nothing.
- BrowserStack capabilities and region apply to the whole run.
- Record the device id and model with every run; results can depend on the device.
- `platform_to_run` values are case-sensitive (`iOS`, `Android`); a lowercase value deselects every test.
- Before you call something a product defect, read the product code in /Users/playrix/projects/perfect-project
  (read-only) and quote it.

## Memory file
{MEMORY_FILE}. Read the task table, "Shared findings" and the sections of finished items first. Append ONLY to
your section `## {SECTION_HEADING}`, as `- YYYY-MM-DD HH:MM: ...`. If it already shows progress from an earlier
attempt, continue from there. Log, as facts: what the Qase case says (platforms, key steps), the branch, each commit
(sha + subject), each run (platform, n/5, device, PASSED/FAILED, failing step, BrowserStack build link), diagnosis
and change, control runs, .env restore, push, the PR link, and the prepared Asana comment. Do not edit other
sections or tables. Never write secrets or tokens.

## Final message (the only thing the orchestrator sees)
Return exactly these fields:
- Status: green PR | draft PR (framework, awaiting validation) | draft PR [WIP] (halted) | not started (+ reason)
- Branch: / Base:
- PR URL:
- Platforms and runs used: e.g. iOS 2/5 PASSED (dev 201); Android 1/5 PASSED (dev 110)
- Framework items exercised: which items' code ran on a device and whether it worked, or "none"
- Open problem: one line, or "none". Mark a suspected product defect as "PRODUCT DEFECT?".
- .env restored: yes/no (+ how verified)
- Working tree clean and back on master: yes/no
```

## Stacking

- Each item's branch starts from its `Base`: `origin/master` for an item with no dependency, otherwise the branch of
  the item it depends on. Its PR targets that same branch, so the PR shows only its own commits.
- Prefer a linear stack. If an item depends on two branches, put one of them on top of the other in the plan.
  Cherry-picking copies of commits across branches is a last resort: copies conflict once the original is squash-merged
  (the Sentry batch had to restructure three PRs because of this). If you do it anyway, say so in the PR body and
  the merge-order table.
- Keep "Merge order" current. It is also the order you recommend to the user for merging.

## At the end of the batch

1. Re-read the memory file. Every Task table row must be final (🟢 / 🟡 / 🔴 / ⛔ / out of scope) and every blocker row
   current ([memory-file.md](memory-file.md) § Keeping the status view current).
   Every framework item with a PR must have a blocker task linked to the subtasks it blocks; create any that is
   missing now (§ Blocker tasks for framework items).
2. **Asana**, Russian, comment-only, `html_text` per the writing rule:
   - one comment per processed subtask, from the prepared text. Check it against the final PR state and correct it
     before you post;
   - one comment per green framework item's blocker task, if § Blocker tasks for framework items step 5 has not
     posted it yet;
   - one summary comment on the parent task: how many items were automated, green and draft PRs, the merge order,
     the blocker tasks created, shared findings worth a task, and the open questions.
   Record each story gid. Do not comment on subtasks that were not worked on.
3. **Reviewer**: `gh pr edit <n> --add-reviewer <reviewer>` on green, non-draft PRs only (delivery.md § Reviewer).
4. Delete the `.env` batch backup. Set the header goal to `after merges`.
5. Give the user the final report from SKILL.md.

## After merges

When the user says PRs were merged (they are usually squash-merged), or asks for a rebase pass:

1. Fetch. For each merged PR, record the squash commit and set its row to `merged`. GitHub retargets a dependent PR
   to master when its base branch is deleted. Check each base with `gh pr view`.
2. Rebase each open dependent PR **replaying only its own commits**:
   `git rebase --onto origin/master <old base tip> <branch>`. Never re-apply the merged item's commits.
3. Check: `make code-style-check`, `pytest --collect-only` of the test, and that every file the branch touches is
   byte-identical to the pre-rebase version, unless you resolved a conflict there.
4. Re-validate on a device whenever a conflict was resolved or master changed code the test uses. Record the
   device and the build link.
5. Push with `git push --force-with-lease=<branch>:<old sha>`. This is the only force-push the batch makes, and only
   in this pass. The auto-mode permission check may refuse it: then give the user the exact command and wait,
   do not work around it. Then remove outdated dependency lines from the PR body (and any batch-internal wording,
   § Text for people outside the batch), comment the rerun on the PR, and re-request the reviewer, because the
   force-push dismisses earlier approvals.
6. To simulate a merge order, use a scratch worktree and scratch branch names. Never name a real branch in a
   simulation command: one batch rebased and pushed a real PR branch onto a fake commit that way.
7. Record a batch event: new heads, reruns, conflicts and how each was resolved, and the recommended merge order.
