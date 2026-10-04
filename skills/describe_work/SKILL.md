---
name: describe_work
description: File an Asana task for a set of code changes, open a matching GitHub PR, and cross-link both. Use when asked to "describe the work", "write up these changes", or close out a change with a task+PR pair.
disable-model-invocation: true
argument-hint: "[optional: which changes/diff to describe]"
---

# Describe Work: Asana task + GitHub PR

Given a set of code changes (uncommitted, committed on a branch, or described by the user), produce:
1. An Asana task describing the change.
2. A GitHub PR for the change, linked to that task.
3. A comment on the Asana task linking back to the PR.

**Language rule:** every piece of text you write into Asana or GitHub (task title/description, PR title/body, Asana comment) must be in **Russian**. Describe the work clearly but concisely — don't pad it. Don't translate terms, proper names, identifiers, or other parts that are naturally in English (API names, function/class names, library names, etc.) — keep those as-is inside the Russian text.

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

If `git status` shows uncommitted changes in the scope identified in step 1, call the **`commit`** skill yourself (via the Skill tool, `skill: "commit"`) on that scope before continuing — do this directly, don't ask the user to run `/commit` themselves and don't hand-roll a single commit here instead. The `commit` skill splits the changes into logical, reviewable commits with Russian commit messages.

(If working on `master`/`main`, create a feature branch — following the repo's existing naming convention if visible in recent branches — *before* invoking `commit`, so the commits land on a branch, not on `master`.)

Once `commit` finishes, the branch's commit history is itself the most reliable source for what the diff contains — use `git log` on the new commits as input to step 3 rather than re-reading the raw working-tree diff.

### 3) Write two descriptions — Asana looks forward, the PR looks back

Based on the same diff/commit log, write two distinct texts, both **in Russian** per the language rule above:

- **Asana task text (prescriptive — what needs to be done):** phrase it as the goal or problem being addressed, like a task written *before* the work — not a changelog of the diff. Describe the need/requirement that the change satisfies, not a list of what was edited. E.g. "Нужно добавить валидацию X, чтобы ..." rather than "Добавлена валидация X".
- **PR title/body text (retrospective — what was done):** phrase it as what was actually implemented/changed, matching the existing template's language (e.g. "Что поменялось для пользователей?").

Keep both consistent with each other — they describe the same underlying change, just in different tense and purpose. Don't write the Asana text as a copy of the PR text with the tense flipped mechanically; actually frame it around the goal.

### 4) Create the Asana task

Use `asana_create_task` with:
- `project_id`: `1212459666284359`
- `assignee`: `1207120594833706`
- `name`: short, specific title phrased as what needs to be done, in Russian
- `notes` (or `html_notes`): the prescriptive Asana task text from step 3
- `custom_fields`: `{"1212459666284363": "1212459666284364"}` (Work type = QA Automation)
- `opt_fields`: include `permalink_url` so you get a stable link back without re-fetching

Keep the returned task gid and `permalink_url`.

### 5) Push and open the PR

- Push the branch (`git push -u origin <branch>`) — this is the point of the skill, so proceed, but still surface the branch/remote you're pushing to.
- Check whether `.github/pull_request_template.md` exists in the repo root; if so, fill it in, in Russian (it has a "Задача" section for the Asana link — put the task's `permalink_url` there).
- Create the PR with `gh pr create --reviewer shimkovich-a ...` — title and body in Russian (check a few recent PR titles with `gh pr list` for the repo's style/tone), body = filled-in template or the retrospective PR text from step 3 plus the Asana link if no template exists.
- Get the PR URL from the `gh pr create` output (or `gh pr view --json url`).

### 6) Link back from Asana

Add the PR URL as a comment on the Asana task with `asana_create_task_story` (`text`: a short Russian sentence with the PR link, e.g. `Создан PR: <pr_url>`).

### 7) Report back

Give the user both links: the Asana task (`permalink_url`) and the PR URL.
