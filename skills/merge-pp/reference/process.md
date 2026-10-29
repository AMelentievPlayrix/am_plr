# perfect-project: merge and backport process (with sources)

Researched 2026-10-29. The Coda process docs are behind SSO and were **not** read; everything below comes from
the Mergify config, PR timelines, Asana task stories and Slack. If the process seems to have changed, check the
Coda pages first:
[VSO 2.0 Major/Minor](https://coda.io/d/_dkK6hiOt6-E/VSO-2-0-Major-Minor_suZDWdmv),
[Branching strategy](https://coda.io/d/_dkK6hiOt6-E/WiP-Branching-strategy_suMAD4j1),
[Asana flow](https://coda.io/d/_dkK6hiOt6-E/WiP-Asana-flow-against-Branching-strategy_suuVecpn).

## Moving parts

| Piece | Role |
|---|---|
| Mergify (`.mergify.yml` on `master`) | queues, squashes, merges; opens backport PRs `mergify/bp/stage/vX.Y/pr-N` |
| Asana field **Version VSO** (multi-select, gid `1209509889030167`) | source of truth for version labels |
| `playrix-asana-services` bot | syncs Version VSO -> GitHub labels (`2026.3`, `2026.2.7`, ...); can remove labels added by hand |
| TeamCity bot in Asana | attaches PRs to tasks, sets Status VSO, blocks the task on "PR N Status" subtasks |
| "VSO: Minor versions" (gid `1208909725417189`, formerly "VSO. Release Plan") | requests to include a task in a minor |
| "VSO: Major versions" (gid `1209765217658664`) | planning; tasks land here automatically by an Asana rule; triggers nothing |

## Merge to master

Mergify rule "Automatically squash and merge" plus queue `squash_master` require:

- exactly one Asana task link in the PR body -> `mergify/asana_linked` (two links -> `mergify/asana_multi`, blocks);
- the label of the version in master (`squash_master`: `label~=<X.Y>.*`, today `2026.3`). It comes from
  Version VSO; without it Mergify comments "Необходимо указать версию в задаче в поле Version VSO"
  (PR #20345, 2026-10-28);
- an approval from `@Playrix/vso-programmers`, `@Playrix/qa-vso`, or `Austin-AI-PLR` with no changes requested;
- `[QG] VSO Fast Check (Perfect Project)` green to queue, Full Check green to merge;
- no `conflicts`, `do-not-merge`, not a draft;
- the `automerge` label. Then: `mergify/start_deploy` -> squash merge -> `mergify/integration`.

The author sets the master version in Version VSO (the Mergify comment is addressed to the author).
After the merge the author closes their own task (Руслан Байбеков, DM 2026-10-29).

## Backport to a minor

- Mergify rule "Backport master to stage vX.Y": base `master` + label `<master version>` + label `X.Y.*` ->
  after the merge, a backport PR into `stage/vX.Y` with `automerge`, `skip-review`, `backported` that merges by
  itself. Examples: #20101 -> #20309, #20315 -> #20341.
- **Nobody sets a minor version on their own.** Add the task to "VSO: Minor versions" with a short reason;
  the VSO release manager approves, sets Version VSO, and merges.
  - David Brady, #vso_internal, 2026-03-18 ("запрещается проставление версии самостоятельно ... согласовывать
    каждую задачу в минор через VSO. Release Plan").
  - Сергей Зетилов, #vso-delivery-support, 2025-10-01 ("через УК VSO, надо написать обоснование ... и в какую
    версию").
  - Руслан Байбеков, DM 2026-10-29: "клади их просто в проект в асане и всё, я сам их буду заливать",
    "заливка в мастер никак не связана с минором", "клади в секцию 2026.2_approved_minor_candidates".
- The release manager approves only tasks already merged to master and checked (David Brady, #vso_internal,
  2025-03-21).
- QA requirement since 2026-09-30 (Руслан Байбеков, #vso_qa): product bug fixes must be checked on the project
  where the bug was found, after the PP check; tasks and features need a mini-regression of related functionality
  on FD.

## What is not allowed

- Merging straight into a major (`stage/vX.Y` or `release/vX.Y`) by request: after the cut, a major gets changes
  only through minors approved by the release manager. A major that is still in master is "merge to master".
- Minors of a major with no "Backport master to stage vX.Y" rule in `.mergify.yml` (sunset versions): there is
  no automated path and no approval route through this flow.
- Hotfixes into `release/*` (`mergify/hotfix`, "Backport release/hotfix ..." rules): a separate flow, out of scope.
