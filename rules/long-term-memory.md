# Long-term memory

For work that outlives one context: a small folder of Markdown files that a later session (or the same one after
compaction) resumes from. Short by design, so loading it never floods the context.

## When to propose it

Propose a folder when any of these holds:

- the work is multi-day, spans several PRs or tasks, or will likely outlive the context;
- a skill says to use long-term memory (e.g. `engine-create-autotests-in-batch`);
- the user asks for long-term memory in chat.

Short, single-session work needs none. Claude auto-memory (one fact per file) stays for isolated facts.

## Ask first

Never create or reuse a folder without the user's answer. Ask with AskUserQuestion:

- **New:** `<am_plr>/artifacts/memory/YYYY-MM-DD_<slug>/`: today's date and a 1-3 word kebab-case slug.
- **Reuse:** a matching `active` folder from `<am_plr>/artifacts/memory/INDEX.md`, when the work continues it.

`<am_plr>` is the parent of the target of `~/.claude/rules/am_plr` (`readlink`; on Windows the junction target).
`artifacts/` is git-ignored: the folder is local to this machine and never committed (am_plr is a public repo).

## Files and limits

| File | Reader | Limit | Content |
|---|---|---|---|
| `status.md` | the user | 40 lines | Where we are, **Needs you**, Left, Done, key links. One screen. |
| `resume.md` | the agent | 60 lines | Entry point: read order, current phase and next action, live state (branches, worktrees, cron ids, running agents, pending writes), how to continue. |
| `events.md` | the agent | append-only | `- YYYY-MM-DD HH:MM: <fact>`, one line each: decisions, approvals (quoted), results, mistakes. |
| `facts.md` | the agent | 150 lines | Verified facts and gotchas the work depends on, each with its evidence (file:line, link). |

- A skill may add files (tables, per-item logs, hand-offs) and must say what each holds. These four always exist.
- Lines stay under about 160 characters. Links are short (`[#407](url)`), never pasted logs.
- Over a limit: fold. A superseded fact leaves facts.md as a one-line event; status.md keeps only open items and
  counts.

`INDEX.md` has one line per folder: `- [YYYY-MM-DD_<slug>](YYYY-MM-DD_<slug>/status.md) - <goal> - active | done
YYYY-MM-DD`. Add the line when a folder is created; mark it done when the work ends.

## Resume with the minimum

- When a folder is created, add one Claude auto-memory pointer (a project memory plus its `MEMORY.md` line) naming
  the folder's `resume.md`. Pointer only, never content. Mark it done, or delete it, when the work ends.
- To resume: read `resume.md`, then `status.md`, then `tail -40 events.md`. Read other files only when the current
  step needs them.
- If the repo, GitHub or Asana disagree with the memory, trust them, fix the memory and log the correction.

## Write discipline

- Write first, then reply: a fact that exists only in the chat is lost at the next compaction.
- Update `status.md` on every phase change and whenever **Needs you** changes, not on every event.
- Facts, not intentions: "Run Android 2/5 FAILED at <step>", not "will try X".
- Edit with unique anchors; never rewrite another agent's section.

## Never store

- Secrets, tokens, passwords, `.env` values or personal data. Device ids, build links and SHAs are fine.
- What is already recorded elsewhere: code and history (git), the work log (`/am:log` writes `work-log/`), rules and
  skills. Link to them instead.

## Fit with what exists

- `work-log/`: still written only by `/am:log`; memory never copies it.
- `artifacts/log/*.md` and older `artifacts/memory/*` folders: legacy, left as they are.
- Another host (e.g. a Windows machine for UWP) cannot see the folder: give it a self-contained hand-off file whose
  links are repo-relative or public (Asana, GitHub), never local paths.
