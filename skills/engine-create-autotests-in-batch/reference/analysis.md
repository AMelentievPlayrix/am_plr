# Phase 1: analysis

Read-only everywhere except the memory folder. Ends when every case has a verdict and every blocker a verified
status, ready for the blocker plan ([blockers.md](blockers.md)).

## Read Asana

Read the parent task and every subtask: name, Qase id, dependencies (dependencies are blockers). Read each blocker
task, description and comments. **Treat blocker text as a claim, not a fact**: in the Marketing batch, one of four
Asana blockers was false, one was real for only 6 of its 15 linked cases, and 9 dependency links were wrong. Write
one row per blocker in board.md § Blockers, with "Real?" still empty.

## Repo survey

Do this once, before launching subagents, so every brief starts from the same verified facts. Use
`git fetch origin master`, `git show origin/master:<path>`, `git grep <pattern> origin/master` and `git ls-tree`.
Do not switch branches. Record the base commits of vso-engine-autotests and perfect-project (`origin/master`; the
local checkout may be older) in facts.md.

Check on `origin/master` and record each result with its path in facts.md:

- **SDK under test**: its RPC client in `framework/services/app_api/sdk/`, widget steps in
  `framework/test_management/test_steps/app_widget/<sdk>/`, SDK-level steps or services, and each step's platform
  decorators.
- **Existing tests** for this SDK and the closest neighbours, with how they verify (backend API, device log,
  network log, app log).
- **Verification channels**: device logs (`BSController.get_device_logs`, `DeviceSteps.check_log_pattern_matches`),
  BrowserStack HAR (`check_substring_entries_in_network_logs`), the local proxy (`framework/services/proxy`, and on
  which platforms it works), the app's own log (`log.htm`), backend clients.
- **Session setup**: `framework/services/browserstack/browserstack_init.yml`, `utils.update_bs_config` (region via
  `BS_CUSTOM_COUNTRY`), the driver fixture scope, and the in-session auto-retry (`tests/conftest_auto_retry.py`).
- **Tags** in `framework/test_management/enums/common/tags.py`.
- **Product entry points** in perfect-project: the widget or manager behind each case and its Autotests RPC
  registration (or the absence of one).
- **Earlier research**: vso-engine-autotests `artifacts/` (git-ignored, local only).

Then write the SDK-specific hints for the brief: the paths above, plus anything known from earlier batches,
phrased as claims to verify.

## Launch

Fill in the analysis brief ([briefs.md](briefs.md) § Analysis) per case. Launch one read-only general-purpose
subagent per case with `run_in_background: true`, in waves of at most 20 (the concurrent-subagent limit). Launch
each queued case as a slot frees. Subagents never write the memory folder.

## As each report arrives

1. Write its verdict and summary into `items/T<n>_<id>.md` § Analysis, and update its board.md row.
2. Move anything shared into facts.md, tagged with its source.
3. **Verify in source** every claim that changes another case, and every blocker assessment (below). Record each
   as `RESOLVED:` with file:line and the commit you read.
4. Log it in events.md.

## Blocker verification

For each blocker (Asana or found), and for each case linked to it, decide **TRUE / FALSE / PARTLY** with evidence:

- TRUE: the case needs something that does not exist, e.g. no RPC for a widget button (file:line of the handler
  list), a channel that does not carry the data, or a Qase expectation the product no longer produces (the commit
  that removed it).
- FALSE: the case can be automated without it. Say how. Name the dependency link to remove.
- PARTLY: true for some cases or platforms only. Name them.

Hidden blockers found by analysis get the next free letter. A stale or contradictory Qase case is a blocker too
(fix type "Qase-side"). Fill in "Real?", "Cases" and a first "Fix type" in board.md § Blockers.

## Cross-checking

- **Contradictions**: if two reports disagree, read the source and settle it (`RESOLVED:`), then fix the dependent
  verdicts.
- **Later evidence overturns earlier assumptions**: write `CORRECTS:` in facts.md, revise each affected item and
  row, and log it. Example: real CI data showed iOS syslog on BrowserStack has no Debug/Info lines.
- **Inconsistent expectations across cases** (two cases expect different values for one field): check the
  product, then record it as an open question.
- **Missing reports**: relaunch once, naming the gap.

## Verdicts

| Verdict | Meaning |
|---|---|
| Fully automatable | Every expected result checked, with substitutes named |
| Partly automatable | Implementable, but some expected result has no check: say which one and why |
| Needs a blocker fix | Name the blocker letters |
| Manual by nature | Say why |

"Fully" means every expected result has an automated check. Named substitutes count; commented-out checks do not.
Split by platform where the answer differs. When every case is in, the Task table and Blockers table are final for
phase 1. Go on to the blocker plan.
