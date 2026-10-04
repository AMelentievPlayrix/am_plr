---
name: am-prompt-writer
description: Turn a short, rough description typed in chat into a clear, well-structured prompt using prompt-engineering best practices, ready to paste into Claude (chat, Claude Code, a subagent, a skill or a system prompt). Use when asked to "write a prompt", "improve/enhance this prompt", "make this a better prompt", or /am-prompt-writer <rough idea>.
argument-hint: "<rough description of what the prompt should make the model do>"
---

# Prompt writer

Take the user's rough description (`$ARGUMENTS`, or the message before invoking this skill) and return
one improved prompt they can copy as-is. You write the prompt; you do **not** carry out the task it describes.

## 1. Understand the request

Work out these from the description and the conversation. Infer what you reasonably can:

| Question | Why it matters |
|---|---|
| What should the model produce? (code change, analysis, document, decision, list…) | Sets the deliverable and success criteria |
| Who reads the result, and where does it go? | Sets tone, length and format |
| Where will the prompt run? (chat, Claude Code in a repo, subagent, skill, API system prompt) | Decides which context and tools the prompt can assume |
| What context does the model need that it can't guess? (repo, files, domain facts, constraints) | Missing context is the main reason prompts fail |
| What does "done" look like, and what must be avoided? | Gives the model a way to check its own work |

Ask the user only when a gap would change the prompt substantially and you can't infer it. Then ask at
most 3 short, concrete questions in one message (with AskUserQuestion when available), offering likely
answers as options. Otherwise write the prompt directly and list your assumptions afterwards.

## 2. Write the prompt

Apply these practices. Use only the ones that help this prompt; a short task gets a short prompt.

- **Lead with the task.** State in the first sentence or two what the model must do and what it must
  deliver. Background comes after.
- **Explain why.** Give the purpose and the reason behind each constraint. A model generalises better
  from a reason ("the output is pasted into Slack, so no tables") than from a bare rule ("no tables").
- **Give the context it can't guess**: the audience, domain facts, names of files, systems or people,
  and what was already tried. Leave out things the model already knows.
- **Be specific and positive.** Say what to do rather than only what not to do. Replace vague words
  ("good", "detailed", "clean") with observable criteria ("under 200 words", "each step has a command").
- **Say what done looks like.** Spell out the success criteria, and ask the model to check its output
  against them before it answers.
- **Separate parts with XML tags** when the prompt mixes instructions with material
  (`<context>`, `<code>`, `<document>`, `<examples>`, `<output_format>`). Refer to the tags by name.
  Put long material before the instructions that use it.
- **Use examples** when format or style is hard to describe. Use 1–3 varied examples in `<example>` tags,
  and say they illustrate the pattern rather than being templates to copy.
- **Specify the output**: format, length, sections, language, and what to leave out (e.g. "no preamble").
  Make the prompt's own formatting match the output you want: prose prompts get prose answers.
- **Ask for reasoning when the task is complex** (analysis, debugging, trade-offs): "think it through
  first, then answer". For simple tasks, skip it.
- **Allow uncertainty**: tell the model to say when it doesn't know or lacks information, and to ask
  rather than guess, if that fits the task.
- **For agentic or coding prompts** (Claude Code, subagents): name the repo, files and commands; give the
  scope ("only change X", "don't refactor"); say how to verify (tests, build, run); and say what needs
  confirmation before acting (pushing, deleting, external services).
- **Assign a role only when it adds expertise** the task needs ("You are a senior iOS reviewer…").
  Skip generic roles like "helpful assistant".
- **Keep the user's intent and facts.** Don't add requirements they didn't ask for or invent details.
  Mark anything you had to assume with `<placeholder>` text or list it as an assumption.
- **Match the user's language** for the prompt unless they ask otherwise.

Default skeleton for a medium-sized task. Adapt it, and drop sections that are empty:

```
<one or two sentences: the task and the deliverable>

<context>
Why this is needed, who it is for, relevant facts, files, constraints, what was tried.
</context>

<instructions>
1. ...
2. ...
</instructions>

<output_format>
Format, length, sections, language; what to leave out.
</output_format>

Before answering, check the result against: <success criteria>. If information is missing, say what
and ask instead of guessing.
```

## 3. Reply

Reply with exactly these parts:

1. **The prompt** in one fenced code block, ready to copy. Nothing else inside the block.
2. **What I changed**: 2–5 short bullets on the main improvements and why.
3. **Assumptions**: only if you made any. List each one with the placeholder to replace, so the user
   can fix it in one edit.

Keep the reply short. If the user asks for changes, return the full revised prompt again, not a diff.
