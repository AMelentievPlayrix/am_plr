# commit

Split your uncommitted changes into small, logical commits with Russian messages.

```
/am-plr:commit [paths or scope]
```

**What it does**

- Reads the diff and groups changes by what they do, not by folder.
- Stages exact files or hunks, never `git add -A`.
- Writes short Russian messages in the repo's style.
- Never commits secrets, never rewrites pushed history.

Every other skill commits through this one, so the commit policy lives only here.

Instructions for Claude: [SKILL.md](SKILL.md).
