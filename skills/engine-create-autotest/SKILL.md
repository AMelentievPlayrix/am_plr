---
name: engine-create-autotest
description: Create a new VSO engine autotest from a Qase test case — read the case over Qase MCP, implement it against existing steps, validate it on every applicable platform, open a pull request, and post a summary comment to Asana. Use for "automate VSO-12345", "write an autotest for Qase case 12345".
disable-model-invocation: true
---

# Create a VSO Engine Autotest

Automate one Qase test case end to end: read → implement → validate → PR → report.

Authoring rules live in [reference/authoring-rules.md](reference/authoring-rules.md).
PR, Asana comment and halt-report templates live in [reference/delivery.md](reference/delivery.md).
Read the authoring rules before writing any code — they are the source of truth for
structure, steps, platform logic, tagging and SDK-specific behaviour.

## Use this when

- The user asks to automate a Qase case (`VSO-<id>`) in `vso-engine-autotests`.
- A new pytest test file must be added under `tests/`.

## Do not use this when

- An existing test is broken and must be repaired → use `/am-plr:engine-fix-autotest`.
- The work is pure framework/steps refactoring with no new test.
- The request needs a product-code change rather than test automation.

## Inputs

Required before starting:

| Input | How to get it |
|---|---|
| Qase case id | From the user. Project code is `VSO`. |
| Asana task link | From the user. Ask for it if absent — the final comment needs it. |
| Author initials | Derive from `git config user.name`; confirm if ambiguous. |

If the Qase id is missing, stop and ask. Do not guess it from a file name.

## MCP tools

Qase, Asana, image and GitHub tools: [reference/mcp-tools.md](reference/mcp-tools.md).

## Workflow

### 1. Read the case

Call the Qase MCP. Treat the case steps as the **primary source of truth**.
Record: preconditions, every step, every expected result, required tags, platforms.

Stop with `BLOCKED` if the case is missing, has empty steps, or its steps contradict
its expected results. Report what is contradictory; do not paper over it.

### 2. Settle the branch before you touch code

Follow [reference/delivery.md](reference/delivery.md) § Branch (prefix `feature/`) before the first
edit. PR and Asana conventions come from the rule
[writing-git-github-asana.md](../../rules/writing-git-github-asana.md).

### 3. Implement

Follow [reference/authoring-rules.md](reference/authoring-rules.md) exactly.
Non-negotiables, repeated here because they are violated most often:

- One new file per test, under the directory matching the SDK.
- Use only `step` and `data` fixtures (plus parametrization args).
- **No `assert` in test functions** — verify only through `step.check.*`.
- Use only existing steps from `framework/test_management/test_steps`; add a new
  business-named step there when none fits.
- Grep every `step.device.*` for platform decorators before using it.
- Only tags that exist in `framework/test_management/enums/common/tags.py`.
- Unimplementable case steps become commented code with the step number and a reason.

**Commit as each piece lands**, as [delivery.md](reference/delivery.md) § Commits describes.

### 4. Validate per platform

Follow [reference/delivery.md](reference/delivery.md) § Validation and run budget: the platform
matrix, `.env` switching and restore, at most 5 runs per platform, stop conditions and forbidden
fixes. On failure, diagnose before editing.

### 5. Halt when the budget is spent

When the budget is exhausted or a stop condition fires, use the halt report in
[reference/delivery.md](reference/delivery.md) and ask the user how to proceed.

### 6. Record results

Add the validation results to the test file as the project's other tests do
(platform, date, outcome). Run `make code-style-check` and fix what it reports.
Commit this on its own via `am-plr:commit`.

### 7. Open the pull request

Everything is already committed by now, so this step only pushes and opens.
Follow [reference/delivery.md](reference/delivery.md) § Pull request — including the
"already fixed upstream" check before pushing.


### 8. Comment on Asana

Follow [reference/delivery.md](reference/delivery.md) § Asana comment.
For a new test the comment covers: what was automated, how it was validated, what was
discovered along the way (product defects, gaps, deviations from the case), and the PR
link.

## Final report to the user

1. `🟢 What was done`
2. `🟢 Run results` — per platform, with the run count used
3. `🟢 Commits` — `git log --oneline origin/master..HEAD`, so the user sees the steps
4. `🟡 Extra changes` — new steps, framework touches
5. `🟡 Residual risks / limitations` — commented-out steps, unverified expectations
6. `🔴 Blockers`, if any
7. `ℹ️ Files, commands, PR and Asana links`

State plainly whether `.env` was restored and whether the case is fully covered.

## Hard prohibitions

- Do not invent a step, locator, tag or UI flow that you have not confirmed in code.
- Do not skip validation on an applicable platform without the user's explicit say-so.
- Do not report a test as done before a green run with the platform's own marker.
- Everything in the `am-plr:commit` skill's Constraints (no `.env`/secrets, no rewriting history) and the
  writing rule's Asana section (comment only; never close or reassign the task).
