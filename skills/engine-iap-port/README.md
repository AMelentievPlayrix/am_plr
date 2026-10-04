# engine-iap-port

Port an iOS in-app purchase test to macOS or UWP, in two phases.

```
/am-plr:engine-iap-port <plan|implement> <macos|uwp> <test id>
```

**What it does**

- `plan` — reads the iOS test and the Qase case, writes a plan. Changes no files.
- `implement` — implements the plan from the previous chat, runs and validates it (max 3 attempts).

Run `plan` and `implement` in separate chats so you can review the plan in between.

Instructions for Claude: [SKILL.md](SKILL.md).
