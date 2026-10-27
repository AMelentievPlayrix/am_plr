---
name: update-perf-devices
description: Keep the BrowserStack device matrix of PerfectProject's nightly perf runs healthy - find the devices that turn the QABenchmarkBundle runs red, classify why (device gone or broken vs test/capability problem), pick the best replacement, report in chat, and after approval create the Asana task and a draft PR from a worktree. After the PRs merge, record the change as a dated comment on the device-inventory task "Устройства" and rewrite its description. Use for "/am:update-perf-devices investigate both", "which BS devices make the perf runs red", "the replacement PRs merged, update the inventory", "sync the device inventory".
argument-hint: "investigate [master|stage/vX.Y|both] | follow-up | sync-inventory"
disable-model-invocation: true
allowed-tools: Read Write Edit Skill AskUserQuestion Bash(git *) Bash(gh pr *) Bash(gh label list *) Bash(ls *) Bash(grep *) Bash(diff *) Bash(mktemp -d -t update-perf-devices) Bash(mv */mcp_servers/teamcity/artifacts/* *) Bash(rmdir */mcp_servers/teamcity/artifacts/*) Bash(rm -rf */update-perf-devices.*) Bash(*/.venv/bin/python -I *) Bash(env PLATFORM=* */.venv/bin/python -I *) mcp__teamcity mcp__asana mcp__victoriametrics
---

# Update perf devices

BrowserStack withdraws or breaks devices without warning. The nightly perf runs then go red, the device's
metrics stop, and Grafana fires false perf alerts. This skill runs the same investigation every time and
stops twice: **stop 1** before anything is created in Asana or GitHub, **stop 2** before the inventory task
is touched. Everything else runs on its own; anything unclear becomes a question (AskUserQuestion).

Language and style come from [communication.md](../../rules/communication.md): chat in English; Asana
texts, commit messages and the PR in Russian; plain hyphen `-` as the dash. Commits only through `am:commit`.
IDs, paths, patterns and templates used below are in [Reference](#reference) at the end.

## Hard rules

- **Nothing is published before its stop.** No Asana task, branch push or PR before stop 1 is approved; no
  comment or description change on the inventory task before stop 2 is approved. Show the exact text first;
  if it changes after approval, ask again.
- **A replacement must be run, not only looked up.** A device present in `devices.json` can still fail to
  open a session (October 2026: the first iPhone 11 fix passed `devices.json` and failed on the farm). The
  PR stays draft until a manual TeamCity run on its branch shows the new device with metrics.
- **Never trigger, cancel or rerun a build without asking.** Never merge a PR, never add `automerge` or other
  merge labels unless the user asks.
- **Inventory task 1210351684187304**: comment and description only, after its PRs merged. Never re-open,
  re-status, reassign it or touch its dependencies (the TeamCity bot manages those).
- **Secrets.** BrowserStack credentials only from `BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY` in the
  environment; never print them, never put them on a command line. If they are missing, say so and use the
  public list, marking every result "not verified via devices.json". Batch logs hold the accessKey in plain
  text: handle artifacts only as in [Artifacts](#artifacts), quote only `scan_batch_logs.py` output.
- **Never touch the user's main checkout** of perfect-project: changes go to a worktree.
- **A red build is not a device verdict.** Every verdict names its evidence: build link plus a log quote.

## Investigate

Branches: `master`, `stage/vX.Y`, or `both` (default) = master plus every stage whose
`<tcs>/release_X_Y/CurrentSettings.kt` does not set `browserStackEnabled = false` (2026.1 is off).
Work folder `$T`: run `mktemp -d -t update-perf-devices` once and write the printed path literally into
every later command (shell variables do not persist between Bash calls); delete it at the end
(`rm -rf <that path>`). The same applies in follow-up and sync-inventory.

### a. Collect

1. **Builds.** For each branch and each of the three configs: `list_builds(build_type=<id>,
   branch=<branch>, count=5)`. Stage configs need `branch="stage/vX.Y"` (without it TeamCity shows old
   `release/vX.Y` builds). Keep id, status, `statusText`, finishDate.
2. **Every reason a build is red**, per red build: per-device counts from `statusText`
   (`iPhone 11:OK:0:ER:4`); `get_failed_tests` (`CapabilitiesCheck`, `test_performance[<device>]`);
   `get_build_log(grep="success_runs|add error:|NOT SUPPORTED|timed out after", tail_lines=300)`. For every
   device with errors, scan the newest red build of that config with `scan_batch_logs.py` (Artifacts).
3. **Metrics** per branch, platform and device: the VictoriaMetrics query in the Reference (3-day window;
   longer lookbacks drop the connection). Ignore `HealthCheck`. A YAML device with no series has no data.
4. **Inventory task**: `asana_get_task(1210351684187304, opt_fields=html_notes)` for the current matrix and
   the YAML → metric name mapping; `asana_get_stories_for_task` (keep `comment_added`) for past replacements
   and devices removed as unstable.
5. **YAML and farm**: `git -C <pp> fetch origin master stage/vX.Y`, then
   `check_devices.py check --ref origin/master --ref origin/stage/vX.Y`.
6. **Work in flight**: device PRs already open (`gh pr list --state open --search "BrowserStack in:title"
   --json number,title,headRefName,files`, keep those touching `ci/bs_performance/`), so a problem already
   being fixed is reported as such, not fixed twice.

### b. Classify

Match each failing device against [Failure patterns](#failure-patterns). Sort into:
- **device gone or broken** → replace;
- **test or capability problem** (rotation, capabilities, Appium version) → fix the test code, keep the device;
- **side effect** of another device (batch timeout after "All done!") → no separate problem;
- **farm noise**: failed once, green the next night with metrics → no action, mention it;
- **watch**: works and has metrics but is missing from the public list → no action now, list it;
- **unknown** → report with the evidence and ask; never guess a cause.

A device is replaced only when it fails on at least two of the last runs, or `CapabilitiesCheck` rejects it.
A problem only on stage that master already fixed needs the master PR backported ([Backport](#backport)),
not a new PR.

### c. Candidates

For each device to replace: `check_devices.py list <android|ios>`, then filter per
[Choosing a candidate](#choosing-a-candidate). Check the best two or three with
`check_devices.py check --device <platform> "<name>" <os>`. Rank them; say what each costs (OS coverage,
SoC/GPU class, form factor, a new Grafana series - history does not carry over). SoC/GPU facts come from
your own knowledge: say so.

For stage, simulate the backport now ([Backport](#backport)), so stop 1 can say which PRs stage needs.

### d. Stop 1 - report and approve

One chat message in English:
1. Per branch and config: the builds (viewLog links), red or green, and why, one line each.
2. Per problem: device, class, evidence (build link + quote from the log or scanner), recommended fix, one or
   two alternatives with their cost, and what is **unverified** (no credentials, no test run yet).
3. Watch items and farm noise, briefly.
4. Exactly what will be created: the Russian Asana task (title + full text, template in the Reference),
   branch `fix/bs-perf-<slug>`, worktree `<wt>/bs_<slug>`, the Russian PR title, labels (version label only,
   e.g. `2026.3`; the backport label comes later), and the backport plan with the merge-tree result.

Then AskUserQuestion: create as shown / change something / stop. One task and one PR per problem, as in
October 2026, unless the user wants them joined.

### e. Ship (after stop 1)

1. **Asana task**: `asana_create_task(name, html_notes, project_id=1212459666284359,
   section_id=1218577784372943, assignee=1207120594833706)` unless the user named someone else.
2. **Worktree**: `git -C <pp> fetch origin master`, then
   `git -C <pp> worktree add -b fix/bs-perf-<slug> <wt>/bs_<slug> origin/master`. If the path or branch
   exists, ask; never reuse or delete someone's worktree silently.
3. **Change**: edit the YAML in place (replace the device's two lines, keep the order and format), or the
   test code for a capability problem. Re-run `check_devices.py check --repo <wt>/bs_<slug> --ref HEAD`.
   With credentials also run the real check ([Verify](#verify-with-check_platforms_compatibility)).
4. **Commit** through `am:commit` (Skill, `skill: "am:commit"`, args: the changed paths in the worktree).
   The pre-commit hook leaves `uv.lock` modified and `*.egg-info` untracked: never commit them; afterwards
   `git -C <wt>/bs_<slug> restore uv.lock`.
5. **Still needed?** `git -C <pp> fetch origin master && git -C <pp> log origin/master -S'<new deviceName>'
   --oneline -- ci/bs_performance`, plus the open PRs from step a.6. If someone landed or opened it, stop
   and report the commit or PR, author and date.
6. **Push and PR**: `git -C <wt>/bs_<slug> push -u origin fix/bs-perf-<slug>`;
   `gh pr create --repo Playrix/perfect-project --draft --base master --head fix/bs-perf-<slug>
   --title "<title>" --body-file "$T/pr_body.md"`, body per [PR body](#pr-body). Add the version label from stop 1 (`gh pr edit <n> --add-label 2026.3`).
7. **Report**: task and PR links, and the manual run needed for verification: config id and branch
   `fix/bs-perf-<slug>`. Ask whether to trigger it; only on yes `trigger_build(build_type, branch,
   comment="update-perf-devices <slug>")`. The PR leaves draft only after that run shows the new device.
8. Clean up per [Artifacts](#artifacts). Remind the user to run `follow-up` after the merge.

## Follow-up

1. **Find device PRs.** Read the inventory comments (`asana_get_stories_for_task`, `comment_added`); the
   newest one starting with a date is the cutoff. Merged since then:
   `git -C <pp> log origin/master --since=<cutoff> --format='%h %ad %s' --date=short --
   ci/bs_performance/configurations ci/bs_performance/tools` (the PR number is the `(#<n>)` in the subject).
   Open ones: step a.6 of Investigate. Backports: `gh pr list --state all --head
   mergify/bp/stage/vX.Y/pr-<n> --json number,state,mergedAt`. For each PR:
   `gh pr view <n> --json state,mergedAt,labels,isDraft`.
2. **Not yet recorded** = a PR merged after the cutoff whose number (`#<n>` or `/pull/<n>`) appears in no
   inventory comment. None → report the PR states (open, draft, waiting for backport) and stop.
3. **Metrics** for the new devices: the Reference query on `master` (and stage if backported). The new
   series is the device name that is not in the mapping; if several are new, ask which is which.
4. **Stop 2** - one message, then one AskUserQuestion (post both as shown / change / not now):
   1. the dated Russian comment, one per merge date, oldest first ([Inventory comment](#inventory-comment));
   2. the new description ([Inventory description](#inventory-description)), as `diff -u` of the current
      and new text (write both to `$T`), with the new device's metric name or "метрик пока нет";
   3. backport steps: whether stage needs it ([Backport](#backport)), the merge-tree result including earlier
      PRs that never reached stage, and the exact label to add. Adding the label is a separate yes/no.
5. **After approval**: `asana_create_task_story(1210351684187304, html_text=<comment>)` per comment, then
   `asana_update_task(1210351684187304, html_notes=<description>)`. Re-read the task and report. Add a
   backport label only if approved (`gh pr edit <n> --add-label <label>`).

## Sync-inventory

For a drifted description, without any replacement: steps a.3-a.5 of Investigate, build the description per
the Reference from `origin/master` and `origin/stage/vX.Y` YAML plus metrics, show `diff -u` against the
current one, AskUserQuestion, then `asana_update_task(html_notes=...)`. No comment: nothing was replaced.
A device whose metric name you cannot establish: ask, or write "метрик пока нет".

## Artifacts

The TeamCity MCP saves downloads inside perfect-project (`<pp>/cats2/ai/mcp_servers/teamcity/artifacts/<build>/`,
or `TEAMCITY_DOWNLOAD_DIR`). Each copy holds the BrowserStack key, so:
1. `download_artifact(build=<id>, path="test_artifacts.zip")` → take `local_path` from the response.
2. At once `mv "<local_path>" "$T/<id>.zip"` and `rmdir` the now empty `<build>` folder.
3. Read only through `<am_plr>/.venv/bin/python -I <skill>/scripts/scan_batch_logs.py "$T/<id>.zip"`
   (`--grep <regex>`, `--after <n>` for more context). It reads the zip in place and masks credentials.
   Never unzip, `cat` or `grep` the archive yourself.
4. At the end `rm -rf "$T"` and check the MCP artifacts folder holds no `<build>` folder from this run.

## Before finishing

Check: nothing was created before stop 1 and nothing written to 1210351684187304 before stop 2; every
verdict has a build link and quote; every unverified point is said plainly; no secret appears in chat,
files or Asana; `$T` and the MCP artifact copies are gone; the final message lists what was created, with
links, and what is left (manual run, merge, backport label, `follow-up`).

## Reference

### Paths and IDs

- `<am_plr>`: grandparent of this skill's base directory; `<skill>`: this skill's directory.
- Scripts: `<am_plr>/.venv/bin/python -I <skill>/scripts/check_devices.py ...` and `.../scan_batch_logs.py ...`
  (`--help` on each). Run `gh` with `--repo Playrix/perfect-project` and `git` with `-C <path>`: the
  session starts in am_plr.
- `<pp>`: `/Users/playrix/projects/perfect-project`; worktrees `<wt>`: `/Users/playrix/projects/worktrees/perfect-project`.
- `<tcs>`: `/Users/playrix/projects/teamcity-settings-pp/.teamcity` (triggers, `browserStackEnabled` per release).
- Test code `<pp>/ci/bs_performance/`: device lists `configurations/devices_ios.yml`, `devices_android.yml`;
  `check_platforms_compatibility` in `tools/browserstack/utils.py` → `is_device_supported` in
  `tools/browserstack/web_api.py`; BrowserStack config written by `BsConfig` in `tools/custom_dataclasses.py`;
  batch configs `bs_smart_batch_*.yml` written by `tools/batch_runner.py`. Farm quirks (Appium 1.22 on some
  devices, iOS cannot rotate): `<pp>/ci/bs_screenshots/README.md`.
- TeamCity configs (master): `PerfectProject_IOS_Test_Benchmark_BrowserStack`, `..._BrowserStackMetal`,
  `PerfectProject_Android_Test_Benchmark_BrowserStack`; stage: prefix `PerfectProject_release_<X>_<Y>_`.
  Links: `https://teamcity.local.playrix.com/viewLog.html?buildId=<id>&buildTypeId=<buildTypeId>`.
- Metrics: `count by (branch, platform, device) (count_over_time({team="perfect-project",
  device_farm_type="BS", metric="fps_50prc"}[3d]))`; platforms `android`, `ios`, `ios_metal`.
- Asana: new tasks → project `1212459666284359`, section WIP `1218577784372943`, assignee Anton Melentiev
  `1207120594833706`. Reference task for style: `1219580526403460`. Inventory "Устройства": `1210351684187304`
  (https://app.asana.com/1/656176460444/project/1208100193931469/task/1210351684187304).
- Public device list: https://www.browserstack.com/list-of-browsers-and-platforms/app_automate.

### Verify with check_platforms_compatibility

Only with credentials in the environment (the module raises without them). Per platform, from any directory:

```
env PLATFORM=<android|ios> ARTIFACTS_DIR="$T" <pp>/.venv/bin/python -I -c "import sys; sys.path.insert(0, '<wt>/bs_<slug>'); from ci.bs_performance.tools.browserstack.utils import check_platforms_compatibility as c; _, bad = c(); print('unsupported:', [(d.deviceName, d.osVersion) for d in bad])"
```

### Failure patterns

| Evidence | Meaning | Action |
|---|---|---|
| `CapabilitiesCheck` fails, `IS NOT SUPPORTED` / "not supported on BrowserStack" | device gone from `devices.json` | replace |
| `OS VERSION NOT SUPPORTED` in `CapabilitiesCheck` | that OS version is gone | same device, another OS, or replace |
| `BROWSERSTACK_INVALID_OS_VERSION` while `CapabilitiesCheck` says OK | `devices.json` is stale; check the public list - missing there means it is being retired | replace. The int vs float `osVersion` format is **not** the cause |
| `Unknown mobile command "pushFile"` / `"queryAppState"` | harmless: the client falls back to the legacy endpoint | read the next response |
| `push_file` → `adb ... remote fchown failed: Operation not permitted` | device unusable (no config push) | replace |
| `Unable To Rotate Device` | test/capability problem, not the device | sessions must start in landscape (`deviceOrientation`) |
| `Batch ... timed out after 1800 seconds` after the SDK printed "All done!" | side effect of another failing device | not a separate problem |
| `<device> with success_runs: 0, failure_runs: N`, `add error:` | the device failed every attempt | find the cause in the batch log |
| no `Driver created successfully: <device>` in any batch | the session never opened | look at the response after the session request |

### Choosing a candidate

- Present in both `devices.json` and the public list (public list only, marked unverified, without
  credentials). Missing from the public list alone does not condemn a working device: iPhone SE 2020 (iOS 13)
  was absent on 2026-10-27 yet produced metrics.
- Prefer the dropped device's OS version, SoC/GPU class and form factor; never a tablet for a phone. Not a
  device already in the matrix.
- Avoid devices the inventory comments record as removed for instability: iPhone XR, Huawei P30,
  Moto G71 5G (push broken) - plus any newer ones found there.
- Public names drop the Android brand (`Moto G71 5G` = YAML `Motorola Moto G71 5G`); `check_devices.py`
  adds it back.
- Known 2026-10-26: the only budget Android phones were Galaxy M32, Moto G71 5G (broken push), Huawei Nova
  11 SE. iPhone 11 is gone from the public list; iPhone 12 has iOS 14.

### Backport

Mergify backports master → `stage/vX.Y` when the PR has the master version label (`2026.3`) plus any
`2026.2.*` label (`gh label list --search 2026.2.`; offer the newest existing one - e.g. `2026.2.8` may not
exist yet, creating labels is the user's call). The label can be added after merge; Mergify then opens
`mergify/bp/stage/vX.Y/pr-<n>` (as #20308 for #19350, #20309 for #20101). Simulate before proposing, in one
Bash call per chain (variables do not persist):

```
git -C <pp> fetch origin master stage/vX.Y
BASE=origin/stage/vX.Y
# earlier device commits on master missing on stage, oldest first: compare
#   git log origin/master --format='%h %s' -- ci/bs_performance/configurations ci/bs_performance/tools
#   git log $BASE --format='%s' -- same paths   ("(#<n>)" vs "(backport #<n>)")
T1=$(git -C <pp> merge-tree --write-tree --merge-base=<sha>^ $BASE <sha>) && BASE=$(git -C <pp> commit-tree $T1 -p $BASE -m sim)
git -C <pp> merge-tree --write-tree --name-only --merge-base=<base> $BASE <tip>   # exit 0 clean, 1 conflict
```

`<sha>`: a merged PR's squash commit on master. For the PR itself: merged → `<base>`=`<sha>^`,
`<tip>`=`<sha>`; open → `<base>`=`$(git merge-base origin/master <head>)`, `<tip>`=`<head>`. In October,
#20285 conflicted on stage alone and applied cleanly after #20101 (and #19350 first).

### Asana task (Russian)

Title: `На BrowserStack недоступен <device> в perf-тестах` (or the problem in the same tone). `html_notes`,
tags only `<strong> <em> <code> <ul> <li> <a> <blockquote>`, a goal, not a changelog:

```
<body>Нужно заменить в <Android|iOS> perf-тестах на BrowserStack девайс <code><device></code> (<OS>), <причина>. Тогда <что станет лучше: прогон зелёный, метрики снова есть>.

<strong>Что происходит.</strong> <механизм: какой шаг падает и почему, с доказательством>
<blockquote><строка из лога или сканера, без секретов></blockquote>
<strong>Билды:</strong>
<ul><li>master: <a href="<viewLog>"><id></a> (DD.MM), ...</li><li>stage/vX.Y: ...</li><li>Последний зелёный: ... - что изменилось</li></ul>
<strong>Замена.</strong> <кандидат и почему; что проверено, что нет>

Конфиг: <code>ci/bs_performance/configurations/devices_<platform>.yml</code>.</body>
```

### PR body

Title like `Замена недоступного на BrowserStack <old> на <new> в performance-тестах`. Body: the sections of
`<pp>/.github/pull_request_template.md` (re-read it each run), Russian: **Что поменялось для пользователей?**
(problem and change); **Какие зависимости изменились** (`Не изменились.`); **Как исправить проблему**
(`Не ломающая.`); **Задача** (Asana link); **Технические детали** (file changed, error quote with build link,
why this device, "в Grafana появится новым рядом, история не переедет", then **Проверка:** what was checked,
what not, the manual run needed before leaving draft, and whether stage needs a backport).

### Inventory description

Rewrite from `origin/master` and `origin/stage/vX.Y` YAML plus metrics. Keep the current item order;
replace in place. `html_notes`:

```
<body>Актуальные девайсы perf-тестов на BrowserStack, master на <DD.MM.YYYY>. В скобках - техническое название (<code>device</code> в VictoriaMetrics).

<strong>Android:</strong>
<ul><li><deviceName из YAML>, <osVersion> (<metric device>)</li>...</ul>
<strong>iOS:</strong>
<ul><li>...</li></ul>
<strong>Отличия stage/v<X.Y>:</strong> <только отличия stage от master и открытые бэкпорты как <a href="https://github.com/Playrix/perfect-project/pull/N">#N</a>; если отличий нет - «нет»>

Источник списка: <code>ci/bs_performance/configurations/devices_android.yml</code> и <code>devices_ios.yml</code>. История замен - в комментариях к задаче. Описание обновляется после каждого мержа замены.</body>
```

Item variants: no metrics → `(метрик нет: <короткая причина>, замена на <device> в <a href="...">#N</a>)`;
new device without data yet → `(метрик пока нет)`; two names → `(iPad_9_Wi_Fi_Cellular или iPad_9_Wi_Fi - зависит от выданного девайса)`.

### Inventory comment

Agreed by the team on 08.07.2025: every device update is a dated comment. Date = merge date. Past comments
indent the replacements with spaces; whether `html_text` keeps leading spaces is unverified, so they go
into a list:

```
<body>DD.MM.YYYY
<a href="<PR or task link>"><PR or task link></a>

Замены:
<ul><li><old> → <new></li><li><device> c <OS> → тот же девайс с <OS></li></ul>
<одна-две строки причины: «на BS закончилась его поддержка», «по перфу оказался +- похожим»></body>
```

A non-device change in the same merge (e.g. landscape start) gets its own line after the list.

### State as of 2026-10-27

The description is current. Not yet recorded as comments (record on the first `follow-up` run, one comment
per merge date): Redmi Note 11 → Moto G71 5G (#20101, backport #20309); iPad 8th → iPad 9th and iPhone 11
iOS 13 → 14 (#20100, backport #20123); pending: iPhone 11 → iPhone 12 (#20284), Moto G71 5G → Huawei Nova 11 SE
(#20285), sessions start in landscape (#20286).
