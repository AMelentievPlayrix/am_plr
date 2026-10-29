# merge-pp

Merge a perfect-project PR to master and/or request its backport to a VSO minor, the way the team process
expects. Mergify does the merging; the skill sets what Mergify and the release manager need.

```
/am:merge-pp <PR or Asana task link> master
/am:merge-pp <PR or Asana task link> 2026.2.8
/am:merge-pp <link> <link> <link> master 2026.2.8
```

**What it does**

1. Reads the live `.mergify.yml` to learn the master version (today `2026.3`) and which majors still get minors.
2. Refuses what the process does not allow, and says why: a major without a patch number, a minor of a sunset
   major, hotfixes into `release/*`.
3. Finds the PR from the task or the task from the PR, and checks the PR: Asana link, draft, conflicts,
   approval, Fast Check.
4. Shows the plan and asks once:
   - **master**: adds the master version to the task's Version VSO field (the bot turns it into the `2026.3`
     label), then adds `automerge` in GitHub;
   - **minor**: adds the task to "VSO: Minor versions" / `<X.Y>_approved_minor_candidates` with a short Russian
     comment ("Нужно также в X.Y.Z"). The release manager approves it, sets the minor version and merges. The
     skill never sets a minor version itself.
5. Optionally waits for the merge (Monitor), or you re-run it later with the same link.
6. After the master merge: offers to assign the task to Anton Melentiev and close it, then to run `/am:log`.

**Needs**

- `gh` signed in with access to Playrix/perfect-project.
- The `asana` MCP. The V1 Asana MCP cannot add a task to a project, so for the minor step the skill gives you
  the one manual click and checks the result.

Process, sources and what was not verified: [reference/process.md](reference/process.md).
Instructions for Claude: [SKILL.md](SKILL.md).
