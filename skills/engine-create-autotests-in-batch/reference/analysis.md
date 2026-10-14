# Phase 1: survey, analysis brief, cross-checks, verdicts

## Repo survey

Do this once, before you launch the subagents, so that every brief starts from the same verified facts. It is
read-only: use `git fetch origin master`, `git show origin/master:<path>`, `git grep <pattern> origin/master`
and `git ls-tree`. Do not switch branches. Record the base commit, and whether the tree is clean, in the memory
file header.

Check, on `origin/master`, and record each result with its path in "Known repo facts":

- **SDK under test.** Its RPC client in `framework/services/app_api/sdk/`, its widget steps in
  `framework/test_management/test_steps/app_widget/<sdk>/`, and any SDK-level steps or services
  (`test_steps/<sdk>/`, `framework/services/<sdk>/`). Note each step's platform decorators.
- **Existing tests** for this SDK, and the closest neighbours for another SDK, with how they verify things
  (backend API, database, device log, network log).
- **Verification channels:**
  - device logs: `BSController.get_device_logs` and `DeviceSteps.cut_logs` / `check_log_pattern_matches`;
  - BrowserStack HAR network logs: `check_substring_entries_in_network_logs`;
  - the local proxy: `framework/services/proxy`, `ServiceManager.proxy` (check on which platforms it works);
  - backend or database clients for the SDK.
- **Session setup:** `framework/services/browserstack/browserstack_init.yml` and `utils.update_bs_config`
  (capabilities, region via `BS_CUSTOM_COUNTRY`), the driver fixture scope (`tests/conftest_browserstack.py`),
  and in-session auto-retry (`tests/conftest_auto_retry.py`).
- **Tags** in `framework/test_management/enums/common/tags.py`: is there a tag for this SDK?
- **Earlier research**, if any, in vso-engine-autotests `artifacts/` (ignored by git, so it exists only locally).

Then write the **SDK-specific hints** for the brief: the paths above, plus anything already known from earlier
batches or the blocker tasks, phrased as claims to verify.

## Brief

One brief per case. Fill in the `{...}` slots. Launch every case's subagent at the same time
(`run_in_background: true`), using the general-purpose agent type.

```text
You are doing a READ-ONLY feasibility analysis of ONE Qase test case for automation in the repo
/Users/playrix/projects/vso-engine-autotests (Python, pytest, CATS2 framework). Nobody will answer questions:
never use AskUserQuestion. Do NOT write code, create branches, commit, edit any file (including the batch memory
file), post to Asana/GitHub, or run tests on devices. Read origin/master (git show / git grep); do not switch
branches.

## The question
Can this case be automated by changing ONLY vso-engine-autotests (new steps, services, utils, schemas, API
clients, BrowserStack/Appium capabilities, network logs, etc.), WITHOUT changes to the product or TestSDK code
(/Users/playrix/projects/perfect-project, read-only for you) and without manual steps?

## Inputs
- Qase case VSO-{CASE_ID}: read it fully with mcp__qase__get_test_case_data(project_code="VSO",
  test_case_id={CASE_ID}): description, preconditions, every step and expected result, params, tags, platforms.
  The Qase case is the source of truth.
- Asana subtask: {ASANA_LINK}
- Blocker (Asana dependency): {BLOCKER_LINK_AND_NAME or "none"}. Its text: {BLOCKER_SUMMARY}
- Asana MCP calls may time out: retry once, then go on with the inputs above and say so in your report.
- Authoring rules the eventual test must follow (read them to judge feasibility):
  /Users/playrix/projects/am_plr/skills/engine-create-autotest/reference/authoring-rules.md

## Known facts (verify, don't trust blindly)
{KNOWN_REPO_FACTS: the survey results, with paths}

## SDK-specific hints (verify, don't trust blindly)
{SDK_HINTS: product entry points to search, verification channels to assess, region/capability questions,
lessons from earlier batches that apply}

## Traps from earlier batches
- A "not sent / not logged / absent" expectation needs a positive control: say how a run would prove the
  check can see the thing when it IS there.
- One-shot events (first install, first open, uninstall) cannot be reproduced by the in-session auto-retry
  (tests/conftest_auto_retry.py); say if the case needs an opt-out or a fresh install.
- BrowserStack capabilities and region apply to the whole run, not to one test.
- Fixed sleeps are forbidden; name the observable condition a wait would use, or say there is none.
- Check that a substitute channel really carries the data on the target platform (e.g. which log levels
  reach the device log), and give evidence. Mark anything not proven as "to prove on first run".

## What to deliver (your final message is the only thing the orchestrator sees)
Return exactly this structure, in English, concise but complete:

### VSO-{CASE_ID}: <title>
- Platforms (from Qase):
- Steps: numbered; each step -> what must be verified -> HOW it would be verified in automation
  (existing step/API with file path, or "NEW: <what>").
- Blocker assessment (if a blocker exists): is the blocker's stated need real for this case? Can it be solved
  only in vso-engine-autotests? How, concretely? What, if anything, still needs the product/TestSDK side?
- Hidden blockers (also for cases without an Asana blocker): missing RPC, unreachable UI, region, capability,
  data visible only in a console with no API, etc.
- Verdict: one of
  - AUTOMATABLE (autotests-only)
  - AUTOMATABLE WITH CAVEATS (autotests-only, but part of an expected result is checked through a substitute;
    say which part and which substitute)
  - NOT AUTOMATABLE WITHOUT PRODUCT CHANGES (say which change)
  - NOT AUTOMATABLE (manual by nature; say why)
- Needed changes in vso-engine-autotests: bullets (steps/services/utils/schemas/capabilities/tags), each S/M/L.
  Mark the ones other cases are likely to need too.
- Risks / unverified assumptions: what a first device run must prove.
- Evidence: file paths with line numbers (say whether origin/master or another ref), Qase quotes, product code
  references with the perfect-project commit you read.
```

## Cross-checking

The orchestrator does this while the reports arrive, not after all of them are in.

- **Contradictions.** If two reports disagree on a fact, read the source yourself and settle it. Record a
  `RESOLVED:` entry with file:line and the commit you read, then fix the verdicts that depended on it.
  Example: two agents disagreed on whether an RPC accepts enum flag combinations; the validator showed that only
  exact item names pass, which turned one case into "not automatable without product change".
- **Claims that change other cases** (a capability is impossible, a channel does or does not carry the data, an
  RPC is missing). Verify them before you apply them to other rows.
- **Later evidence can overturn earlier assumptions.** Example: real CI data showed that iOS syslog on
  BrowserStack has no Debug/Info lines, and that BrowserStack HAR keeps decrypted bodies. Several earlier
  verdicts changed. Write a `CORRECTS:` entry, revise each affected row and section, and list the changes as
  a batch event.
- **Inconsistent expectations across cases** (e.g. two cases expect different values for the same field):
  check the product, then record the inconsistency as an open question for the user.
- **Missing reports.** If a subagent fails or returns an incomplete report, relaunch it once, with the gap named.

## Verdicts and the status view

When every case is in, bring both status tables ([memory-file.md](memory-file.md) § Task table, § Blockers) up
to date: every case row has its verdict and blocker ids, every blocker (Asana or found) has a row.

Define "fully" explicitly, in the line above the Task table: **every expected result has an automated check.** Named substitutes
count (e.g. a device-log line instead of a console view that has no API). Checks that are commented out do not.

| Group | Meaning |
|---|---|
| Fully automatable (autotests-only) | Every expected result checked, with substitutes named |
| Partly automatable | Implementable, but some expected result has no check. Say which one and why |
| Not automatable without product change | Name the change and who would own it |
| Manual by nature | Say why |

Put the group into the case's Status and Comment, split by platform where the answer differs (e.g. blockers
`— (Android); D (iOS)`). Each Asana blocker gets a row in § Blockers saying whether it is real and whether the
tests side can solve it; an unreal one goes under the table as "Not a real blocker". The shared autotests work
and the open questions go into § Plan. State the honest status in the Task table header line, e.g. "nothing has
run on a device yet".
