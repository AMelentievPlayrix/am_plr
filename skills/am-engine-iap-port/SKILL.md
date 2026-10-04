---
name: am-engine-iap-port
description: Port an existing iOS in-app purchase autotest in vso-engine-autotests to macOS or UWP — first plan (read-only), then implement and validate the planned variant. Use for "add a macOS/UWP variant of IAP test 10559", "port purchase test to UWP".
disable-model-invocation: true
argument-hint: "<plan|implement> <macos|uwp> <test id>"
---

# Port an in-app purchase test to macOS or UWP

Two phases, usually in two separate chats so the plan can be reviewed first:

| Phase | macOS | UWP |
|---|---|---|
| **plan** — analyse the iOS (and macOS) test, write a plan, change no files | [reference/plan-macos.md](reference/plan-macos.md) | [reference/plan-uwp.md](reference/plan-uwp.md) |
| **implement** — implement the plan from the previous chat, run and validate | [reference/implement-macos.md](reference/implement-macos.md) | [reference/implement-uwp.md](reference/implement-uwp.md) |

Read `$ARGUMENTS` for phase, platform and test id; ask if any is missing. Then follow the matching
reference file exactly.

Shared rules that apply on top of the reference file:

- Test code follows [authoring-rules.md](../am-engine-create-autotest/reference/authoring-rules.md)
  § In-app purchase.
- The validation run limit in the reference files is 3 attempts; that is intentional for this
  narrow, plan-driven change and overrides the 5-run budget of the other engine skills.
- Commits go through the `am-commit` skill; PR and Asana conventions come from
  [writing-git-github-asana.md](../../rules/writing-git-github-asana.md).
