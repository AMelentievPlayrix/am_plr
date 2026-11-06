# Briefs

Fill in the `{...}` slots. A brief is the subagent's only context, and nobody answers its questions. Every brief
that writes text for others repeats the rule from [execution.md](execution.md) § Text for people outside the
batch.

## Analysis (phase 1, one per case, read-only)

```text
You are doing a READ-ONLY feasibility analysis of ONE Qase test case for automation in
/Users/playrix/projects/vso-engine-autotests (Python, pytest, CATS2). Nobody will answer questions: never use
AskUserQuestion. Do NOT write code, create branches, commit, edit any file, post to Asana/GitHub or run tests.
Read origin/master (git show / git grep); do not switch branches. perfect-project is read-only for you.

## The question
Can this case be automated by changing ONLY vso-engine-autotests, without product/TestSDK changes in
/Users/playrix/projects/perfect-project and without manual steps? If not, what exactly is missing?

## Inputs
- Qase case VSO-{CASE_ID}: mcp__qase__get_test_case_data(project_code="VSO", test_case_id={CASE_ID}). The case is
  the source of truth: description, preconditions, every step and expected result, tags, platforms.
- Asana subtask: {ASANA_LINK}
- Linked blockers: {BLOCKER_LINKS_AND_TEXT or "none"}. Treat their text as claims to verify.
- Authoring rules the test must follow: /Users/playrix/projects/am_plr/skills/engine-create-autotest/reference/authoring-rules.md
- Traps: /Users/playrix/projects/am_plr/skills/engine-create-autotests-in-batch/reference/gotchas.md § Test state

## Known facts (verify, don't trust blindly)
{KNOWN_REPO_FACTS}

## SDK-specific hints (verify, don't trust blindly)
{SDK_HINTS}

## Deliver (your final message is the only thing the orchestrator sees), in English:
### VSO-{CASE_ID}: <title>
- Platforms (from Qase):
- Steps: numbered; each -> what must be verified -> HOW (existing step/API with path, or "NEW: <what>").
- Blocker assessment, per linked blocker: TRUE / FALSE / PARTLY for THIS case, with evidence (file:line).
- Hidden blockers: missing RPC, unreachable UI, stale Qase expectation (commit that changed the product),
  region, capability, data with no API.
- Verdict: FULLY AUTOMATABLE | AUTOMATABLE WITH CAVEATS (substitute named) | NEEDS BLOCKER FIX (which) | MANUAL
- Needed changes in vso-engine-autotests, each S/M/L; mark those other cases likely need too.
- "Absent / not sent" checks: how a positive control would prove the check can see the thing.
- Risks: what a first device run must prove.
- Evidence: paths with line numbers and the ref/commit read; Qase quotes.
```

## Blocker fix (phase 3, one per fix, in its own worktree)

```text
You implement ONE blocker fix. Nobody answers questions: never use AskUserQuestion; record open questions in your
item file and choose the safest reasonable option.

## Item
- Fix: {FIX_TITLE}. Repo: {REPO}. Worktree: {WORKTREE} (branch {BRANCH} from origin/master, already created).
- Why: {BLOCKER_EVIDENCE}. Cases it unblocks: {CASES}. Asana task: {ASANA_LINK} (read-only for you).
- Design agreed in the blocker plan: {DESIGN}
- Shared files other fixes also touch (keep edits minimal there): {OVERLAPS or "none"}

## Ground rules
- Work ONLY in your worktree. Never touch the main checkouts or other worktrees, never switch branches there.
- Write ONLY to your item file {ITEM_FILE}: keep its "Status:" line current; append "- YYYY-MM-DD HH:MM: ..." to
  § Log (plan written, decisive files read, each commit sha + subject, each check and result, problems).
- Never push, open PRs, post to Asana or GitHub, merge, build on TeamCity, or run devices. The orchestrator does.
- Put a timeout on long commands. No secrets in any file.
- Rules: /Users/playrix/projects/am_plr/rules/code.md, python.md (Python), communication.md (Russian commit text,
  plain hyphen). Match the surrounding style exactly (C++: tabs, the file header, existing naming).
- perfect-project hooks without VPN: see /Users/playrix/projects/am_plr/skills/engine-create-autotests-in-batch/reference/gotchas.md § Environment.

## Rounds
1. PLAN (this message): read the code; write § Plan in your item file (goal, files, API signatures or step names,
   verification, risks; 60 lines max); set Status "plan ready"; STOP and return a summary. No code edits.
2. IMPLEMENT (when resumed, with review fixes): implement, commit with the `am:commit` skill (Skill tool), leave
   the worktree clean, run the checks named below. Then add to your item file "## PR draft" (Russian title and
   body: perfect-project fills .github/pull_request_template.md; vso-engine-autotests uses the template in
   communication.md) and "## Prepared Asana comment" (2-3 Russian sentences: what was added, how it was checked).
   The text must read without batch context: no item ids, no "batch", "orchestrator", "memory".
- Checks: {CHECKS: e.g. make code-style-check; pytest --collect-only; compile if a build is possible}

## Final message (each round)
- Item / round / state; branch, worktree, commits (sha + subject) or "none"; checks and results; open questions.
```

## Test item (phase 5, one at a time)

```text
You are implementing ONE item of an unattended batch in /Users/playrix/projects/vso-engine-autotests.
Nobody will answer questions: never use AskUserQuestion.

## Item
- {ITEM_ID}: VSO-{CASE_ID} {TITLE} (Qase project VSO; read the case again with mcp__qase__get_test_case_data)
- Asana task: {ASANA_LINK}. Link it in the PR's "Ссылки". Read-only for you: no comments, no status changes.
- Branch: {BRANCH}, from origin/master. Platforms: {PLATFORMS}.
- What the analysis found: {ITEM_FILE} § Analysis, and board.md row VSO-{CASE_ID}. {EXTRA_NOTES}

## Procedure
Read and follow /Users/playrix/projects/am_plr/skills/engine-create-autotest/SKILL.md and its reference files
(authoring-rules.md, delivery.md, mcp-tools.md) before writing any code. The skill can't be loaded with the Skill
tool, so read the files. Obey /Users/playrix/projects/am_plr/rules/code.md, python.md, communication.md. Commit
ONLY through the `am:commit` skill, with delivery.md's split order. Read
/Users/playrix/projects/am_plr/skills/engine-create-autotests-in-batch/reference/gotchas.md first.

## Overrides to the skill (these win)
1. Never stop to ask. Where the skill says halt and ask, instead: commit what is worth keeping, push, open a DRAFT
   PR titled "[WIP] ..." (Russian) with the halt report as the body, log it, and finish.
2. If `git status --porcelain` is not empty, STOP and report "not started: dirty tree" with the file list.
   Otherwise `git fetch origin && git switch -c {BRANCH} origin/master`. Initials: {INITIALS}.
3. Runs go only through run_on_platform.py (delivery.md § Validation). Never edit, cat, grep or print .env.
4. Shared code: a change to framework code goes in its own commit. If it changes the behaviour of a step that
   merged tests use ({USERS_OF_TOUCHED_STEPS} - grep for others), rerun those tests on one platform each and list
   the runs in the PR. Never copy a helper from an open PR; if you need one that is not on master, halt (override 1).
5. Do NOT post to Asana. Write the comment you would post (Russian, delivery.md § Asana comment) into your item
   file under "## Prepared Asana comment". Text for others must read without batch context: no item ids, "batch",
   "orchestrator", "memory", scratch paths; name tests as "автотест VSO-<id> (#NNN)".
6. Do NOT request reviewers, merge, or run `gh pr edit` / `gh pr ready`: the orchestrator does.
7. Finish on master with a clean tree (`git switch master`).

## Environment facts (verified; from facts.md)
{ENVIRONMENT_FACTS: builds in artifacts/app and their TeamCity numbers, device ids per platform, non-secret
run_on_platform --set overrides, merged framework steps to use, where tests of this SDK live}
- Log to your item file at least every 15 min; put a timeout on every command.

## Item file
{ITEM_FILE}. Append ONLY to its § Log ("- YYYY-MM-DD HH:MM: ...") and the prepared comment. If it shows progress
from an earlier attempt, continue from there. Log, as facts: Qase platforms and key steps, branch, each commit (sha
+ subject), each run (platform, n/5, device id + model, PASSED/FAILED, failing step, BrowserStack build link),
diagnosis and change, positive-control runs, push, PR link. No secrets.

## Final message (the only thing the orchestrator sees)
- Status: green PR | draft PR [WIP] (halted) | not started (+ reason)
- Branch / PR URL
- Platforms and runs used: e.g. iOS 1/5 PASSED (dev 201 iPhone 14 Pro); Android 2/5 PASSED (dev 110 Pixel)
- Shared code touched and reruns of its users, or "none"
- Open problem: one line, or "none". Mark a suspected product defect "PRODUCT DEFECT?" with the product code quoted.
- Working tree clean and back on master: yes/no
```
