# Phase 7: separate-platform track

Some cases list a platform this host cannot run: UWP and Windows need a Windows host, and macOS needs a Mac. That
part becomes its own track, with its own Asana subtasks and a hand-off file for an agent on the other host. In the
Marketing batch:
- 15 cases got "(UWP)" subtasks;
- a Windows agent automated them in 3 PRs (#404-#406);
- the Mac session folded the results back into its memory.

## When

After the main platforms of the affected cases are merged, so the other host starts from tests that already pass
elsewhere. Decide it in the test plan (phase 4) and list the cases in board.md.

## Asana

The original case subtasks are marked done when their main-platform PR merges, so the track needs new tasks. Create
one subtask per case under the batch parent (Russian, written as a task, assigned to the batch author):

- title: `[Engine/SDK] Автотест VSO-<id> (<Platform>): <case title>`;
- description: `Нужно добавить платформу <Platform> в автотест VSO-<id> (<test path>), чтобы ...`, then «Что
  известно» (the platform specifics from the item file) and «Готово, когда» («тест проходит на <Platform>, PR смержен»).

Add one board.md row per subtask (`VSO-<id> (<Platform>)`), and remove the platform from the original rows.
Creating these tasks is part of the plan the user approved; list them in the test plan.

## Hand-off file: `handoff-<platform>.md`

The other host cannot see this memory folder (it is local), so the file must stand alone. The user passes it on (paste
it into a session there). Contents:

1. **Goal and scope**: the cases, their test files (repo-relative paths), and the cases deliberately left out, with
   reasons.
2. **Asana**: the subtask link of every case.
3. **Environment**:
   - the TestSDK build type for the platform (e.g. `PerfectProject_TestSDK_Uwp`) and the minimum perfect-project
     commit it needs (one containing the merged blocker fixes);
   - config values from `config/config.py`;
   - the non-secret `.env` keys. If the other host's `.env` has no block for the platform, pass them with
     `run_on_platform.py --set`. Never values of secrets.
4. **Known platform specifics** from the item files: expected values that differ per platform, stubs, steps that are
   skipped on the platform. Name the steps and files involved.
5. **Process**:
   - follow `am_plr/skills/engine-create-autotest` for each case (add the platform tag, run, fix platform-specific
     expectations, record the run);
   - one PR per group of cases, or per case;
   - for each PR, the [merge-loop.md](merge-loop.md) routine: comment and done on the "(<Platform>)" subtask; Qase
     stays automated; `/am:log`;
   - on the other host, ask the user about a long-term memory folder there ([rules/long-term-memory.md](../../../rules/long-term-memory.md)).
6. **Traps**: the [gotchas.md](gotchas.md) items that apply (positive controls, state between tests, case-sensitive
   `platform_to_run`).
7. **Report back**: the final link list ([merge-loop.md](merge-loop.md) § Final reply) and any new blocker task.

Use repo-relative skill paths and public links (Asana, GitHub, Qase) only, never `/Users/...` paths of this host.
Put "hand-off ready" under **Needs you**.

## Fold-back

When the user says the other host is done:
1. Read the "(<Platform>)" subtasks (completed, last comments) and `gh pr list --state all --search` for their PRs.
2. Update board.md rows to merged with their PRs, and log it in events.md.
3. Add any new blocker or follow-up to board.md, and to **Needs you** if someone has to act.
4. Update status.md.
