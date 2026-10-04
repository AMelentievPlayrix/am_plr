---
name: plan-review
description: Review an implementation plan (the current plan, or a plan file at a given path) for major problems — bugs, wrong assumptions, missing steps, risks, rule violations — and walk the user through every one as a question with proposed solutions. Skips minor nitpicks. Use for "review this plan", "check the plan", or /am-plr:plan-review [path].
argument-hint: "[optional: path to a plan file]"
---

# Plan review: major issues as a questionnaire

You review a plan as an independent reviewer: judge it on its merits, as if you had not written it.
You do not edit project files, and you do not rewrite the plan unless the user asks.

## 1. Find the plan

In this order:

1. A path in `$ARGUMENTS` → read that file.
2. Plan mode is on and its plan file has content → that file.
3. The most recent plan in this conversation.
4. None of these → ask the user for the plan or its path, and stop until you have it.

## 2. Check it against the code

Read the code the plan touches; verify its claims rather than trusting them. Look for:

- **Correctness** — the proposed change wouldn't work: wrong API or signature, broken call chain, unhandled
  edge case, race, wrong data flow, an assumption the code contradicts.
- **Completeness** — a stated achievement with no action step; missing call-site updates, migrations,
  config or tests; a file that must change but isn't listed.
- **Regressions** — a public symbol or behaviour changes and something relying on it isn't handled.
- **Order and dependencies** — steps in an order that can't build or leaves the repo broken midway;
  circular dependencies.
- **Security** — secrets in code, injection, unsafe deserialisation, missing validation at a boundary.
- **Rules** — serious violations of [code.md](../../rules/code.md) and, for Python,
  [python.md](../../rules/python.md) (read them first): only violations that would cause a bug, a security
  problem or rework, not style.
- **Design** — a much simpler or safer approach exists, or the plan over-builds what was asked.
- **Verification** — no way to tell the change works (no test or check step) where one is needed.

**Report only major findings**: things that would cause a bug, a regression, a security problem, rework,
or a wrong outcome. Skip naming, wording, formatting, ordering of bullets and other minor style. There is
**no limit** on the number of findings; report every major one. If there are none, say so plainly; never
invent findings.

## 3. Walk the user through the findings

Order findings by impact, most serious first. For each one, ask a question with **AskUserQuestion**,
up to 4 findings per call, and keep calling until all are asked:

- `header`: short id and topic, e.g. `#3 Rollback`.
- `question`: the problem in one or two sentences — what is wrong, where (plan section or file), and what
  happens if it's left as is.
- `options`: 2–4 concrete proposed solutions, your recommended one first with `(Recommended)` in its label.
  Include "Keep as is" only when leaving it is a reasonable choice, and say the risk in its description.

If AskUserQuestion isn't available, write the same thing as a numbered list: problem, then options a/b/c
with the recommended one marked, and ask the user to reply with their picks.

## 4. Wrap up

Summarise the decisions in a short table (finding → chosen solution). Then offer to update the plan with
them; in plan mode, rewrite the whole plan in the plan file in its existing format when the user agrees.
