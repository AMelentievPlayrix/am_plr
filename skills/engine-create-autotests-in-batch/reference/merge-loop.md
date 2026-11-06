# Merge loop

Runs for every green vso-engine-autotests PR of the approved plan, right after the orchestrator verifies it:
framework PRs in phase 3 (covered by approval 1), and test and follow-up PRs in phases 5-6 (approval 2). The user
does not trigger it.

perfect-project PRs are never merged here. They go through Mergify after review, and the user runs
`/am:merge-pp` ([blockers.md](blockers.md) § Merge and close).

## Per PR

1. **Check the state.**
   `gh pr view <n> --repo Playrix/vso-engine-autotests --json state,isDraft,mergeable,mergeStateStatus,reviewDecision,baseRefName,title`.
   Proceed when it is `OPEN`, not draft, on base `master` and `MERGEABLE`.
   - `BLOCKED`: the ruleset wants something, e.g. an approval of the last push; check the current ruleset rather
     than assuming.
   - `CONFLICTING`: rebase the branch only if it was never pushed; otherwise fix it in a new commit.

   In either case, put it under **Needs you** with the reason and go on.
2. **Request the reviewer** if not yet requested (`gh pr edit <n> --add-reviewer shimkovich-a`). Do not wait for
   the review.
3. **Merge** with a squash:

   ```bash
   gh pr merge <n> --repo Playrix/vso-engine-autotests --squash \
     --subject "<PR title> (#<n>)" --body "<1-2 строки, что сделано>"
   ```

   - Append the session's commit attribution lines to the body.
   - On **any** error (502, timeout, GraphQL), read `gh pr view <n> --json state,mergeCommit` before retrying. A blind
     retry once created an empty duplicate commit.
   - If the classifier refuses the merge, put the exact command under **Needs you** and continue with the items that
     do not need this PR.
4. **Asana.**
   - Post the item's prepared comment (`html_text`, Russian), updated with the merge commit and the final PR state.
   - On an error or timeout, read the task's stories before retrying.
   - Then mark the task done:
     - a case subtask: done (covered by approval 2), and read back `completed`;
     - a blocker task: comment, and close it only if approval 1 named it.

   Record the story gid in events.md. If Asana is down, record the pending write in resume.md and go on.
5. **Qase**, for test PRs whose case is fully covered:
   `<am_plr>/.venv/bin/python -I <skill>/scripts/qase_case.py automation <case_id> 2`. The script reads the value
   back; a mismatch exits with 3. A partly covered case keeps its value, with the reason noted in board.md.
6. **Branch cleanup.**
   - Run `git branch -D <branch>`.
   - Remove the remote branch if the repo did not delete it on merge: `git ls-remote --heads origin <branch>`, then
     `git push origin --delete <branch>`.
   - Run `git switch master && git pull --ff-only`. When SSH fails, use the HTTPS remote URL.
7. **Log** with `/am:log` (Skill tool, `skill: "am:log"`) for the merged PR.
8. **Memory.** Update the row in board.md (`✅ merged <sha>`), add a line to events.md, and update status.md "Last
   merged" and the counts.

Then the next item starts from the fresh master.

## Final reply

When the plan's PRs are all merged, or after a run of merges at close-out, reply with one line per PR. Drop any
column that does not apply (no Qase for a framework PR, no Asana subtask for a follow-up without one).

```markdown
- [#378](https://github.com/Playrix/vso-engine-autotests/pull/378) - [Автотест VSO-16958: launch_start](<asana url>) - [VSO-16958](https://app.qase.io/case/VSO-16958) - launch_start, iOS/Android/macOS
- [#390](https://github.com/Playrix/vso-engine-autotests/pull/390) - [нет remote API у PreTosTrackerManager](<asana url>) - PreTosTracker client, validated by VSO-16972
```

- PRs as `#NNN`, Qase cases as `VSO-NNNNN`, and Asana tasks by their name as it reads in Asana (shortened).
- Then **Needs you**, if it is not empty.
