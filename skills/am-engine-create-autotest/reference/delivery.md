# Delivery: branch, commits, pull request, Asana comment, halt report

Applies to both `/am-engine-create-autotest` and `/am-engine-fix-autotest`.

Language, the generic PR body and Asana formatting come from the rule
[writing-git-github-asana.md](../../../rules/writing-git-github-asana.md). Every commit goes through
the `am-commit` skill. This file adds only what is specific to vso-engine-autotests.

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

---

## Commits — as you go, split like this

**Commit each finished piece of work when it is finished** by calling the `am-commit` skill
with that piece's paths, this split order and `make code-style-check` as the pre-commit check.
Do not accumulate everything into one commit at the end.

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

Never mix a framework change and a test change in one commit.

---

## Validation and run budget

Validate on every applicable platform unless the user says skip:

| Platform tag | When |
|---|---|
| `iOS`, `Android` | Always (runs on BrowserStack) |
| `macOS`, `android_on_linux`, `ios_on_linux` | Only when the host is macOS |
| `Windows`, `UWP` | Only when the host is Windows |

For each platform:

1. Record the original `.env`, then edit its `# App config` block: comment out the old platform,
   uncomment the target one.
2. `make ai-run-tests key=<test_name> platform_to_run=<PLATFORM_TAG>`
3. Validate only active, uncommented code.

**Restore `.env` to its original content when validation finishes — including when you stop early
or hit the run budget** — and say so in the final report. `.env` is never committed.

**At most 5 automatic runs per platform** (the repo's `.cursor/rules/test.mdc` says 3; this limit
wins). Before each rerun, diagnose: name the exact symptom and the failing step, list 1–3 likely
causes, pick the most likely, and make the smallest change that addresses it. Never rerun
unchanged. Commit each fix right after the run that justified it, one per cause, so the history
shows the sequence of hypotheses; never leave several runs' worth of edits uncommitted.

### Stop conditions

Stop **before** the budget is spent when:

- the same failure repeats and you have no new root-cause hypothesis;
- the failure is infrastructure — relay server, BrowserStack, certificates, device allocation;
- a required step or element does not exist and cannot be confirmed;
- the case itself is contradictory, or contradicts observed product behaviour (a likely
  **product defect**) and needs a decision;
- the remaining change would stop being local and become a refactor.

Then commit what is worth keeping and write the halt report below. Do not silently continue.

### Forbidden fixes

Never buy a green run with any of these; each makes the failure invisible instead of solved:

| Anti-fix | Why it is wrong |
|---|---|
| Raising a timeout with no established cause | Converts a real failure into a slow one |
| Adding `sleep` to "let it settle" | Hides a race; breaks again on a slower machine |
| Adding retries or a `while` until it passes | Hides non-determinism |
| Broadening an `except` | Swallows the actual signal |
| Weakening or removing an assertion | Silently reduces what the test guarantees |
| A fallback `if` for an unconfirmed UI state | Two code paths, neither verified |
| A broad or fuzzy locator | Matches the wrong element eventually |
| `skip` / `xfail` as the fix | Removes coverage without deciding anything |

A `sleep` is acceptable only as an explicitly temporary stabiliser: short, commented with its
reason, recorded as a residual risk, and only when no explicit wait exists.

---

## Pull request

### Preconditions

Open the PR only after:

- a green target run on every applicable platform;
- `make code-style-check` passing;
- `.env` restored to its original content;
- every change committed, and nothing of the user's staged.

Then run the rule's "still needed" and own-history checks, and push. This repository has no
`.github/pull_request_template.md`, so use the rule's body template with these sections filled in:

- **Причина** — for a fix: the root cause with evidence; for a new test: the Qase case and why now.
- **Проверка** — a table per platform:

  | Платформа | Команда | Результат |
  |---|---|---|
  | macOS | `make ai-run-tests key=<test> platform_to_run=macOS` | PASSED |

- **Ссылки** — `Qase: VSO-<case_id>` and the Asana task.
- **Риски и ограничения** — commented-out steps, unverified expectations, known flakiness.

---

## Asana comment

Post it as `html_text` (formatting rules are in the rule). Write it so a teammate who never saw
the session can follow it:

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
