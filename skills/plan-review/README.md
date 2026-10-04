# plan-review

Find the major problems in a plan and decide on fixes with you.

```
/am-plr:plan-review [path to plan]
```

**What it does**

- Checks the plan against the real code: bugs, missing steps, regressions, risks, rule violations.
- Major issues only, no style nitpicks, no limit on how many.
- Asks about each one as a question with proposed fixes (recommended first).
- Offers to update the plan with your answers.

Uses the current plan if no path is given.

Instructions for Claude: [SKILL.md](SKILL.md).
