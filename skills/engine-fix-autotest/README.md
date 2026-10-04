# engine-fix-autotest

Fix a broken vso-engine-autotests test, starting from its Asana task.

```
/am-plr:engine-fix-autotest <Asana task link>
```

**What it does**

- Gets a real failure signature before touching code.
- Checks whether someone already fixed it upstream.
- Finds the root cause and fixes it, with no sleeps, retries or weakened checks.
- Validates (max 5 runs per platform), opens a PR, comments on the task.

Stops and reports if the budget runs out or the cause looks like a product bug.

Instructions for Claude: [SKILL.md](SKILL.md).
