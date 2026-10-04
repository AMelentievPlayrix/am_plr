---
name: commit
description: The single place for commit policy. Split the current uncommitted changes into several independent, logically-scoped commits instead of one big commit. Use when asked to "commit this", "commit in logical parts", or before opening a PR. Every other skill that needs to commit invokes this skill instead of committing itself.
argument-hint: "[optional: paths/scope to commit, plus any project-specific split order]"
allowed-tools: Bash(git status *) Bash(git diff *) Bash(git log *) Bash(git add *) Bash(git restore --staged *) Bash(git commit *) Bash(make code-style-check *)
---

# Commit: split changes into logical commits

Turn the current working-tree changes into a small series of commits, each one a coherent, independent logical unit, instead of a single commit with everything mixed together. The goal is reviewability: someone reading `git log -p` should be able to understand each change in isolation.

This skill owns the commit policy. Other skills call it (Skill tool, `skill: "am-plr:commit"`) with the paths to commit and, if they have one, a project-specific split order. Commit message language comes from the rule [writing-git-github-asana.md](../../rules/writing-git-github-asana.md) (Russian).

## Procedure

### 1) Survey the changes

Run `git status` and `git diff` (and `git diff --stat` for an overview) in the target repo. If `$ARGUMENTS` names a path/scope, limit the survey to that.

Read through the diff, not just the file list — logical grouping is about *what the change does*, not which directory it's in. Two edits in the same file can belong to different commits; two edits in different files can belong together.

Uncommitted changes you did not make belong to the user: leave them out unless the user asked to commit them. If they overlap the files you must commit, ask first.

### 2) Group into logical units

One commit = one logical change. If the subject would need "и", it is two commits. Group hunks/files by what they accomplish together, e.g.:
- A behavioral fix/feature vs. unrelated formatting/renames touched along the way
- A new helper/utility vs. the call sites that start using it (these two usually belong in the *same* commit if the helper has no other purpose yet — don't split a change from its only usage)
- Test changes that verify a specific code change go with that code change, not bundled into one giant "tests" commit
- Unrelated fixes noticed in passing go in their own separate commit, not folded into the main change
- Generated/lock files go with the change that caused their regeneration

If the caller passed a project-specific split order, follow it. Order commits so the result is reviewable top to bottom (e.g. foundational/helper changes before the code that uses them). Each commit should leave the repo in a sane state — no half-written piece that the next commit repairs.

If the changes genuinely don't decompose (one small self-contained edit), it's fine to make a single commit — don't force an artificial split.

### 3) Confirm the plan for anything non-obvious

If the grouping is clear from the diff, proceed without asking. If you're unsure whether two pieces belong together or apart, or whether something unrelated should be included at all, ask the user rather than guessing — a wrong split is worse than a pause.

### 4) Stage and commit incrementally

For each logical group, stage precisely the relevant hunks/files:
- Prefer `git add <specific files>` when a commit's changes live in whole files.
- Use `git add -p` (or stage specific hunks another way) when a single file contains changes belonging to more than one commit.
- Never `git add -A`, `git add .` or `git commit -a` — they sweep up the user's work and secrets.
- After staging, run `git diff --staged --stat` (and the full diff if unsure) to verify exactly the intended hunks are staged — nothing extra, nothing missing — before committing.
- If the repo has a pre-commit check the caller named (e.g. `make code-style-check`), run it before each commit.

**Message:**
- Subject: one line, about 50 characters, hard limit 72, no trailing period. Say **what changed**, in the past-tense style of the repo's history (check `git log --oneline -10`): `Исправлено ...`, `Добавлено ...`, `Обновлены ...`.
- Body only when the *why* is not obvious from the subject: 2–3 lines after a blank line.
- Describe the change, not the task or ticket. Never invent a reason you can't infer from the diff — ask instead.

| Bad | Why | Better |
|---|---|---|
| `fix` / `Исправления` | Says nothing | `Исправлен локатор кнопки покупки на iOS` |
| `wip` | Not a change | Commit when the piece is done |
| `Добавлен тест, новый шаг и тег` | Three changes | Three commits |
| `Рефакторинг` | Hides the scope | `Общий код покупок вынесен в common_part` |
| `Правки по ревью` | Reviewer-only context | `Убран лишний sleep из проверки события` |

Commit with a heredoc to keep formatting exact:
```
git commit -m "$(cat <<'EOF'
<тема на русском>

<необязательное тело>
EOF
)"
```

### 5) Verify the result

After all commits, run `git status` (should be clean, or show only what was intentionally left out) and `git log --oneline -n <count>` to show the resulting sequence back to the user. Briefly state what each commit contains.

## Constraints

- Never commit `.env`, tokens, secrets or `artifacts/`.
- Never rewrite pushed history: no `--amend` on pushed commits, no interactive rebase or squash, no `--force` push. Fix a mistake with a new commit that says what it fixes.
- Never use `git reset --hard`, `git checkout .` / `git restore .`, or `git clean -f` to "start over" — if a staging mistake happens, unstage with `git restore --staged <path>` instead.
