---
name: am-engine-create-autotest
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

- An existing test is broken and must be repaired → use `/am-engine-fix-autotest`.
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

**Qase** — `mcp__qase__get_test_case_data(project_code="VSO", test_case_id=<id>)`.
This is the only Qase tool. It returns `title`, `description`, `preconditions`,
`steps[]` (with `action`, `expected_result`, `data`, nested `steps`), `params`,
`tags`, `type`, `importance`, `status`, `suites`, `category_vso`, `vso_frontend_ra`.
It does **not** return attachments or linked-task fields — if the case references a
screenshot or a linked bug, ask the user for the link instead of inventing context.

**Asana** — `mcp__asana__asana_get_task` (notes + comments arrive in the same response),
`asana_get_stories_for_task` (full activity), `asana_get_attachments_for_object`,
`asana_typeahead_search`, and `asana_create_task_story` for the final comment.

**Images** — `mcp__cats__read_image(source=<path or url>)` reads a screenshot from an
Asana attachment. Ignore every other `mcp__cats__*` tool here: they drive the VSO
Editor from `perfect-project`, not this project's test app.


## Workflow

### 1. Read the case

Call the Qase MCP. Treat the case steps as the **primary source of truth**.
Record: preconditions, every step, every expected result, required tags, platforms.

Stop with `BLOCKED` if the case is missing, has empty steps, or its steps contradict
its expected results. Report what is contradictory; do not paper over it.

### 2. Settle the branch before you touch code

Commits happen **as you work**, not in one lump at the end, so the branch must be settled
first. A branch for this task may already exist — check before creating one.

```bash
git branch --show-current
git status --porcelain                       # what is already dirty is the user's work
git fetch origin master
git log --oneline origin/master..HEAD        # what the current branch already carries
```

- **On `master` or detached HEAD** → create it yourself:
  `git switch -c feature/<initials>/test_<case_id>_<short_slug> origin/master`
- **Already on another branch** → **ask with `AskUserQuestion`**: use the current branch, or
  create a new one from `origin/master`. Show the branch name, how many commits it is ahead
  and what they are. Do not decide this yourself, even when the branch name looks like it
  belongs to this task.

Read [reference/delivery.md](reference/delivery.md) § Branch and § Commits before the first
edit, and the rule [writing-git-github-asana.md](../../rules/writing-git-github-asana.md) for
PR and Asana conventions. Every commit goes through the `am-commit` skill.

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

**Commit as each piece lands**: call the `am-commit` skill (Skill tool, `skill: "am-commit"`) with the paths of that piece,
the split order from [delivery.md](reference/delivery.md) § Commits, and `make code-style-check`
as the pre-commit check.

### 4. Validate per platform

Platform matrix — validate on all applicable platforms unless the user says skip:

| Platform tag | When |
|---|---|
| `iOS`, `Android` | Always (runs on BrowserStack) |
| `macOS`, `android_on_linux`, `ios_on_linux` | Only when the host is macOS |
| `Windows`, `UWP` | Only when the host is Windows |

For each platform:

1. Edit the `# App config` block in `.env` — comment out the old platform, uncomment
   the target one. Record the original content first.
2. `make ai-run-tests key=<test_name> platform_to_run=<PLATFORM_TAG>`
3. On failure, diagnose before editing (see step 5).
4. Validate only active, uncommented code.

**Commit each fix right after the run that justified it** (via `am-commit`), one per cause,
while the reason is still fresh. Never leave several runs' worth of edits uncommitted.

**Restore `.env` to its original content when validation finishes — including when
you stop early or hit the run budget.** State in the final report that you did.
`.env` is never committed.

### 5. Run budget — 5 automatic runs per platform

You get **at most 5 automatic runs per platform** (the repo's `.cursor/rules/test.mdc` says 3;
this skill's limit wins).

Before each rerun, diagnose: name the exact symptom, name the failing step, list 1–3
likely causes, pick the most likely, and make the smallest change that addresses it.
Never rerun unchanged hoping for a different result.

Stop **before** 5 runs when any of these is true:

- the same failure repeats with no new root-cause hypothesis;
- the failure is infrastructure (BrowserStack, relay server, certificates, device);
- a required step or UI element does not exist and cannot be confirmed;
- the case contradicts observed product behaviour — a likely **product defect**;
- the remaining fix would be a refactor rather than a local change.

When the budget is exhausted or a stop condition fires, commit whatever is finished and
worth keeping, then **halt and report** using the halt-report template in
[reference/delivery.md](reference/delivery.md). Ask the user whether to continue and how
many additional runs to allow. Do not silently continue.

Never buy a green run with a longer `sleep`, a raised timeout, a broad `except`, a
retry loop, or a weakened assertion.

### 6. Record results

Add the validation results to the test file as the project's other tests do
(platform, date, outcome). Run `make code-style-check` and fix what it reports.
Commit this on its own via `am-commit`.

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
- Everything in the writing rule's git safety section (no `.env`, no rewriting history, comment-only on Asana).
