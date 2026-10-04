# Delivery: branch, commits, pull request, Asana comment, halt report

Applies to both `/vso-create-autotest` and `/vso-fix-autotest`.

## Output language

Different outputs go to different audiences, so they use different languages:

| Output | Language |
|---|---|
| Talking to the user in chat — progress, reports, questions, halt report | English |
| Commit messages | English |
| Pull request title and description | Russian |
| Asana comment | Russian |

Keep each one consistent throughout a task. An explicit instruction from the user overrides
this table; nothing else does. This is the only place the choice is stated — the workflow
steps do not repeat it.

---

## Branch — settle it before you start working

Do this **before** the first edit, not at PR time. Committing as you go needs a branch to
commit onto. A branch may already exist for this task — do not assume you must create one.

```bash
git branch --show-current
git status --porcelain                       # what was already dirty is the user's work
git fetch origin master
git log --oneline origin/master..HEAD        # what the current branch already carries
```

### On `master` (or a detached HEAD)

Create the branch yourself, from freshly fetched `origin/master`:

```bash
git switch -c <branch> origin/master
```

| Task | Pattern |
|---|---|
| New test | `feature/<initials>/test_<case_id>_<short_slug>` |
| Fixing a test | `fix/<initials>/test_<case_id>_<short_slug>` |

Derive `<initials>` from `git config user.name`; ask when ambiguous.

### Already on some other branch

**Ask before doing anything.** Never silently create a second branch on top of the user's
work, and never silently commit onto a branch that belongs to something else. Use
`AskUserQuestion` with two concrete options:

- **Use the current branch `<name>`** — say how many commits it is ahead of `origin/master`
  and name them, so the user can see what they would be adding to.
- **Create a new branch `<proposed name>` from `origin/master`** — say that the current
  branch's commits would be left behind.

Give the user the facts to decide with: current branch name, commits ahead, dirty files, and
whether the branch looks related to this task. Do not guess from the branch name alone, even
when it matches the expected pattern — a name that looks right can still be someone else's
in-flight work.

Reusing the current branch is fine; that is what the user may want. What is not fine is
choosing for them.

### Either way

Record the pre-existing dirty files. Uncommitted work you did not make is the user's —
never stage, commit, revert or stash it. If it overlaps files you must change, ask first.

---

## Commits — small, logical, as you go

**Commit each finished piece of work when it is finished.** Do not accumulate everything
into one commit at the end. The goal is a history a reviewer can read commit by commit and
understand what happened, in order, without opening the whole diff.

### One commit = one logical change

Split along these boundaries. Skip the ones that do not apply.

**Creating a test:**

1. new or extended step in `framework/test_management/test_steps/...`
2. any other framework change the test needs (enum value, util, fixture) — separate commit
   per concern
3. the test file itself
4. each fix from a failed validation run — its own commit, one per cause
5. the recorded validation results

**Fixing a test:**

1. the root-cause fix — one commit per cause, even when two causes live in one file
2. each follow-up fix from a further failing run — its own commit
3. a latent copy of the same bug found elsewhere — its own commit
4. the recorded validation results

Never mix a framework change and a test change in one commit. Never mix two unrelated
fixes. When you catch yourself writing "and" in a subject line, it is two commits.

### Staging discipline

Stage explicit paths only:

```bash
git add path/to/file.py path/to/other.py
git status --porcelain          # confirm nothing else got picked up
git diff --cached --stat        # confirm the commit is what you think it is
git commit -m "<subject>"
```

Never `git add -A`, `git add .`, or `git commit -a` — they sweep up the user's work,
`.env`, and `artifacts/`.

### Commit messages

Short, plain, in simple words. Say **what changed**, so someone scanning `git log --oneline`
understands the step without opening the diff.

- One line. Aim for 50 characters, hard limit 72. No trailing period.
- Plain words over jargon. No ticket-speak, no internal shorthand.
- English, per § Output language — the PR and the Asana comment are Russian, commits are not.
- Add a body only when the *why* is not obvious from the subject. Two or three lines, blank
  line after the subject.

| Bad | Why | Better |
|---|---|---|
| `fix` | Says nothing | `Fix purchase button locator on iOS` |
| `wip` | Not a change | — commit when the piece is done |
| `Updates` | Which ones? | `Add step that waits for the scene to load` |
| `Add test and new step and fix tag` | Three changes | Three commits |
| `Refactor` | Hides the scope | `Move shared purchase code to common_part` |
| `Review fixes` | Reviewer-only context | `Remove extra sleep from event check` |

### Each commit should stand on its own

Before committing, the tree should be importable and style-clean:

```bash
make code-style-check
```

A reviewer should be able to check out any single commit and find the repo in a sane state.
Do not commit a half-written step that the next commit repairs.

### Do not rewrite history

No `--amend` on a pushed commit, no interactive rebase, no squashing your own history to
"tidy it up" — the step-by-step trail is the point. No `--force` push, no `git reset --hard`.
Fix a mistake with a new commit that says what it fixes.

---

## Pull request

### Preconditions

Open the PR only after:

- a green target run on every applicable platform;
- `make code-style-check` passing;
- `.env` restored to its original content;
- every change committed, and nothing of the user's staged.

### Check whether the change is still needed

Before pushing, compare against the default branch:

```bash
git fetch origin master
git log --oneline origin/master -20
git log origin/master -S'<distinctive_token_from_your_change>' --oneline
```

If someone has already landed the same fix, **do not open the PR.** Report the commit, its
author and date, and ask the user how to proceed. This check has caught duplicate work
before; run it every time.

### Push and open

```bash
git log --oneline origin/master..HEAD    # read your own history as a reviewer would
git push -u origin <branch>
gh pr create --base master --title "<title>" --body-file <file>
```

No GitHub MCP is configured in this workspace, so use `gh`; prefer a GitHub MCP if one is
added later. This repository has no `.github/pull_request_template.md` — use the body
template below, but check for a template on every run in case one is added.

### PR body template

Title and body in Russian, matching the repository's history.

```markdown
## Что сделано
<1–3 sentences: what the PR adds or repairs.>

## Причина
<For a fix: the root cause, with evidence. For a new test: the Qase case and why now.>

## Изменения
<A top-level summary of what changed — a few bullets at the level a reviewer thinks in:
which step was added, which locator was corrected, which framework file was touched.
Not a commit list; the commits are in the branch and speak for themselves.>

## Проверка
| Платформа | Команда | Результат |
|---|---|---|
| macOS | `make ai-run-tests key=<test> platform_to_run=macOS` | PASSED |

## Ссылки
- Qase: VSO-<case_id>
- Asana: <task url>

## Риски и ограничения
<Commented-out steps, unverified expectations, known flakiness — or "нет".>
```

Summarise at the level of the work, not the log. The PR description says *what was done*;
the commit history shows *how it got there*. Do not paste `git log` into the body.

Still read `git log --oneline origin/master..HEAD` yourself before pushing. If it does not
read as a clear sequence of steps, say so to the user — do not let a tidy summary cover for
commits that were split badly.

### Prohibitions

- Never commit `.env`, tokens, or `artifacts/`.
- Do not merge the PR.

---

## Asana comment

Post with `mcp__asana__asana_create_task_story(task_id=<gid>, html_text=...)`.
The task gid is the last numeric segment of the Asana URL.

Allowed HTML: `<body>`, `<strong>`, `<em>`, `<u>`, `<s>`, `<code>`, `<ol>`, `<ul>`,
`<li>`, `<a>`, `<blockquote>`, `<pre>`. A single root `<body>` element, well-formed XML.
No other elements, no attributes except on `<a>`.

**Comment only. Do not close, reassign or re-status the task unless the user asks.**

### What the comment must contain

Write it so a teammate who never saw the session can follow it:

1. **Что было** — the symptom for a fix, or the case being automated for a new test.
2. **Как нашли причину** — the actual investigation path: which artifact, log line, build
   or command produced the decisive evidence. Quote the decisive line in `<pre>`.
3. **Причина** — the root cause in one or two sentences, and why it did not reproduce
   in the obvious environment if that is relevant.
4. **Что сделано** — the change described at a top level, and why that change and not a
   workaround. Summarise; do not list commits or paste SHAs.
5. **Проверка** — platforms, commands, results, number of runs used.
6. **Ссылки** — PR, Qase case, related commits.
7. **Замечено попутно** — anything worth a separate task: latent copies of the same bug,
   flaky neighbours, stale rules. Optional but valuable.

Report honestly. If something is unverified, say so in the comment rather than implying
a stronger result than you have.

### Skeleton

```html
<body><strong>Что было</strong>
...

<strong>Как нашли причину</strong>
...
<pre>decisive log line</pre>

<strong>Причина</strong>
...

<strong>Что сделано</strong>
...

<strong>Проверка</strong>
...

<strong>Ссылки</strong>
<ul><li>PR: ...</li><li>Qase: VSO-...</li></ul></body>
```

---

## Halt report — run budget exhausted

Trigger this when 5 automatic runs on a platform are used up, or an early stop condition
fires. Keep it short and plain: four blocks, no essay, no speculation dressed as fact.

Commit whatever is finished and worth keeping **before** reporting, so the user can read the
trail. Do not leave the work only in the working tree.

```markdown
**Stopped: run budget used up (<used>/5 on <platform>)**

**What I found**
<The failure symptom and the most likely cause, with the evidence line.>

**What I changed**
- `<sha>` <subject> — <did it help: yes / no / partially>

**What I tried**
1. <hypothesis> → <run result>
2. ...

**What is still unclear**
<The open question blocking progress.>
```

Then ask the user, with `AskUserQuestion`, how to proceed. Offer concrete options:

- continue with a specific additional run budget (e.g. +3 or +5 runs);
- switch to diagnosis only, no further runs;
- stop and hand over the report;
- treat it as a product defect and file a task instead.

State the current branch, the commits made so far, and the working-tree state so the user
can decide safely. Do not continue running until the user answers.
