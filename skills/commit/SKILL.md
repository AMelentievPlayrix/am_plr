---
name: commit
description: Split the current uncommitted changes into several independent, logically-scoped commits instead of one big commit. Use when asked to "commit this", "commit in logical parts", or before opening a PR when changes touch several unrelated things. Also invoked by the describe_work skill to commit pending changes before filing a task/PR.
argument-hint: "[optional: scope/path to limit which changes get committed]"
---

# Commit: split changes into logical commits

Turn the current working-tree changes into a small series of commits, each one a coherent, independent logical unit, instead of a single commit with everything mixed together. The goal is reviewability: someone reading `git log -p` should be able to understand each change in isolation.

## Procedure

### 1) Survey the changes

Run `git status` and `git diff` (and `git diff --stat` for an overview) in the target repo. If `$ARGUMENTS` names a path/scope, limit the survey to that.

Read through the diff, not just the file list — logical grouping is about *what the change does*, not which directory it's in. Two edits in the same file can belong to different commits; two edits in different files can belong together.

### 2) Group into logical units

Group hunks/files into commits by what they accomplish together, e.g.:
- A behavioral fix/feature vs. unrelated formatting/renames touched along the way
- A new helper/utility vs. the call sites that start using it (these two usually belong in the *same* commit if the helper has no other purpose yet — don't split a change from its only usage)
- Test changes that verify a specific code change go with that code change, not bundled into one giant "tests" commit
- Unrelated fixes noticed in passing go in their own separate commit, not folded into the main change
- Generated/lock files go with the change that caused their regeneration

Order commits so the result is reviewable top to bottom (e.g. foundational/helper changes before the code that uses them).

If the changes genuinely don't decompose (one small self-contained edit), it's fine to make a single commit — don't force an artificial split.

### 3) Confirm the plan for anything non-obvious

If the grouping is clear from the diff, proceed without asking. If you're unsure whether two pieces belong together or apart, or whether something unrelated should be included at all, ask the user rather than guessing — a wrong split is worse than a pause.

### 4) Stage and commit incrementally

For each logical group, stage precisely the relevant hunks/files:
- Prefer `git add <specific files>` when a commit's changes live in whole files.
- Use `git add -p` (or stage specific hunks another way) when a single file contains changes belonging to more than one commit.
- After staging, run `git diff --staged` to verify exactly the intended hunks are staged — nothing extra, nothing missing — before committing.

Write each commit message in **Russian** (matching this repo's convention — check `git log --oneline -10` if unsure), in the imperative/descriptive style already used in the repo's history (e.g. `Исправлено ...`, `Добавлено ...`, `Обновлены ...`). Keep the subject line short and specific to what that commit changes; add a body only if the "why" isn't obvious from the subject + diff. Don't describe the task or ticket in the message — describe the change itself. English terms, identifiers, and proper names stay in English inside an otherwise Russian message (don't translate them).

Commit with a heredoc to keep formatting exact, same as any other commit:
```
git commit -m "$(cat <<'EOF'
<субъект на русском>

<опциональное тело на русском, если нужно>
EOF
)"
```

### 5) Verify the result

After all commits, run `git status` (should be clean, or show only what was intentionally left out) and `git log --oneline -n <count>` to show the resulting sequence back to the user. Briefly state what each commit contains.

## Constraints

- Never use `git reset --hard`, `git checkout .` / `git restore .`, or `git clean -f` to "start over" — if a staging mistake happens, unstage with `git restore --staged <path>` instead.
- Never force-push or amend pre-existing commits that were already on the branch before this session touched it.
- Don't invent a rationale for changes you didn't write and can't infer from the diff — if the "why" isn't clear from the diff alone, ask rather than fabricate.
