# Phases 2-3: blocker plan and blocker fixes

Blockers are proven, fixed and validated on devices before any test is written. The Marketing batch did this:
- three TestSDK RPC APIs (perfect-project #20217-#20219);
- three framework PRs (#374-#376);
- two Qase-side fixes by the case owner;
- one false blocker closed with a comment.

All of it was validated by one throwaway device test before the tests started.

## Phase 2: blocker plan

Start from board.md § Blockers after phase 1: every blocker has "Real?" verified in source.

### Fix types

| Fix type | Typical cause | Fix | Who |
|---|---|---|---|
| C++ product | Widget-only actions with no Autotests RPC, hardcoded values, a manager that exists only while a widget is open | TestSDK RPC API in perfect-project (`sdk_test/src/<Module>/<Module>Api.cpp`, registered next to the existing handlers), plus a Python client as a framework item | the batch, if the user allows perfect-project edits for this fix; otherwise the owning team |
| Python framework | Missing reader or step, enum mismatch, missing client, no reset step | Framework item in vso-engine-autotests | the batch |
| Qase-side | Case expects what the product no longer does, or a step that does not exist | The case owner updates the case. The agent edits steps only after the owner's or user's decision, with [qase_case.py](../scripts/qase_case.py) `steps` | QA / case owner |
| Infra / access | Region, device, CI configuration, credentials | A task for the owner | owning team |

### Framework items

Every change that two or more tests will need becomes a framework item now, with its own branch and PR from
`origin/master`. That includes small shared helpers: event predicates, "wait for an event of the current run", a
baseline reset, and the Python client of a new RPC API. In the Marketing batch, helpers that appeared mid-batch were
copied into several tests, and a follow-up PR was needed to unify them.

### The plan (plan.md, then shown to the user)

1. **Blockers table**: id, real or not (with evidence), fix type, fix design (API signatures or step names), cases
   unblocked, owner.
2. **Asana actions**, each naming its task:
   - create blocker tasks for fixes with none (§ Blocker tasks below);
   - set dependencies; remove wrong ones (the user does it in the UI when the MCP cannot);
   - comment on real blockers with the exact fix plan;
   - close false blockers with a comment explaining why;
   - list the blocker tasks to close once their fix is merged. Only tasks named here may be closed.
3. **perfect-project edits** requested: which fixes, in which worktrees. Nothing in perfect-project without this
   approval.
4. **Draft test scope**: the cases each fix unblocks; cases left out and why.
5. **Open questions** (one per decision, with a recommended answer).
6. **Request for approval 1**, saying what it covers: the listed Asana actions, the perfect-project edits, and
   merging the vso-engine-autotests framework PRs once they are validated. Record the approval, quoted, in plan.md
   and events.md.

## Phase 3: blocker fixes

### 1. Asana actions

Post the approved actions and read each one back (dependencies in both directions). Record the story and task gids
in events.md. On a timeout, read before retrying ([gotchas.md](gotchas.md) § Tools).

### Blocker tasks

A fix with its own PR needs its own Asana task, otherwise the PR is linked to nothing. Dependencies container:
<https://app.asana.com/1/656176460444/project/1212459666284359/task/1218516934688376> (gid `1218516934688376`).

- Create it as a subtask of the container, assigned to the batch author (`me`). Russian, written before the work
  (rules/communication.md § Asana):
  - title `[Engine/SDK] Автоматизация: <что нужно сделать>`;
  - description `Нужно <сделать X>, чтобы <автоматизировать VSO-<id> (<что сейчас невозможно>)>.`;
  - then «Почему» (the gap, with file:line), «Что блокирует» (subtask links), «Готово, когда».
- Link it as a dependency of every subtask it blocks, and read the links back.
- Record it in board.md § Blockers and § Merge order. The fix's brief carries the link, so the PR names it.

### 2. Implement in worktrees

- One worktree per fix: `/Users/playrix/projects/worktrees/<repo>/<id>_<slug>`, branch from `origin/master`:
  - vso-engine-autotests: `feature/<initials>/<slug>`;
  - perfect-project: `dev/<initials>/<slug>`, created with `GIT_LFS_SKIP_SMUDGE=1`; the sources are enough for code
    changes, but the worktree is not buildable locally.
- Fixes run in parallel (separate worktrees, no device runs). Use the blocker-fix brief from
  [briefs.md](briefs.md). Note the files several fixes touch (e.g. one handler list), and keep those edits minimal.
- **Round 1, plan.** For each plan, run `am:plan-review` in an independent subagent that returns its findings as a
  list (it cannot ask the user). Decide each finding, record the decision in the item file, then resume the
  subagent for **round 2, implement**.
- Verify each fix: worktree clean, commits as logged, checks passed. Then push (HTTPS fallback) and open a **draft**
  PR from the item's PR draft. Comment the PR link on its blocker task.

### 3. Build the TestSDK

Trigger the TestSDK build types ([gotchas.md](gotchas.md) § Environment) on the fix branch when the build type
accepts one. Otherwise build after the merge, from master. Wait for the build with
`release-check/scripts/wait_builds.py` under Monitor. Download the builds into vso-engine-autotests `artifacts/app/`
and record the build numbers in facts.md. A compile error goes back to that fix's worktree, followed by a new build.

### 4. Validate on devices

- Build one **throwaway device test** that exercises every fix: raw RPC calls or the new framework steps, the
  responses expected per platform, and a positive control for every "absent" result. Keep its source in the memory
  folder, not in git.
- Run it in a scratch worktree of vso-engine-autotests: `origin/master` with the framework branches merged into a
  local `scratch/<slug>-validation` branch, never pushed. Run on every platform in scope through
  `run_on_platform.py --env-file <main checkout>/.env`.
- Record each run in every item it covers: platform, device, build, result.
- A fix that fails gets fixed on its own branch, and the test is run again. A C++ change also needs a new build.
- Once validated: add the runs to each PR's «Проверка», mark it ready (`gh pr ready`, from the orchestrator), and
  request the reviewer (delivery.md § Reviewer).

### 5. Merge and close

- **vso-engine-autotests framework PRs**: merge them through the [merge-loop.md](merge-loop.md) routine (no Qase
  step), in an order that avoids conflicts. Retarget or rebase only branches that have not been pushed.
- **perfect-project PRs** merge through Mergify after human review. The agent answers review comments: it checks
  each one in source, fixes it in the worktree, pushes, and replies in the thread.

  Once a PR is approved, put `/am:merge-pp <PR links> master` (plus a minor if the user wants one) under **Needs
  you** in status.md. `merge-pp` cannot be run by the agent and asks for the user's confirmations.

  After the merge: build the TestSDK from master, download it, and record the builds. Cases that need the fix wait
  for that build. The other cases go ahead.
- **Close**: comment on each blocker task with the PR and a short summary of what was done and how it was
  validated. Close only the tasks named in approval 1. Tasks owned by other people get a comment; their closing
  goes under **Needs you**.
- **Qase-side blockers**: track the owner's answer (read the task stories). When the case changes, re-read it and
  update the item. Then the case enters the test scope.

### Gate to phase 4

Each in-scope blocker is in one of these states:
- merged and validated;
- validated and waiting for a perfect-project merge (its cases are queued last and wait for the master build);
- deferred, with its cases out of scope.

Update board.md and status.md, then write the test plan ([execution.md](execution.md)).
