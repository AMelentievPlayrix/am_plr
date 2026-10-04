# engine-create-autotest

Automate a Qase test case as a new vso-engine-autotests test, end to end.

```
/am-plr:engine-create-autotest   (give the Qase case id and the Asana task link)
```

**What it does**

- Reads the case from Qase.
- Writes the test with existing steps, adds steps only if needed.
- Validates on every applicable platform (max 5 runs each).
- Opens a PR and comments on the Asana task.

Needs the `qase` and `cats-mcp-server` MCP servers. Run it inside vso-engine-autotests.

Instructions for Claude: [SKILL.md](SKILL.md).
