# engine-create-autotests-in-batch

Automate all the Qase cases under one Asana parent task, as a batch, in vso-engine-autotests.

```
/am:engine-create-autotests-in-batch <Asana parent task link> <memory file path>
```

**What it does**

- Analysis (read-only): one subagent per case, all in parallel. Each one decides whether its case can be
  automated in autotests alone, and how. Ends with a plan: shared framework items, tests from simplest
  first, a stacked merge order, proposed Asana actions and open questions.
- Waits for you to approve the plan.
- Execution: one item at a time, through `engine-create-autotest`. Each item gets its own branch and PR, and
  halted items become `[WIP]` draft PRs. At the end it posts Asana comments and requests reviewers on green PRs.
- After you merge: rebases the stacked PRs and re-validates them.

The memory file is required, and you choose where it lives. Put it somewhere git ignores, e.g.
`~/projects/am_plr/artifacts/log/<sdk>.md`. Everything the batch learns goes there, so a later session can resume
from it.

Needs the `qase` and `asana` MCP servers. Run it from vso-engine-autotests.

Instructions for Claude: [SKILL.md](SKILL.md).
