---
name: engine-fix-autotest
description: Repair a broken VSO engine autotest starting from an Asana task link — pull the task and failure evidence over Asana MCP, check whether it is already fixed upstream, find the root cause, fix it, validate, open a pull request, and post a summary comment to Asana. Use for "test X is broken", "fix this failing autotest", or a bare Asana link to a test-failure task.
disable-model-invocation: true
---

# Fix a Broken VSO Engine Autotest

Repair an existing test: task → evidence → root cause → fix → validate → PR → report.

Diagnosis method lives in [reference/diagnosis-playbook.md](reference/diagnosis-playbook.md).
PR, Asana comment and halt-report templates live in [delivery.md](../engine-create-autotest/reference/delivery.md).
Authoring rules for any code you touch live in
[../engine-create-autotest/reference/authoring-rules.md](../engine-create-autotest/reference/authoring-rules.md).

## Use this when

- A test in `vso-engine-autotests` fails and there is an Asana task for it.
- A test fails on CI but passes locally, or the reverse.
- A test broke after a framework, SDK or app change.

## Do not use this when

- A brand-new test must be written from a Qase case → use `/am-plr:engine-create-autotest`.
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

Qase, Asana, image and GitHub tools: [mcp-tools.md](../engine-create-autotest/reference/mcp-tools.md).
Use Qase when the test maps to a case, to confirm what the test is *supposed* to verify before changing
any assertion. The Asana task gid is the last numeric segment of the URL.

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

Follow [delivery.md](../engine-create-autotest/reference/delivery.md) § Branch (prefix `fix/`) before the first edit. PR and Asana conventions
come from the rule [writing-git-github-asana.md](../../rules/writing-git-github-asana.md).

### 6. Fix

- Change the minimum that addresses the root cause.
- Touch only files relevant to this failure.
- Follow the authoring rules for any code you write.
- Leave a short comment where the fix is non-obvious, explaining the cause — not the syntax.
- No fix from [delivery.md](../engine-create-autotest/reference/delivery.md) § Forbidden fixes.

**Commit each cause on its own, as soon as it is fixed**, as [delivery.md](../engine-create-autotest/reference/delivery.md) § Commits describes.

### 7. Validate — 5 automatic runs per platform

Follow [delivery.md](../engine-create-autotest/reference/delivery.md) § Validation and run budget (platforms, `.env`, budget, stop conditions).
When the budget is exhausted or a stop condition fires, use its halt report and ask the user how
to proceed.

Verify the fix was actually exercised. If the original failure only reproduces under CI
conditions, say so plainly: a green local run then proves absence of regression, not the fix.

Record the validation results where the project records them, and commit that separately
via `am-plr:commit`.

### 8. Open the pull request

Everything is already committed by now, so this step only pushes and opens.
Follow [delivery.md](../engine-create-autotest/reference/delivery.md) § Pull request.


### 9. Comment on Asana

Follow [delivery.md](../engine-create-autotest/reference/delivery.md) § Asana comment. It must cover: the
symptom, **how the cause was found** (which artifact and which log line was decisive — quote
it), the root cause, what was changed and why that instead of a workaround, how it
was validated, and links. Add anything worth a separate task under "Замечено попутно".

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
- Everything in the `am-plr:commit` skill's Constraints (no `.env`/secrets, no rewriting history) and the
  writing rule's Asana section (comment only; never close or reassign the task).
