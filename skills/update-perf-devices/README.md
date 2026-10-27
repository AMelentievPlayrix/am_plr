# update-perf-devices

Keep the BrowserStack devices of PerfectProject's nightly perf runs healthy: find the devices that turn the
runs red, find out why, pick a replacement, open the Asana task and PR, and after the merge record the change
on the inventory task "Устройства".

```
/am:update-perf-devices investigate [master|stage/vX.Y|both]
/am:update-perf-devices follow-up
/am:update-perf-devices sync-inventory
```

**What it does**

- `investigate` (default `both`): reads the last builds of the three `*_Test_Benchmark_BrowserStack` configs
  per branch, the batch logs, VictoriaMetrics and the inventory task; tells a gone or broken device from a
  test or capability problem; ranks replacements. Reports in chat and asks before creating anything. After
  approval: Asana task, branch in a worktree from `origin/master`, commit via `/am:commit`, draft PR, and the
  manual TeamCity run needed to verify it (started only on request).
- `follow-up`: checks the device PRs and their Mergify backports. For merged ones it drafts the dated comment
  and the new description for the inventory task and the backport label steps, and writes them after approval.
- `sync-inventory`: rebuilds the inventory description from the YAML files and metrics, shows the diff, and
  updates it after approval.

**Needs**

- MCP servers `teamcity`, `victoriametrics` (VPN), `asana`; the `gh` CLI; perfect-project and
  teamcity-settings-pp next to am_plr.
- Optional: `BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY` in the environment, to check against
  `devices.json`. Without them only the public device list is checked, and the report says so.

Scripts: `scripts/check_devices.py` (YAML lists and candidates against `devices.json` and the public list),
`scripts/scan_batch_logs.py` (batch log lines that matter from `test_artifacts.zip`, with the key masked).

Instructions for Claude: [SKILL.md](SKILL.md).
