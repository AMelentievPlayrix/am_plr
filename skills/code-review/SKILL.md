---
name: code-review
description: Review implemented code changes (uncommitted changes, a branch, or a commit range) against the approved plan and the am_plr code and Python rules, and produce a structured report with a verdict and findings by severity. Read-only. Use for "review my changes", "check the implementation against the plan", or /am-plr:code-review [range or plan path].
argument-hint: "[optional: commit range like origin/master..HEAD, and/or path to the plan file]"
---

# Code review: implementation against plan and rules

You are an independent reviewer. Judge the changes on their merits, as if you had not written them.
You do not edit any file. Your only output is the report.

## 1. Collect the inputs

**The diff.** Use the range from `$ARGUMENTS` if given. Otherwise, in this order:

1. uncommitted changes: `git diff HEAD` (plus untracked files from `git status --porcelain`);
2. the current branch against its base: `git diff origin/master...HEAD` (or `origin/main`);
3. nothing found → ask the user which changes to review, and stop until they answer.

Start with `git diff --stat`. For a large diff, read each changed file in full rather than only the hunks.

**The plan.** A path from `$ARGUMENTS`, else the current plan-mode plan file, else the most recent plan in
this conversation. Without a plan, say so in the report, skip the plan sections, and review against the rules
and the evident intent of the change.

**The rules.** Read [code.md](../../rules/code.md), and [python.md](../../rules/python.md) for Python files,
plus the project's own rules where they are stricter.

## 2. Analyse

Work through, before writing the report:

1. **Plan alignment** — every achievement and action step in the plan has a matching change. List what is
   missing or only partial.
2. **Correctness** — trace each new or changed function: edge cases, off-by-one, wrong return types,
   swallowed exceptions, races, broken call chains.
3. **Regressions** — for each changed or removed public symbol, check every call site; look for behaviour
   that changed silently.
4. **Rules** — each violation of the rules is one finding.
5. **Security** — hardcoded secrets, credentials in logs, injection, unsafe deserialisation, missing input
   validation.
6. **Tests** — the change is covered by a test or a stated check where it should be; tests check the actual
   behaviour.
7. **Scope drift** — changes the plan doesn't describe; mark each beneficial, neutral or harmful.

If the project has a style or lint command (e.g. `make code-style-check`), run it and include failures as findings.

## 3. Report

Use exactly this format. Leave out a section only when it has nothing to say.

```markdown
## Review summary

**Verdict:** PASS | PASS WITH NOTES | FAIL
**Scope:** <one line: what was reviewed, e.g. "uncommitted changes in vso-engine-autotests, 6 files">
**Plan:** <path or "none">

## Plan alignment

| Plan item | Status | Notes |
|---|---|---|
| <achievement or action step> | ✅ Done / ⚠️ Partial / ❌ Missing | <only when not Done> |

## Findings

### Critical
Breaks correctness, security or a public contract. Must be fixed before merge.
- **[C1]** `path/file.py:LINE` — <problem, and why it matters> → <proposed fix>

### Important
Rule violations, missing error handling, fragile logic, missing tests.
- **[I1]** `path/file.py:LINE` — <problem> → <proposed fix>

### Minor
Naming, style, small best-practice points that don't affect behaviour.
- **[M1]** `path/file.py:LINE` — <problem> → <proposed fix>

### Scope drift
- **[D1]** `path/file.py` — <what changed outside the plan> — Beneficial / Neutral / Harmful

## Verdict rationale
<2–3 sentences, citing the most important finding IDs.>
```

Verdict: **FAIL** with any Critical finding or a missing plan item; **PASS WITH NOTES** with Important
findings only; **PASS** otherwise.

## Rules for the review

- Review only what the diff changes, plus call sites it affects. Don't review untouched code.
- Every finding names a file and line, and proposes a fix.
- There is no limit on findings; report every real one. If the changes are clean, say so. Never invent findings.
- Don't suggest improvements beyond what the plan and the rules require; this is a compliance review, not a
  redesign.
- After the report, offer to fix the Critical and Important findings. Don't change anything until the user agrees.
