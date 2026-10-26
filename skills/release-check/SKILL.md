---
name: release-check
description: Run the release check for a PerfectProject minor version end to end - find the TeamCity builds for the Asana release subtasks ([Render], [OSnP/Resources], [GameUI], [Perf]), start them (or take builds already started), wait for them, analyse the results (functional via failed tests and logs, perf via perf-report), report in chat, and after confirmation comment on the subtasks, assign them (Anton Melentiev by default), complete them and reply in the release Slack thread. Use for "/am:release-check <X.Y.Z> both <task> <slack thread>", "run release autotests for <X.Y.Z>", "check the release, perf only", "check the release, the perf bundle is already running".
argument-hint: "<minor version> <auto|perf|both> [Asana container or subtask links] [Slack thread link] [existing build links] [assignee]"
disable-model-invocation: true
allowed-tools: Read Write Edit Bash(python3 *) Bash(*/.venv/bin/python -I *) Bash(mkdir -p /tmp/release-check-*) mcp__teamcity mcp__asana mcp__victoriametrics mcp__slack Monitor
---

# Release check

Automates the release-testing loop for one PerfectProject minor version: Asana subtasks → TeamCity builds →
start → wait → analyse → chat report → Asana and Slack. Two stops for the user: before builds start and
before anything is written to Asana or Slack. Everything else runs on its own, and anything unclear becomes
a question.

Language, style, Asana and Slack rules come from [communication.md](../../rules/communication.md):
chat in English, Asana comments and the Slack reply in Russian, plain hyphen `-` as the dash. Stop 2 (step 8)
is the approval of the Slack text that rule asks for.

## Hard rules

- **Ask instead of guessing.** A missing input, a `buildTypeId` that does not exist, an unclear branch, a
  subtask that matches no build, a person matching several Asana users: stop and ask with AskUserQuestion,
  offering the likely answers as options. Never invent a `buildTypeId`, branch, build id or user.
- **Two confirmations, always:** the build plan before any `trigger_build` (step 3), and the Asana and Slack
  writes before any comment, assignment, completion or Slack message (step 8).
- **Slack posts under the user's own name**: send exactly one reply, only in the given thread, only with the
  text the user approved. Never post to the channel itself, never edit or delete messages, never post when
  the Slack MCP is not connected.
- **Every Asana write is approved at stop 2.** Completing subtasks is offered only when every result in
  the run is good (green, or an explained non-blocking failure - step 6). When something is blocking,
  posting the comments without completing is offered instead; nothing is written without that approval.
- **Touch only the subtasks covered by this run.** Never complete the container task, never touch
  subtasks such as [Migration] or [Resave], never re-status or reassign anything else.
- **A TeamCity `FAILURE` is not a finding by itself.** Read the cause before calling it a failure (step 6).
- **Never cancel a build** unless the user asks, and never start a build for a config the user already gave
  an existing build for.
- **Never print the TeamCity token** or other secret values; refer to variables by name. `get_build`
  returns build properties that include vault references - never copy them into chat or files.

## Paths and constants

- `<am_plr>`: the grandparent of this skill's base directory. `<pp>`: `<am_plr>/../perfect-project`.
- Mapping: [config/build_mapping.json](config/build_mapping.json). Wait script: `scripts/wait_builds.py`.
- Perf analysis scripts: `PERF=<pp>/.claude/skills/perf-report/scripts` (read `<pp>/.claude/skills/perf-report/SKILL.md`
  when something there fails).
- Default assignee: **Anton Melentiev**, Asana user gid `1207120594833706`.
- Build links, everywhere (chat and Asana), in one format only:
  `https://teamcity.local.playrix.com/viewLog.html?buildId=<id>&buildTypeId=<buildTypeId>`, built from the
  build id and `buildTypeId` that TeamCity returned. Never pass on the `webUrl` that TeamCity returns
  (`teamcity.playrix.com/build/<id>` or `.../buildConfiguration/...`); the wait script already prints links in
  the right format.
- Working folder: `WORK=/tmp/release-check-<version>` - by version only, no date, because a run with perf
  often goes past midnight. Keep the state in `$WORK/state.json` (version, suite, container and subtask
  gids, build plan, build ids - triggered or taken over, verdicts, Asana and Slack writes done) and update it
  after every step. On start, if `state.json` exists: show what it holds (builds, their age, writes done) and
  ask - continue this run / start over (rename the old folder to `$WORK-<YYYYMMDD-HHMM>`, never delete it).
  Large outputs (logs, failed tests, perf files) go to `$WORK`, not into chat.

## Step 0 - inputs

Parse `$ARGUMENTS` and the message:

| Input | Expected | If missing or unclear |
|---|---|---|
| Version | minor `X.Y.Z` (e.g. `2026.2.7`); major = `X.Y` | ask; if only `X.Y` was given, ask which minor (the container name needs it) |
| Suite | `auto`, `perf` or `both` | ask |
| Tasks | container link, or subtask links | search (step 1), then confirm |
| Assignee | a name | default Anton Melentiev |
| Slack thread | `https://<workspace>.slack.com/archives/<channel>/p<ts>` | ask in step 3: a link, or no Slack reply this run |

Only the explicit user words change the assignee: "assign to Sasha", "assignee Руслан Байбеков".

| Existing builds | TeamCity build links or ids already started for this release | none: all builds get started |
Slack thread link → channel id and thread ts: `.../archives/C0CB6H4N672/p1793004591268139` → channel
`C0CB6H4N672`, ts `1793004591.268139` (insert a dot before the last 6 digits). A `?thread_ts=...` query in the
link (a link to a reply) wins: it names the parent thread. Read the thread once with
`slack_read_thread(channel_id, message_ts, response_format="concise")` to confirm it is about this release, and
ask if it is not. If no Slack tool is available, say
that the `slack` MCP is not connected (run `/mcp` and authorise it) and carry on without Slack.

## Step 1 - tasks

1. With a container link or gid: `asana_get_task` with `opt_fields=name,completed,subtasks.name,subtasks.gid,subtasks.completed,subtasks.assignee.name`.
   With subtask links: fetch each, and its `parent`.
2. Without tasks: `asana_typeahead_search` (`resource_type=task`, query `Тестирование релиза <version>`), keep
   names matching `container_name_pattern`. Exactly one hit → offer it in the step 3 confirmation. Zero or
   several → ask for the link now.
3. Match subtask names to `subtask_name_pattern` in the mapping, keep those whose `suite` is in the run
   (`both` = auto + perf). Report subtasks of the chosen suite that are missing from the container, and
   ask about any subtask with a test-like name (`[...] Запущены ...`) that matches no pattern.
4. A subtask that is already completed: ask whether to include it (rerun) or skip it.

## Step 2 - builds and branch

1. Substitute `{major}` (`2026_2`) and `{major_dotted}` (`2026.2`) into every `build_type_id` and into
   `default_branch` (`stage/v2026.2`).
2. Check each config exists and see where it runs:
   `list_builds(build_type=<id>, count=5, branch="default:any")`. **Always pass `branch="default:any"`**:
   without a branch filter TeamCity returns only default-branch builds, so a live config looks empty.
   A 404 means the config id is wrong for this release → ask for the real id, then update the mapping.
3. Branch: use `default_branch` when the recent builds of that config ran on it. If they ran on another
   release branch (e.g. `release/v2026.2`), or there are none, ask which branch to use.
4. Note the latest finished build per config (id, status, statusText): it is the baseline for step 6.

## Step 3 - confirm the plan (stop 1)

5. Existing builds from step 0: `get_build` each (only `id`, `buildTypeId`, `state`, `branchName`, `status`,
   `statusText`; never copy `properties`). Match each to a planned config by `buildTypeId`; the build then
   **replaces** the trigger for that config. A child of a composite (e.g. one benchmark of the bundle) does not
   replace the composite: ask whether to take it alone or start the composite. Ask when a build matches no
   planned config, its branch differs from the planned one, or it is cancelled.
Show the plan in chat, then ask with AskUserQuestion (options: start the new builds / change something /
cancel). Mark every config as **start** or **existing <link> (<state>)**:

```
Release check <X.Y.Z>, suite: both, branch stage/v<X.Y>
Container: Тестирование релиза <X.Y.Z> <link>
[Render]          Windows_Test_Cats_Render - start; RunScreenshotsTests - start
[OSnP/Resources]  Windows_Test_Cats_Resources - start; Windows_Test_Cats_Core - start
[GameUI]          Windows_Test_Cats_Frontend - start
[Perf]            QABenchmarkBundle (Android, iOS, iOS Metal) - existing <viewLog link> (running)
Assignee after a good result: Anton Melentiev
Slack reply (after approval): <thread link> - "<first words of the parent message>"
```

Include anything you resolved by search or default (container, branch, assignee), so the user sees it.

## Step 4 - start builds

For each planned config marked **start** (skip the ones with an existing build):
`trigger_build(build_type=<id>, branch=<branch>, comment="release-check <version>")`.
Record the returned build id and web URL in `state.json` right away. If a trigger fails, report the error
as-is and ask (retry / skip that build / stop); keep the builds that did start. Composite configs
(`RunScreenshotsTests`, `QABenchmarkBundle`) return the composite's id; the wait script lists their children.

As soon as the triggers are done, post every build of the run in chat so the user can open them, one line
each, existing ones marked:

```
Builds (branch stage/v<X.Y>):
[Render]          Windows_Test_Cats_Render - started - https://teamcity.local.playrix.com/viewLog.html?buildId=<id>&buildTypeId=PerfectProject_release_<X_Y>_Windows_Test_Cats_Render
[Perf]            QABenchmarkBundle - existing - https://teamcity.local.playrix.com/viewLog.html?buildId=<id>&buildTypeId=PerfectProject_release_<X_Y>_QABenchmarkBundle
```

Take `<id>` and `buildTypeId` from the `trigger_build` response (`id`, `build_type_id`); never guess an id.

## Step 5 - wait

Start one Monitor (`timeout_ms` 1800000, description `release-check <version> builds`) on all builds of the
run, started and existing:

```
<am_plr>/.venv/bin/python -I <skill>/scripts/wait_builds.py <id> <id> ... --interval 60
```

It prints one line per state change of each listed build: `<id> <buildTypeId> <state> branch=<branch>`, plus
`waitReason="..."` while queued, plus `SUCCESS|FAILURE "<statusText>" finishDate=<date>` when finished, then
the build link. The snapshot dependencies follow as `dep ...` lines in the same format (the children of a
composite, so you see which one failed). It ends with `ALL FINISHED`. When the Monitor expires before that,
re-arm it with the same ids: it re-prints the current state.

- Report a build when the listed build finishes: for a composite, that is when the whole bundle is done; its
  children's results come with it from the `dep` lines. Post the children's links once, the first time they
  appear.
- **Queue check.** The script also checks queued builds: a non-composite build with no compatible agent, or a
  build still queued more than 60 minutes after its snapshot dependencies finished, prints
  `ERROR queue <id> <buildTypeId>: <reason> <link>` and the script exits. Waiting for its own dependencies
  (e.g. a CATS build waiting for the game build) does not count. Report the reason and ask: keep waiting
  (re-arm with a bigger `--max-queue-minutes`) / cancel and restart that build / stop.
- Other `ERROR` lines (unknown build, TeamCity unreachable) → report and ask. The token comes from
  `TEAMCITY_TOKEN` or `<am_plr>/mcp/.env`; if the script says it is not set, tell the user to fill
  `mcp/.env` and stop.

While waiting, start the analysis of builds that already finished; do not poll with MCP calls.

## Step 6 - analyse

Give every build one verdict: **green**, **explained** (failed, but the cause is known and non-blocking, with
evidence), or **blocking** (a real problem, or a cause you could not establish).

### Functional builds (`functional_tests`)

1. `SUCCESS` → green; take the counts from `statusText` (`Tests passed: 971, ignored: 11`).
2. `FAILURE` → `get_failed_tests(build=<id>)` (save to `$WORK`), and for failures without a clear traceback
   `get_build_log(build=<id>, grep="error|traceback|assert", context_lines=5, tail_lines=400)`. A red build with
   no failed tests is an infrastructure or build problem: find it in the log.
3. For each failed test, look for evidence that it is explained:
   - it also failed in the baseline build from step 2.4 (same test, same error) - compare `get_failed_tests`;
   - the same subtask of the previous minor (`Тестирование релиза <X.Y.Z-1>`, read its comments with
     `asana_get_stories_for_task`) gave a cause for this test, and the cause still applies;
   - a known infrastructure pattern: agent or device problem in the log, BrowserStack "not supported ... will
     be ignored", reference screenshots fixed on master but not backported.
   A test that also fails in the baseline is not automatically explained: it is explained only with a
   concrete cause (test bug, known product bug already tracked, infrastructure). Write the cause and the
   evidence (build, story or task link) next to the verdict. No concrete cause → blocking.
4. Infrastructure failure of one child (e.g. a Mac screenshot agent): recommend rerunning that config and ask.

Precedents (verify the specific cause matches; never pattern-match on status alone):
- Perf Android benchmark FAILURE only because BrowserStack does not support Xiaomi Redmi Note 9: all
  `test_performance` runs passed (Asana task `1217906673515578`).
- 2026.2 screenshot tests: 2 tests failed on the release branch because their reference screenshots were
  fixed on master and never backported - judged not a release bug.
- 2026.2.6 Render VSO-8600 and Core VSO-14342: caused by backport b485a4cff6f (#18813) without its master
  follow-up #18893 - a real cause found from git history; the subtask was completed with that explanation.

### Perf build (`perf_report`)

Analyse with the perf-report scripts (VPN required); they write to files, so nothing large passes through chat.

```
PR_WORK=/tmp/perf-report-<branch with / replaced by _>-<YYYYMMDD>
python3 $PERF/fetch_metrics.py --branch <branch> --days 30 --out $PR_WORK/raw_data.json
python3 $PERF/analyze.py --in $PR_WORK/raw_data.json --out $PR_WORK/analysis.json --summary $PR_WORK/summary.md --focus <focus>
python3 $PERF/check_device_history.py --analysis $PR_WORK/analysis.json --include-device-section --out $PR_WORK/device_history.json
python3 $PERF/draft_verdicts.py --analysis $PR_WORK/analysis.json --history $PR_WORK/device_history.json --out $PR_WORK/verdicts.draft.json
```

- `<branch>`: the branch the children actually ran on (`branchName` in the wait output or `get_build`).
- `<focus>`: the UTC date(s) of the children's `finishDate` (`20261012T163418+0000` → `2026-10-12`); one day →
  `YYYY-MM-DD`, several → `FIRST..LAST`.
- A failure about VPN, branch, certificate or `--focus`: pass the message to the user as-is.
- Read only `summary.md`, `device_history.json` and `verdicts.draft.json`. Edit the draft into
  `$PR_WORK/verdicts.json` (drop repeats, re-check every `alarm`); it is a draft, never the final word.
- Map: `unit_flaky` / `farm_recurring` → farm noise (explained); `isolated` / `shared_with_branch` → not
  explained by the farm → blocking until a rerun disproves it; a device with no data (e.g. all attempts
  errored) → blocking until rerun.
- If `summary.md` recommends a `QABenchmarkBundle` rerun, or any device is blocking: ask (rerun the bundle →
  back to step 4 for that config only / accept with a reason / stop). In 2026.2.6 a rerun cleared both an
  iPhone 16 with no data and an iPhone 17 Metal deviation.
- Grafana: use the `grafana_url` values from the perf-report files. Generic dashboards: FPS
  `https://graphite.local.playrix.com/d/eekd8qvw0czr4f?from=now-14d&to=now`, benchmarks
  `https://graphite.local.playrix.com/d/fdrfo71gl1q80a?from=now-14d&to=now`. Never invent a link.
- `victoriametrics` MCP: only for a quick follow-up the scripts do not answer. Always scope selectors with
  `team="perfect-project", device_farm_type="BS"` plus `branch`, `metric` and ideally `device`/`point`; include
  `metric` in `list_label_values`' `match`; use a coarse `step`; if a response says `truncated`, narrow it.

## Step 7 - chat report

One message, overview first, nothing left out. The Asana drafts carry the details (failed tests, causes,
evidence, devices, links), so the overview does not repeat them:

1. Overall verdict in one line: **all good** (every build green or explained) or **not good: <N> blocking**.
2. One line per build: subtask, build link, status, verdict and the reason in a few words
   (`[OSnP/Resources] Core <link> - FAILURE - explained: VSO-<id>, backport without follow-up`).
3. The Russian comment drafted for each subtask (format below), in full, with the subtask link. This is the
   exact text stop 2 approves.
4. The Russian Slack reply draft (format below), with the thread link, if a thread was given.
5. Recommendations, only if there are any: reruns, references to update, bugs worth filing.

Shorter is good, losing information is not: every failed build, every blocking item and every unverified
point must appear in the overview or in a draft.

## Step 8 - confirm the Asana and Slack writes (stop 2)

- **All good**: one AskUserQuestion with two questions:
  - Asana: post, assign to <assignee> and complete / post only / do not touch Asana. Name the assignee and
    list the subtasks.
  - Slack (only if a thread was given): send the reply as shown / do not send. If the user edits the text,
    show the new version and ask again before sending.
- **Not good**: completing is not offered. One AskUserQuestion:
  - Asana: post the comments without completing (the drafts as shown, describing the blocking items) / rerun
    specific builds (back to step 4) / treat an item as explained with my reason (then re-ask this step) /
    do not touch Asana, keep the drafts.
  - Slack (only if a thread was given): send the reply as shown (the "problem found" variant) / do not send.

## Step 9 - write to Asana

1. Assignee: Anton Melentiev → gid `1207120594833706`. Anyone else → `asana_typeahead_search`
   (`resource_type=user`, the name); exactly one match → use its gid; zero or several → ask with the
   candidates as options.
2. For each subtask in the run: `asana_create_task_story(task_id, text=<comment>)`, then, only if completing
   was approved, `asana_update_task(task_id, assignee=<gid>, completed=true)`. A comment-only choice changes
   neither the assignee nor the status.
   Record each done write in `state.json`, so a retry never posts a comment twice.
3. Re-read each subtask (`asana_get_task`, `opt_fields=completed,assignee.name`) and report what changed with
   links. If a write failed, say which and why; do not retry silently.

Tool names: this session's Asana MCP may be V1 (`asana_get_task`, `asana_update_task`,
`asana_create_task_story`) or V2 (`get_task`, `update_tasks`, `add_comment`); use whichever exists.

## Step 10 - reply in Slack

Only if the user approved it in step 8. Do it after the Asana writes, so the reply can say the subtasks are
closed.

1. Send the approved text, unchanged: `slack_send_message(channel_id=<channel>, thread_ts=<ts>, message=<text>)`
   with the channel and ts from step 0. Leave `reply_broadcast` unset, so the reply stays in the thread.
2. Record it in `state.json` (`slack_reply_sent` and the returned link), so a retry never posts twice.
3. Report the message link the tool returns. If sending fails, show the error and the text, so the user can
   paste it by hand.

If the user wants to review in Slack itself, `slack_send_message_draft` with the same channel and ts puts the
reply in their Drafts instead of sending it.

## Slack reply format (Russian)

One or two short sentences: the result and where the details are. The details live in the Asana comments,
so the reply does not repeat builds, tests or devices; it links the task (the subtask, or the container when
the reply covers several subtasks). These illustrate the length and tone, they are not templates:

```
Авто и перф тесты - всё ок, комментарии в задачах, задачи закрыл: <container link>
```

```
Perf OK, комментарии в задаче, задачу закрыл: <subtask link>
```

```
CATS - есть падение в Render, похоже на продуктовую проблему, разбираю. Подробности в задаче: <subtask link>
```

## Comment format (Russian)

Short plain sentences a teammate reads at a glance; a link to every build; one comment per subtask. These
illustrate the style, they are not templates to copy word for word:

```
Render - прогон зелёный, падений нет: passed 827, ignored 56.
https://teamcity.local.playrix.com/viewLog.html?buildId=<id>&buildTypeId=PerfectProject_release_2026_2_Windows_Test_Cats_Render
Скриншотные тесты - всё ок: https://teamcity.local.playrix.com/viewLog.html?buildId=<id>&buildTypeId=PerfectProject_release_2026_2_RunScreenshotsTests
```

```
Core: https://teamcity.local.playrix.com/viewLog.html?buildId=<id>&buildTypeId=PerfectProject_release_2026_2_Windows_Test_Cats_Core
Упал VSO-14342 (https://app.qase.io/case/VSO-14342). Причина: <конкретная причина и доказательство - коммит, задача, прошлый релиз>. Не блокер для релиза.
Resources - всё ок: https://teamcity.local.playrix.com/viewLog.html?buildId=<id>&buildTypeId=PerfectProject_release_2026_2_Windows_Test_Cats_Resources
```

```
Итоги перф-тестов (BrowserStack), ветка stage/v2026.2, сборки <id> (Android), <id> (iOS), <id> (iOS Metal)
https://teamcity.local.playrix.com/viewLog.html?buildId=<bundle id>&buildTypeId=PerfectProject_release_2026_2_QABenchmarkBundle
https://graphite.local.playrix.com/d/eekd8qvw0czr4f?from=now-14d&to=now

1. Xiaomi Redmi Note 9 - ферма его не поддерживает, девайс пропущен. Из-за этого сборка Android красная, сами тесты прошли.
2. iPad Air 5, SM_S931B - скачки FPS. Такое на этих моделях уже было много раз за 90 дней на других ветках - глюк фермы.

Вывод: реальных регрессий перфа не найдено, все отклонения объясняются нестабильностью девайсов фермы BrowserStack.
```

## Before finishing

Check: every planned build was started or taken over and finished (or the user chose to skip it); every verdict has a
reason; Asana and Slack were written only after stop 2, Asana only for subtasks in this run, Slack only as one
reply in the given thread with the approved text; the final message lists what was written, with links. Say plainly what was not done or not verified.
