# log

Short dated log of my work for bi-weekly meetings, with period reports.

```
/am:log                              add what was done in this chat, commit, push
update am_log                        same, from any chat in any repo
/am:log info this week               report: Monday to today
/am:log info last week               report: previous Monday to Sunday
/am:log info from 01.10 to 12.10     report for any range
```

**What it does**

- Write mode reads the current chat and adds one short line per item to `am_plr/work-log/YYYY-MM.md`,
  with an optional `hard:` note on why something took long. A repeated call updates lines instead of
  duplicating them.
- If the log changed, it commits only `work-log/` through `am:commit` (English message,
  `Update work log for <date>`) and pushes. Other uncommitted changes in am_plr are left alone. On a
  rejected push it retries once with `pull --rebase --autostash`; it never force-pushes.
- Report mode counts items per category (blockers per area), lists notable items and the hard parts, in
  Russian, under about 15 lines.

**Storage**

One Markdown file per month: easy to read and fix by hand, small diffs per commit, and a date range maps
to one or two files. Each day is a `## YYYY-MM-DD` heading; each item is one line:

```
- <category>[/<area>] [×N]: <кратко> — <refs>
  - hard: <почему было долго>
```

Categories: `autotest-new`, `autotest-fix`, `blocker-found/<area>`, `blocker-fixed/<area>`, `perf`,
`other`. To add one, add a row to the categories table in [SKILL.md](SKILL.md); old entries stay valid.

Instructions for Claude: [SKILL.md](SKILL.md).
