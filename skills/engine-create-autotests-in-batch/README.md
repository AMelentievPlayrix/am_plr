# engine-create-autotests-in-batch

Automate all the Qase cases under one Asana parent task, as a batch, in vso-engine-autotests. Blockers first.

```
/am:engine-create-autotests-in-batch <Asana parent task link> [memory folder]
```

**What it does**

1. **Memory**: proposes a long-term memory folder `am_plr/artifacts/memory/YYYY-MM-DD_<slug>/` and asks you first.
   You read `status.md` (one screen: where we are, what needs you, what is left). Everything else in the folder is
   the agent's.
2. **Analysis** (read-only): one subagent per case. Every Asana blocker is checked in product source: real, false
   or partly real.
3. **Blocker plan**: per blocker, the fix (C++ TestSDK RPC, Python framework item, Qase-side decision, infra) and
   the Asana actions. **You approve it** (approval 1).
4. **Blocker fixes**:
   - fixes planned, reviewed and implemented in worktrees;
   - TestSDK built on TeamCity;
   - all fixes checked by one throwaway device test;
   - framework PRs merged;
   - perfect-project PRs reviewed, then you run `/am:merge-pp`.
5. **Test plan**: **you approve it** (approval 2) and add the listed allow rules (`gh pr merge`, `gh pr ready`,
   `gh pr edit`, the Qase script).
6. **Tests**, autonomously, one at a time through `engine-create-autotest`, each branched from master. Each green PR
   is merged right away. Then: Asana comment and subtask done, Qase automation set, branch deleted, `/am:log`.
7. **Follow-ups**, a **separate-platform track** (e.g. UWP subtasks plus a hand-off file for a Windows agent), and
   a final list: `<PR> - <Asana task> - <Qase case> - <what>`.

Device runs never touch `.env` (`engine-create-autotest/scripts/run_on_platform.py`), and Qase writes keep the
token out of the shell (`scripts/qase_case.py`).

Needs the `qase`, `asana` and `teamcity` MCP servers. Run it from vso-engine-autotests.

Instructions for Claude: [SKILL.md](SKILL.md).
