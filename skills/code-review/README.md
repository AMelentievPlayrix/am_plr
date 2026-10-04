# code-review

Check finished changes against the plan and the rules.

```
/am-plr:code-review [commit range] [plan path]
```

**What it does**

- Reviews uncommitted changes, or your branch vs `origin/master`, if no range is given.
- Checks plan coverage, correctness, regressions, rules, security, tests and changes outside the plan.
- Report: verdict (PASS / PASS WITH NOTES / FAIL) and findings by severity, each with a fix.

Read-only. Offers to fix Critical and Important findings only if you agree.

Instructions for Claude: [SKILL.md](SKILL.md).
