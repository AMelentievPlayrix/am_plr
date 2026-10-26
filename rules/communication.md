# Communication: git, GitHub, Asana and Slack

Applies to everything written for teammates: commit messages, pull requests, Asana tasks and comments,
and Slack messages - whether or not a skill is running. Skills add task-specific details on top of this
rule and do not repeat it.
How to make commits lives in the `am:commit` skill; this rule only sets their language.

## Language

| Output | Language |
|---|---|
| Chat with the user: progress, questions, reports | English |
| Commit messages | Russian |
| Pull request title and body | Russian |
| Asana task title, description, comment | Russian |
| Slack message or thread reply | Russian |

- Keep identifiers, API, class and function names, library names, file paths and other naturally English
  terms in English inside the Russian text. Do not translate them.
- This includes programming and engineering terms that developers use in English: language concepts
  (`smart pointer`, `raw pointer`, `reference`, `template`, `lambda`), build and tooling terms (`build`,
  `snapshot dependency`, `unity build`, `lock file`), test terms (`flaky`, `baseline`, `fixture`).
  Write `smart pointer, а не raw pointer`, not `умный указатель, а не сырой`. When unsure, keep English.
- An explicit instruction from the user overrides this table.

## Style

- Plain, specific words. Say what changed or what is needed. No padding, ticket-speak or internal shorthand.
- Write for a teammate who never saw the session.
- Report honestly. If something is unverified, say so instead of implying a stronger result.
- Never invent a reason you cannot infer from the diff or the evidence. Ask instead.
- Use a plain hyphen `-` as the dash, never the em dash `—` or en dash `–`: `Frontend - падает каждую ночь`,
  `14-16.10`.

## Commits

Always commit through the `am:commit` skill (Skill tool, `skill: "am:commit"`, optionally with the paths
to commit). It owns the commit policy: splitting, message format, staging and git safety.
Do not hand-roll commits or restate that policy in other skills.

## Pull requests

- Use the `gh` CLI (no GitHub MCP is configured; prefer one if it gets added).
- Before pushing, check the change is still needed:
  `git fetch origin master && git log origin/master -S'<distinctive token from your change>' --oneline`.
  If someone already landed it, do not open the PR. Report the commit, author and date, and ask.
- Read your own history first: `git log --oneline origin/master..HEAD`. If it does not read as clear
  steps, tell the user rather than hiding it behind a tidy description.
- Title: match the tone of recent PRs (`gh pr list`).
- Body: fill in `.github/pull_request_template.md` if the repo has one; check on every run. Otherwise use:

```markdown
## Что сделано
<1-3 предложения: что PR добавляет или чинит.>

## Причина
<Для фикса: корневая причина с доказательством. Для нового: зачем и почему сейчас.>

## Изменения
<Несколько пунктов на уровне ревьюера: что добавлено, что исправлено, какие файлы затронуты.
Не список коммитов.>

## Проверка
<Как проверено: команды, платформы, результаты.>

## Ссылки
- Asana: <ссылка на задачу>

## Риски и ограничения
<Что не проверено, известная нестабильность - или «нет».>
```

- Summarise the work, not the log. Never paste `git log` into the body.
- Never merge the PR.

## Asana

- The task gid is the last numeric segment of the Asana URL.
- A **task** describes what needs to be done, as if written before the work: the goal or problem
  (`Нужно добавить валидацию X, чтобы ...`), not a changelog (`Добавлена валидация X`).
- A **PR** describes what was done. Same change, different purpose: frame the task around the goal,
  do not just flip the PR's tense.
- **Comment only.** Never close, reassign or re-status a task unless the user asks.
- Comments with formatting use `html_text`: one root `<body>`, well-formed XML, only `<strong>`, `<em>`,
  `<u>`, `<s>`, `<code>`, `<ol>`, `<ul>`, `<li>`, `<a>`, `<blockquote>`, `<pre>`; attributes only on `<a>`.
- Tool names differ by Asana MCP version: V2 uses `get_task`, `create_tasks`, `add_comment`;
  the old V1 used `asana_get_task`, `asana_create_task`, `asana_create_task_story`. Use whichever
  the session actually has.

## Slack

- The `slack` MCP signs in as the user, so every message appears **under the user's own name**. Show the
  exact text and where it goes (channel or thread link), and send only after the user approves that text.
  If the text changes after approval, ask again. A skill that already has its own approval step for the
  message counts as this approval.
- Reply where you were asked: in the given thread (`thread_ts`), not in the channel, and never with
  `reply_broadcast` unless the user asks. Never edit, delete or react to messages unless asked.
- A thread link `https://<workspace>.slack.com/archives/<channel>/p1793004591268139` gives channel
  `<channel>` and ts `1793004591.268139` (a dot before the last 6 digits). A `?thread_ts=` in the link names
  the parent thread and wins.
- Read the thread (`slack_read_thread`) before replying, so the reply fits what was asked.
- Keep it short: the result first, then the details and links. `slack_send_message` takes standard
  Markdown (`**bold**`, lists, links); keep tables and headings out of short replies.
- When the user wants to review in Slack itself, `slack_send_message_draft` puts the text in their
  Drafts without sending it.
- Tool names: `slack_read_thread`, `slack_send_message`, `slack_send_message_draft` (prefixed
  `mcp__slack__`).
