# describe-work

Create an Asana task and a GitHub PR for your changes, and link them to each other.

```
/am-plr:describe-work [which changes]
```

**What it does**

- Commits pending changes first (via `/am-plr:commit`).
- Asana task (what is needed) in the VSO QA Auto backlog, assigned to you.
- PR (what was done) with the task link, reviewer set.
- Comment with the PR link on the task.

Asks first if it's unclear which changes to describe. Texts are in Russian.

Instructions for Claude: [SKILL.md](SKILL.md).
