# Gotchas

Each one cost a real batch time (Marketing / Pre-ToS, 2026-10/11, unless noted). Briefs point subagents here.

## Tools

**Asana MCP**
- Calls time out after 300 s and writes often succeed anyway. After any write that reported an error or timeout,
  read the task's stories (or the task) before retrying. A blind retry posted a duplicate comment.
- The MCP needs re-authorisation every day or two. Record the pending writes in `resume.md` § Live state, tell the
  user under **Needs you**, and keep working on everything else. Post the writes when the MCP is back.
- `html_notes` and `html_text` allow no `<p>` ("XML is invalid"). Use only the tags listed in `rules/communication.md`.
- The V1 MCP cannot remove a dependency (`set_task_dependencies` only appends). Ask the user to remove it in the UI,
  then read it back. Use the V2 tools when the session has them.

**GitHub**
- SSH sometimes fails with `Permission denied (publickey)`. Fetch and push over HTTPS:
  `git push https://github.com/Playrix/<repo>.git <branch>`.
- `gh pr merge` once returned 502, and the retry created an empty duplicate squash commit. After any error, read
  `gh pr view <n> --json state,mergeCommit` before retrying.
- `gh` GraphQL errors ("Something went wrong") are transient. Re-read, then retry once.

**Qase**
- The Qase MCP is read-only. Writes (the automation field, steps) go through
  [../scripts/qase_case.py](../scripts/qase_case.py), which reads the token in-process and reads every write back.
  Never `curl` with the token in a shell.

**Subagents and waiting**
- At most 20 subagents run at once. Launch analysis in waves.
- Foreground `sleep` is blocked. Wait on a condition with Monitor (an `until` loop) or `run_in_background`.
- macOS has no `timeout`/`gtimeout`. Use the tool's own timeout parameter, or `run_in_background` plus Monitor.

## Permission refusals

The auto-mode classifier refused these. Never work around a refusal with another tool or another spelling.
Record the exact command under **Needs you** in `status.md`, then go on with the work that does not depend on it.

| Refused as | Action |
|---|---|
| [Git Destructive] | `git push --force*`. The process avoids it: no stacked branches |
| [Merge Without Review] | `gh pr merge`, unless the user added an allow rule (asked at approval 2) |
| [Unrequested Commit in a Connected App] | `gh pr edit` / `gh pr ready` from a subagent. Do these from the orchestrator |
| [Credential Materialization] | reading `.env` or tokens. Use `run_on_platform.py` / `qase_case.py` |

## Environment

- **TestSDK builds** come from TeamCity build types, downloaded over REST (`https://teamcity.local.playrix.com`,
  `$TEAMCITY_TOKEN`) or with the `teamcity` MCP:
  - `PerfectProject_TestSDK_IOS_Production` gives the ipa;
  - `PerfectProject_TestSDK_Android` gives `app-google-release.apk`;
  - `PerfectProject_TestSDK_Mac_Sign` gives `Engine-Example.pkg` (expand with `pkgutil --expand-full`);
  - the UWP build type is `PerfectProject_TestSDK_Uwp`.

  Put the builds in vso-engine-autotests `artifacts/app/` and record the build numbers in `facts.md`.
  `TestApplication.app` (`PerfectProject_Mac_MacOSArm64`) is the editor test app, **not** the TestSDK.
- **`.env`**: never edit or print it. Run through `engine-create-autotest/scripts/run_on_platform.py`, as
  described in delivery.md § Validation. In a worktree, a shared venv's `load_dotenv()` finds the main checkout's
  `.env` first; the script with `--env-file` handles that.
- **Killed macOS run**: the Wi-Fi proxy stays at `127.0.0.1:8082`, and BrowserStack Local then fails with "SSL
  inspection". Fix it with `networksetup -setwebproxystate Wi-Fi off; networksetup -setsecurewebproxystate Wi-Fi off`
  (check with `networksetup -getwebproxy Wi-Fi`). Prefer letting runs finish.
- **Relay server restarts** (WebSocket close 1012, SSL error on relay auth) cause BrowserStack reruns. The in-session
  auto-retry absorbs them. They are infrastructure, not a test failure, and do not use the run budget.
- **Device-specific SDK failures**: Unity Ads init failed server-side on BrowserStack device 101 (Galaxy S22 Ultra)
  and passed on 110 (Pixel 9 Pro XL). Before suspecting a product defect, rerun on a second device. Record both
  devices, and pin the working one in the test's notes and the PR.
- `platform_to_run` is case-sensitive (`iOS`, `Android`, `macOS`, `UWP`). A lowercase value deselects every test.
- perfect-project git hooks need the VPN (`./vpython` fetches from nexus). Offline: run
  `uv sync --offline --frozen` once in the worktree (then revert `uv.lock`), and prefix git with
  `UV_FROZEN=1 UV_OFFLINE=1`. Never `--no-verify`.

## Test state

- On macOS, GlobalVars and SDK settings persist across tests and launches. Launch completion from one test made
  `launch_start` drop in the next, and the reset step had to destroy and wipe the tracker, not just restart.
  Shared reset steps clear what the tests rely on: authoring-rules.md § State between tests.
- A "diff" payload (e.g. Pre-ToS `update_tracking`) depends on the previous state. Reset the baseline first.
- One-shot events (first install, first open, uninstall) cannot be reproduced by the in-session auto-retry
  (`tests/conftest_auto_retry.py`). A retry that passes after a failure proves nothing.
- Every "not sent / absent" check needs one uncommitted positive-control run, in which the thing is present and the
  check fails. Revert the control afterwards.
