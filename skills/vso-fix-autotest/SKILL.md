---
name: vso-fix-autotest
description: Repair a broken VSO engine autotest starting from an Asana task link — pull the task and failure evidence over Asana MCP, check whether it is already fixed upstream, find the root cause, fix it, validate, open a pull request, and post a summary comment to Asana. Use for "test X is broken", "fix this failing autotest", or a bare Asana link to a test-failure task.
disable-model-invocation: true
---

# Fix a Broken VSO Engine Autotest

Repair an existing test: task → evidence → root cause → fix → validate → PR → report.

Diagnosis method lives in [reference/diagnosis-playbook.md](reference/diagnosis-playbook.md).
PR, Asana comment and halt-report templates live in [reference/delivery.md](reference/delivery.md).
Authoring rules for any code you touch live in
[../vso-create-autotest/reference/authoring-rules.md](../vso-create-autotest/reference/authoring-rules.md).

## Use this when

- A test in `vso-engine-autotests` fails and there is an Asana task for it.
- A test fails on CI but passes locally, or the reverse.
- A test broke after a framework, SDK or app change.

## Do not use this when

- A brand-new test must be written from a Qase case → use `/vso-create-autotest`.
- The failure is an app defect and no test change is warranted — diagnose, then report it
  as a defect instead of weakening the test.

## Inputs

| Input | How to get it |
|---|---|
| Asana task link | **Required.** Ask for it if the user did not give one. |
| Test name / path | From the task, or `grep` the repo for the name in the failure log. |
| Failure evidence | CI artifacts, ReportPortal, BrowserStack session, or the user's log. |

Do not start editing code from a task title alone. Get a real failure signature first.

## MCP tools

**Asana** — `mcp__asana__asana_get_task(task_id=<gid>)` returns notes and comments together;
`asana_get_stories_for_task` for the full activity trail;
`asana_get_attachments_for_object` for screenshots and logs;
`asana_create_task_story` to post the final comment.
The gid is the last numeric segment of the Asana URL.

**Qase** — `mcp__qase__get_test_case_data(project_code="VSO", test_case_id=<id>)` when the
test maps to a case. Use it to confirm what the test is *supposed* to verify before changing
any assertion. It returns no attachments and no linked-task fields.

**Images** — `mcp__cats__read_image(source=<path or url>)` for screenshots from Asana.
Ignore every other `mcp__cats__*` tool: they drive the VSO Editor in `perfect-project`.

**GitHub** — no GitHub MCP is configured in this workspace; use `gh` (v2.95.0).

## Workflow

### 1. Read the Asana task

Fetch the task, its comments and its attachments. Extract: the test name, when it started
failing, which platform, which build, and any log the reporter attached. Read attached
screenshots with `read_image`.

If the task is inaccessible (403/404), stop and tell the user — do not guess the scenario.

### 2. Get a real failure signature

Find the exact error: the assertion or exception, the failing step, the file and line.
Sources, in order of preference: the CI artifact or ReportPortal entry for the failing run,
the BrowserStack session, the reporter's attached log, then a local reproduction.

Local runs are weaker evidence than CI runs. A test that passes locally and fails on CI is a
strong hint that the difference *is* the cause — session state, ordering, a counter that is
only zero in a single-test run, a device that only CI uses. Read
[reference/diagnosis-playbook.md](reference/diagnosis-playbook.md) § "Local green is not proof".

### 3. Check whether it is already fixed — before writing any code

This gate exists because it has been missed before, costing a full day of duplicate work.

```bash
git fetch origin master
git log --oneline origin/master -30
git log origin/master --oneline -- <path/to/test_or_framework_file>
git log origin/master -S'<distinctive_token>' --oneline
```

Also check whether the test is currently green on CI. If a fix already landed, **stop**:
report the commit, its author and date, and the current CI status, and ask the user whether
to close the task instead of opening a PR.

Confirm your branch point too — a stale base makes an already-fixed bug look alive.

### 4. Find the root cause

Follow [reference/diagnosis-playbook.md](reference/diagnosis-playbook.md). In short: name
the symptom, name the failing step, form 1–3 hypotheses, pick the most likely, and identify
the smallest change that addresses **that** cause. Do not begin with a workaround.

Decide explicitly whether this is a test problem or a **product defect**. If the product is
wrong, do not weaken the test — report the defect.

### 5. Settle the branch before you touch code

Commits happen **as you work**, not in one lump at the end, so the branch must be settled
first. A branch for this task may already exist — check before creating one.

```bash
git branch --show-current
git status --porcelain                       # what is already dirty is the user's work
git log --oneline origin/master..HEAD        # what the current branch already carries
```

- **On `master` or detached HEAD** → create it yourself:
  `git switch -c fix/<initials>/test_<case_id>_<short_slug> origin/master`
- **Already on another branch** → **ask with `AskUserQuestion`**: use the current branch, or
  create a new one from `origin/master`. Show the branch name, how many commits it is ahead
  and what they are. Do not decide this yourself, even when the branch name looks like it
  belongs to this task.

Read [reference/delivery.md](reference/delivery.md) § Branch and § Commits before the first
edit. Short version: one commit per finished logical piece, short plain-language subject,
explicit paths only, never `git add -A`.

### 6. Fix

- Change the minimum that addresses the root cause.
- Touch only files relevant to this failure.
- Follow the authoring rules for any code you write.
- Leave a short comment where the fix is non-obvious, explaining the cause — not the syntax.
- Never fix by raising a timeout, adding a `sleep`, adding a retry, broadening an `except`,
  or weakening an assertion. Each of those hides the failure rather than repairing it.

**Commit each cause on its own, as soon as it is fixed.** Two causes in one file are still
two commits. A latent copy of the same bug found elsewhere is a third. The subject says what
changed in plain words — `Fix ICS editor locator to accept any index`, not `Fix` or
`Post-investigation changes`. Run `make code-style-check` before each commit so every commit
stands on its own, and never mix an unrelated cleanup into a fix commit.

### 7. Validate — 5 automatic runs per platform

```bash
make ai-run-tests key=<test_name> platform_to_run=<PLATFORM_TAG>
```

Platforms: `iOS` and `Android` always (BrowserStack); `macOS`, `android_on_linux`,
`ios_on_linux` only on a macOS host; `Windows`, `UWP` only on a Windows host. Switch platform
by editing the `# App config` block in `.env`, and **restore `.env` afterwards** — including
when you stop early. `.env` is never committed.

You get **at most 5 automatic runs per platform**. Diagnose before each rerun; never rerun
unchanged. Commit each follow-up fix right after the run that justified it, so the history
shows the sequence of hypotheses rather than one opaque final state. Stop before 5 when the
same failure repeats with no new hypothesis, the failure is infrastructure, a required element
cannot be confirmed, the cause looks like a product defect, or the remaining fix would become
a refactor.

When the budget is exhausted or a stop condition fires, commit whatever is finished and worth
keeping, then **halt** and use the halt-report template in
[reference/delivery.md](reference/delivery.md): what was found, what was changed, what was
tried, what remains unclear. Then ask the user whether to continue and how many additional runs
to allow. Do not silently continue.

Verify the fix was actually exercised. If the original failure only reproduces under CI
conditions, say so plainly: a green local run then proves absence of regression, not the fix.

Record the validation results where the project records them, and commit that separately:
`Add test run results`.

### 8. Open the pull request

Everything is already committed by now, so this step only pushes and opens.
Follow [reference/delivery.md](reference/delivery.md) § Pull request.

Read your own history first, as a reviewer would:

```bash
git log --oneline origin/master..HEAD
```

If it does not read as clear steps, say so to the user instead of hiding it behind a summary.
Never force-push, never `git reset --hard`, never squash or rebase what you already pushed,
never touch the user's unrelated working-tree changes.

### 9. Comment on Asana

Follow [reference/delivery.md](reference/delivery.md) § Asana comment. It must cover: the
symptom, **how the cause was found** (which artifact and which log line was decisive — quote
it), the root cause, what was changed and why that instead of a workaround, how it
was validated, and links. Add anything worth a separate task under "Замечено попутно".

Comment only — do not close or reassign the task unless the user asks.

## Final report to the user

1. `🟢 What was fixed` — root cause in one sentence
2. `🟢 Run results` — per platform, runs used, and what the runs do and do not prove
3. `🟢 Commits` — `git log --oneline origin/master..HEAD`, so the user sees the steps
4. `🟡 Extra changes`
5. `🟡 Residual risks`
6. `🔴 Blockers`, if any
7. `ℹ️ Files, PR link, Asana link`

State plainly whether `.env` was restored and whether the working tree is clean.

## Hard prohibitions

- Do not edit code before you have a real failure signature.
- Do not skip the already-fixed check in step 3.
- Do not stabilise a failure you have not explained.
- Do not weaken or delete an assertion to get green.
- Do not disable, skip or xfail a test as the fix unless the user explicitly asks.
- Do not commit `.env`, secrets, or unrelated changes.
- Do not pile the whole fix into one commit, and do not rewrite pushed history.
