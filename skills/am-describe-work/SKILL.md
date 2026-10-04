---
name: am-describe-work
description: File an Asana task for a set of code changes, open a matching GitHub PR, and cross-link both. Use when asked to "describe the work", "write up these changes", or close out a change with a task+PR pair.
disable-model-invocation: true
argument-hint: "[optional: which changes/diff to describe]"
---

# Describe Work: Asana task + GitHub PR

Given a set of code changes (uncommitted, committed on a branch, or described by the user), produce:
1. An Asana task describing the change.
2. A GitHub PR for the change, linked to that task.
3. A comment on the Asana task linking back to the PR.

Language, style, PR body and Asana conventions come from the rule [writing-git-github-asana.md](../../rules/writing-git-github-asana.md). Read it first; this skill only adds the task + PR workflow and its constants.

## Known constants (don't re-look these up)

- Asana project **"VSO QA Auto + Delivery: Backlog"**: gid `1212459666284359`
- Asana custom field **"Work type"**: gid `1212459666284363`, option **"QA Automation"**: gid `1212459666284364`
- Assignee **Anton Melentiev**: Asana user gid `1207120594833706`
- Reviewer **Alexandr Shimkovich** (Александр Шимкович): GitHub login `shimkovich-a`. Verify this login is a collaborator on the *current* repo before using it (`gh api graphql -f query='query { repository(owner:"Playrix", name:"<repo>") { collaborators(query:"shimkovich", first:10) { nodes { login name } } } }'`) — if it's not found there, ask the user for the right reviewer on that repo instead of guessing.

## Procedure

### 1) Identify which changes this is for

Run `git status` and `git diff` (and `git diff master..HEAD` / `git log` if on a feature branch) in the current working directory's repo.

If there is exactly one coherent set of changes (one branch's diff, or one clear group of uncommitted edits), proceed with it — don't ask.

If it's ambiguous which part of the changes the task/PR should cover — e.g. there are multiple unrelated edits mixed together, multiple repos with pending changes, or no changes at all and the user didn't say what to describe — **stop and ask first** using AskUserQuestion. Offer the concrete options you found (e.g. "all uncommitted changes in `<repo>`", "branch `<name>` vs master", "only files X, Y"), not an open-ended question.

### 2) Commit any uncommitted changes

If `git status` shows uncommitted changes in the scope identified in step 1, call the **`am-commit`** skill yourself (via the Skill tool, `skill: "am-commit"`) on that scope before continuing — do this directly, don't ask the user to run `/am-commit` themselves and don't hand-roll a single commit here instead. The `am-commit` skill splits the changes into logical, reviewable commits.

(If working on `master`/`main`, create a feature branch — following the repo's existing naming convention if visible in recent branches — *before* invoking `am-commit`, so the commits land on a branch, not on `master`.)

Once `am-commit` finishes, the branch's commit history is itself the most reliable source for what the diff contains — use `git log` on the new commits as input to step 3 rather than re-reading the raw working-tree diff.

### 3) Write two descriptions — Asana looks forward, the PR looks back

Based on the same diff/commit log, write two distinct texts as the rule's Asana section describes: the **Asana task** text says what needs to be done (the goal), the **PR** text says what was done. They describe the same change and must stay consistent.

### 4) Create the Asana task

Create the task (`asana_create_task` / V2 `create_tasks`) with:
- `project_id`: `1212459666284359`
- `assignee`: `1207120594833706`
- `name`: short, specific title phrased as what needs to be done
- `notes` (or `html_notes`): the prescriptive Asana task text from step 3
- `custom_fields`: `{"1212459666284363": "1212459666284364"}` (Work type = QA Automation)
- `opt_fields`: include `permalink_url` so you get a stable link back without re-fetching

Keep the returned task gid and `permalink_url`.

### 5) Push and open the PR

- Push the branch (`git push -u origin <branch>`) — this is the point of the skill, so proceed, but still surface the branch/remote you're pushing to.
- Write the body per the rule's PR section. Put the task's `permalink_url` in the template's Asana/"Задача" section.
- Create the PR with `gh pr create --reviewer shimkovich-a ...`.
- Get the PR URL from the `gh pr create` output (or `gh pr view --json url`).

### 6) Link back from Asana

Add the PR URL as a comment on the Asana task (`text`: a short sentence with the link, e.g. `Создан PR: <pr_url>`).

### 7) Report back

Give the user both links: the Asana task (`permalink_url`) and the PR URL.
