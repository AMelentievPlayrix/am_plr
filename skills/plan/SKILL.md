---
name: plan
description: Write a reviewable implementation plan for requested code changes, in plan mode only, following the am_plr code and Python rules. Use when asked to "plan this", "make a plan for …", or /am-plr:plan <what to change>.
argument-hint: "<what should be built or changed>"
allowed-tools: Read Grep Glob Bash(git status *) Bash(git diff *) Bash(git log *)
---

# Plan: conceptual plan for review and approval

You produce a human-facing plan for the change in `$ARGUMENTS` (or the request just before this skill
was invoked). This is a conceptual overview: **what** changes and **why**, not every detail of how.
You do not edit any project file.

## 1. Make sure plan mode is on

Plan mode is on when the session's system messages say so (they name the plan file to write to).

- **On** → continue with step 2.
- **Off** → call the `EnterPlanMode` tool so the user can approve switching. If the tool is unavailable,
  ask the user to switch (Shift+Tab in the CLI, or the mode selector in VS Code) and wait.
- **The user declines or does not switch** → stop. Reply in one line that this skill only works in plan mode,
  and do nothing else.

## 2. Clarify before starting

Before reading code or writing anything, make sure the request is clear. Check the goal, scope (what is in and
out), expected behaviour, constraints (compatibility, performance, deadlines), and what "done" looks like.

- Anything unclear or ambiguous that would change the plan → ask first, with AskUserQuestion: concrete
  options, your recommended one first. Ask all such questions now, in as few rounds as possible.
- Wait for the answers before going on. Don't fill gaps with guesses.
- If questions come up later while reading the code, ask them too before writing the plan.
- Only things that truly don't affect the plan may be assumed; list those under assumptions in the plan.

## 3. Analyse before writing

Read the code involved; don't plan from file names. Work through, in your reasoning:

1. **Scope** — what exists and what must change (refactor), or what must be created and where it plugs in.
2. **Dependencies** — import chains and integration points; a safe build order; circular dependencies.
3. **Breaking surface** — every public symbol whose signature or contract changes, and its call sites.
4. **Compliance gaps** — where touched code breaks the rules below.
5. **Risk** — rate each finding HIGH / MEDIUM / LOW; the top risks go prominently into the plan.

## 4. Standards every proposed solution must meet

- [code.md](../../rules/code.md) for all code, and [python.md](../../rules/python.md) for Python.
  Read them before proposing solutions; the plan must not propose anything they forbid.
- Match the conventions of the code around the change; the project's own rules win where they are stricter.

## 5. Write the plan

Write it to the plan file in exactly this format:

1. **Overview** — 2–3 sentences: what is being built or changed, and why.
2. **Issues and proposed solutions** — each problem with its resolution, risk level, and a short code snippet
   only where it clarifies the idea.
3. **Files** — every file to add, delete or update, with a one-line description of the change.
4. **Achievements** — short bullets: what is achieved once the plan is executed.
5. **Action steps** — numbered, concrete steps in build order, including how to verify (tests, commands).

Rules for the text:

- Code examples are minimal: signatures plus 2–4 lines, with comments for what goes there. Never full bodies.
- On every revision, rewrite the whole plan. Never refer to earlier versions or say what changed; the plan
  always reads as a fresh, self-contained document.
- If something can't be decided without the user, list it as an open question at the end, with your
  recommended answer.

Then call `ExitPlanMode` so the user can review and approve it. For an independent check before approving,
the user can run `/am-plr:plan-review`.
