---
name: log
description: Keep a short dated log of my work in am_plr/work-log and report on it for bi-weekly meetings. Write mode (`/am:log`, "update am_log", "log this to am_log") adds what was done in the current chat to the log, then commits and pushes it. Report mode (`/am:log info this week`, `info last week`, `info from <date> to <date>`) prints counts and notable items for that period.
argument-hint: "[info] [this week | last week | from <date> to <date>]"
allowed-tools: Bash(git -C *am_plr *) Bash(date *)
---

# Work log

Keep a short log of my work so I can say at the bi-weekly meeting "from X to Y I automated N autotests
(M counting platforms), found and fixed Z blockers for <area>, fixed M existing blockers, investigated K
perf reports", and explain what made some items slow.

- **Paths:** the skill runs from any repo (am_plr, vso-engine-autotests, perfect-project), so always use
  absolute paths. `<repo>` is the am_plr root: the grandparent of this skill's base directory (shown above
  as "Base directory for this skill"). Log folder: `<repo>/work-log/`; git: `git -C <repo>`.
- **Language:** log entries and reports in Russian; identifiers, links, names, file paths and the
  category slugs stay as they are. Commit messages for the log in English (this overrides the commit
  language in `rules/communication.md` for this skill only).

Mode by `$ARGUMENTS`:
- empty, or a plain request like "update am_log" → **write mode**;
- starts with `info`, or is just a range (`this week`, `last week`, `from … to …`) → **report mode**.

## Storage format

One Markdown file per month: `work-log/YYYY-MM.md`. Inside, one `## YYYY-MM-DD` heading per day, days in
ascending order, and one bullet per item under it:

```
# 2026-10

## 2026-10-13
- autotest-new ×3 [iOS, Android, macOS]: покупки в магазине — Qase VSO-512, VSO-513, VSO-514; PR #231
- autotest-fix [Windows]: VSO-601 стабилизирован выбор ключа — PR #232
- blocker-found/ACE: после undo не открывается key popup — https://app.asana.com/0/0/1213...
  - hard: падало только на Windows, воспроизвёл после 4 прогонов; причина в порядке событий фокуса
- blocker-fixed/ACE (C++): key popup снова открывается после undo — PR #20150
- perf: разбор алерта FPS на сцене Match3Level (iOS) — шум, не деградация
```

Line format: `- <category>[/<area>] [(C++)] [×N] [<platforms>]: <кратко, что сделано> — <refs>`
- `(C++)` marks work done in C++ code. The report counts it separately, because C++ work is harder for
  me and should show as its own entries. Mark a line `(C++)` when the change itself was in C++ (`.cpp`, `.h`,
  `.hpp`, `.mm`, `.cc`), e.g. a blocker fixed in the engine or editor, or UI IDs added in C++. Python
  work and work with no code change (perf analysis, investigation, testing) have no marker. Each item
  counts once: one line, `(C++)` or not. If one item had a separate C++ change on top of Python work (e.g.
  new UI IDs in C++ so a Python autotest could be written), log the C++ change as its own `(C++)` line in
  the matching category (usually `other`).
- `×N` only when one line covers several items of the same kind; no `×` means 1.
- `[<platforms>]`: required for `autotest-new` and `autotest-fix`, not used elsewhere. The platforms each
  test on the line was written or repaired for, comma-separated, using the `Platform` values of
  vso-engine-autotests: `iOS`, `Android`, `macOS`, `Windows`, `UWP`, `Emscripten`, `Facebook`,
  `android_on_linux`, `ios_on_linux`. Every test on one line must cover the same platforms; if they
  differ, split into lines. Platform-weighted count of a line = N × number of platforms. Old lines without
  the list count as 1 platform.
- If one test's platforms were done on separate days, it gets separate lines; put its test ID (`VSO-<n>`)
  on each so the report can count it once.
- `<area>` is required for blocker categories (ACE, ASG, PSI, Inspector, IAP, …), optional otherwise.
- `<refs>`: Asana link, PR number or URL, Qase case IDs, TeamCity build, whichever the chat has. Omit
  ` — <refs>` if there are none.
- One line per item, at most about 150 characters. No step-by-step details.
- Optional sub-bullet `  - hard: <1–2 предложения>`: why it took long.

### Categories

This list is the single source of categories. To add one, add a row here; old entries stay valid.

| Slug | Meaning |
|---|---|
| `autotest-new` | new autotests automated |
| `autotest-fix` | existing autotests repaired |
| `blocker-found` | blocker (bug blocking tests or release) found; `/area` required |
| `blocker-fixed` | existing blocker fixed or verified fixed; `/area` required |
| `perf` | perf report, benchmark or perf alert investigated |
| `other` | anything else worth mentioning (tooling outside am_plr, reviews, release testing) |

A blocker found and fixed in the same chat gets two lines: `blocker-found` and `blocker-fixed`.

## Write mode

1. **Get the date:** `date '+%F %A'`. Use today unless the chat clearly says the work was on another day.
2. **Extract work from the current chat.** List what was actually done: tests automated or repaired,
   blockers found or fixed, perf reports investigated, other notable work. Take IDs and links only from
   the chat. Count only finished work; work that is still going on goes in as `other` with
   "в процессе", or is left out if trivial.
   **Never log work on the am_plr repo itself**: it is my internal tooling. This covers its skills,
   agents, rules, MCP and workspace setup, scripts, memory and artifact files (`artifacts/…`) and the
   work log. If an item mixes am_plr work with other work, log only the other part and drop am_plr
   refs (am_plr commits, paths). If only am_plr work is left, treat it as "nothing to log".
   **Platforms of an autotest** (each platform is usually separate work: its own run, fixes and
   validation, so the platform-weighted count shows the real volume). Determine them in this order:
   - the platforms the chat shows the test was implemented and validated on;
   - otherwise read the test file in vso-engine-autotests: the platform tags in `@tag(...)`
     (`Tag.IOS`, `Tag.ANDROID`, `Tag.MAC`, …) minus platforms excluded by `skipif`/`skip`
     (e.g. `config.platform_to_run in Platform.desktop_platforms()` removes all desktop ones);
   - if the test has `Tag.ALL_PLATFORMS` and the chat doesn't say where it was validated, ask the user
     instead of counting every platform.
   **C++ or not:** mark an item `(C++)` from the files the chat shows changed (C++ sources and headers,
   usually in perfect-project). If the chat doesn't show which code was changed, ask.
3. **Hard parts.** Add a `hard:` note only when the chat shows real difficulty: long debugging, a wrong
   first approach, flaky reproduction, a blocker in another team's code, missing access or data. Say what
   was hard in 1–2 sentences. Never invent a reason.
4. **Nothing to log?** If the chat has no finished or notable work, say so, write nothing and stop.
5. **Avoid duplicates.** Read the current month file (and the previous month's if today is within the
   first week). If an entry for the same item already exists (same refs, or the same summary on the same
   day), update that line (count, refs, hard note) instead of adding a new one. This keeps repeated calls
   in one chat idempotent.
6. **Write.** Create `work-log/YYYY-MM.md` with the `# YYYY-MM` title if it is missing; create the
   `## YYYY-MM-DD` heading in date order if it is missing; append or update the lines.
7. **Show** the added or changed lines to the user.
8. **Commit and push** (only if `git -C <repo> status --porcelain -- work-log/`
   shows changes):
   - Invoke the `am:commit` skill (Skill tool, `skill: "am:commit"`) with these arguments:
     `repo <repo> (use git -C); commit only work-log/; leave every other change
     unstaged; one commit, no confirmation needed; English message: "Update work log for YYYY-MM-DD"`.
     If several days changed, name the range: `Update work log for YYYY-MM-DD..YYYY-MM-DD`.
   - Push: `git -C <repo> push`.
   - If the push is rejected because the remote is ahead, run
     `git -C <repo> pull --rebase --autostash` once (autostash because the repo
     often has unrelated uncommitted edits) and push again.
   - On any other failure, or if the retry fails, stop and report the error and the state (committed but
     not pushed, conflict, …). Never force-push, never resolve conflicts on your own.
9. **Report** in one or two lines: entries added or updated, commit hash, pushed or not.

## Report mode

1. **Resolve the range** from today's date (`date '+%F %A'`):
   - `info this week` → Monday of this week to today;
   - `info last week` → previous Monday to previous Sunday;
   - `info from <date> to <date>` → inclusive; accept `YYYY-MM-DD`, `DD.MM`, `DD.MM.YYYY`, "1 окт",
     "Oct 1"; a date without a year means the current year (the previous year if that would be in the
     future).
   - If the range can't be parsed, ask instead of guessing.
2. **Read** every `work-log/YYYY-MM.md` the range touches and keep the day sections inside it.
3. **Count** per category, summing `×N` (no `×` = 1), and split blocker counts by area. For
   `autotest-new` and `autotest-fix` also sum the platform-weighted count (N × platforms per line, 1 for
   lines without a list) and per-platform totals. A test ID (`VSO-<n>`) on several lines of the same
   category counts as one test, and each of its platforms once.
   Count `(C++)` lines apart from the rest: every count above is split into a non-C++ part and a C++
   part, and the two never overlap (5 blockers fixed, 2 of them in C++ → 3 and 2).
4. **Print** in Russian, under about 15 lines, ready to read out at the meeting. A category with C++ lines
   gets a second line, the same one with `, C++` after its name, right below it; no other wording changes:

   ```
   Период: 2026-10-06 — 2026-10-12
   Автотесты: новых 7, с учётом платформ 15; починено 3, с учётом платформ 5
     по платформам: iOS 6, Android 5, macOS 7, Windows 2
   Блокеры найдены: 2 (ACE 1, IAP 1); исправлены: 3 (ACE 2, PSI 1)
   Блокеры исправлены, C++: 2 (ACE 1, Editor 1)
   Прочее, C++: 1
   Perf-отчётов разобрано: 4
   Заметное:
   - покупки в магазине, 3 теста × 3 платформы — PR #231
   - ...
   Сложности:
   - key popup в ACE: падало только на Windows, долго воспроизводил
   ```

   Leave out categories with zero count, and C++ lines with zero count. Print "с учётом платформ" only when it differs from the plain
   count; omit the per-platform line when there are no autotest lines. Pick 3–5 notable items (biggest counts, blockers, items with
   refs). List every `hard:` note in the range, shortened to one line each.
5. Report only what is in the log. If the range has no entries, say so. Report mode never writes or
   commits.
