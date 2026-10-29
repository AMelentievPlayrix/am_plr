---
name: merge-pp
description: Merge a Playrix/perfect-project PR to master and/or request its backport to a VSO minor version, following the team process - Asana Version VSO field + automerge label for master, the "VSO: Minor versions" candidates section for minors - then, after the merge, close the Asana task and offer /am:log. Takes an Asana task link or a GitHub PR link plus a target. Use for "/am:merge-pp <link> master", "/am:merge-pp <link> master 2026.2.8", "put this PR into the 2026.2.8 minor", "automerge these PRs".
argument-hint: "<Asana task or PR link(s)> <master | X.Y.Z | master X.Y.Z>"
disable-model-invocation: true
allowed-tools: Read Bash(gh pr *) Bash(gh api *) mcp__asana Monitor Skill
---

# Merge a perfect-project PR and request backports

Gets one or more PRs of `Playrix/perfect-project` into master and asks for their inclusion in a minor the way
the team does it. Mergify does the actual merging; this skill sets what Mergify and the release manager need,
after one confirmation from the user.

Process and sources: [reference/process.md](reference/process.md). Read it when something here looks wrong or a
case is not covered. Language and Asana rules: [communication.md](../../rules/communication.md) - chat in
English, the Asana comment in Russian, plain hyphen `-` as the dash.

## Hard rules

- **One confirmation before any write** (step 4): Version VSO, the `automerge` label, project membership, the
  comment. A second confirmation before closing the task (step 7).
- **Never set a minor version** in Version VSO and never add a minor or major version label in GitHub. Minors
  go only through the "VSO: Minor versions" project; the release manager sets the version and merges.
- **Never merge, approve, push or edit a PR body.** The only GitHub write is adding the `automerge` label.
- **Never remove existing Version VSO values** - only add the master version to the current list.
- **Ask instead of guessing**: a PR with no or several Asana links, a task with several master PRs, a missing
  candidates section, an unknown version. Use AskUserQuestion with the likely answers as options.

## Constants

- Repo: `Playrix/perfect-project` (always pass `--repo`, the current directory may be another repo).
- Version VSO field gid `1209509889030167`; its option gids come from the task (`custom_fields.enum_options`).
- "VSO: Minor versions" project gid `1208909725417189`.
- Default assignee for closing: **Anton Melentiev**, Asana user gid `1207120594833706`.
- PR link format in chat and Asana: `https://github.com/Playrix/perfect-project/pull/<N>`.

## Step 0 - inputs

From `$ARGUMENTS` and the message: one or more links, and the targets.

| Input | Accepted | Otherwise |
|---|---|---|
| Link | `github.com/Playrix/perfect-project/pull/<N>` or an Asana task URL (gid = last numeric segment) | ask |
| Target | `master`, a minor `X.Y.Z`, or both | ask; see step 2 for what gets refused |

Several links with one target apply the target to each. Process them together: one plan, one confirmation.

## Step 1 - current rules from Mergify

Read the live config, never a cached copy:

```
gh api repos/Playrix/perfect-project/contents/.mergify.yml -H "Accept: application/vnd.github.raw"
```

Take from it:
- **Master version** `M` (`X.Y`): the `label~=<X.Y>.*` condition of the queue rule `squash_master`.
- **Backport majors**: every "Backport master to stage vX.Y" rule -> major `X.Y` with branch `stage/vX.Y`.

If either cannot be parsed, stop and show the relevant part of the file.

## Step 2 - validate the target

| Target | Decision |
|---|---|
| `master`, or `X.Y` equal to `M` | master flow |
| `X.Y.Z` where `X.Y` has a backport rule | minor flow |
| `X.Y` (no patch), not `M` | **refuse** |
| `X.Y.Z` where `X.Y` = `M` | **refuse**: that minor does not exist yet, the change ships in `M` through master |
| `X.Y.Z` where `X.Y` has no backport rule | **refuse** |
| `release/*`, hotfix | **refuse**: separate hotfix flow, out of scope |

When refusing, explain why in 2-3 sentences with the source from reference/process.md, and say what is
possible instead. For example: a major after the cut gets changes only through minors approved by the release
manager, so ask for a minor `X.Y.Z`. For a major with no backport rule (sunset), there is no automated path; ask
the VSO release manager directly.

## Step 3 - resolve and inspect

**PR -> task**: Asana task links in the PR body. Exactly one -> its gid. None or several -> stop: Mergify will
not merge it either (`mergify/asana_linked` / `mergify/asana_multi`); tell the user to fix the description.

**Task -> PR**: `gh pr list --repo Playrix/perfect-project --state all --search "<task gid> in:body"
--json number,title,state,headRefName,baseRefName`. Drop backport PRs (`headRefName` starting with
`mergify/bp/`). Exactly one master PR -> use it; several or none -> ask.

**PR state**: `gh pr view <N> --repo Playrix/perfect-project --json
number,title,url,state,isDraft,baseRefName,headRefName,labels,reviewDecision,latestReviews,statusCheckRollup,mergeable,mergedAt`.

**Task state**: `asana_get_task` with
`opt_fields=name,completed,assignee.name,memberships.project.name,memberships.section.name,custom_fields.gid,custom_fields.name,custom_fields.display_value,custom_fields.multi_enum_values.name,custom_fields.multi_enum_values.gid,custom_fields.enum_options.name,custom_fields.enum_options.gid`.

**Master flow checks** (skip the flow if the PR is already merged - say so and continue with the rest):

| Check | Blocking? |
|---|---|
| `state` OPEN, `baseRefName` = `master`, not a `mergify/bp/` head | yes - stop for this PR |
| draft | yes - ask the user to mark it ready |
| label `conflicts`, `do-not-merge` or `mergify/asana_multi` | yes |
| `mergeable` = CONFLICTING | yes |
| no approval (`reviewDecision` not APPROVED and no APPROVED review from `Austin-AI-PLR`) | no - Mergify waits for it; say so |
| `[QG] VSO Fast Check (Perfect Project)` failed | no, but warn and ask whether to continue |
| `M` missing from Version VSO | no - the plan adds it |
| `M` has no option in Version VSO | yes - ask |

**Minor flow checks**:
- Candidates section: from `asana_get_project_sections(1208909725417189)` find the section whose name starts
  with `<X.Y>_` and contains `minor_candidates` (today `2026.2_approved_minor_candidates`). None or several -> ask.
- Already in "VSO: Minor versions": in the candidates section -> nothing to do; in another section (a minor
  or "Prod-check") -> it is already being handled, report the section and do not move it.
- Version VSO already contains `X.Y.Z`: the release manager has approved it; report, nothing to do.
- PR not merged to master yet: the release manager approves only tasks already in master and checked. Offer:
  request now anyway / request after the merge (re-run the skill then).
- Remind the user once of the QA rule (bug fix checked on the project; feature - mini-regression on FD) and
  ask how it was checked, for the comment. "Skip" is a valid answer.

## Step 4 - plan and confirm

Show one table per PR: PR link and title, task link, target(s), checks with their result, and the exact
writes:

1. Asana `asana_update_task`: Version VSO `<current values>` -> `<current values> + M` (master flow, when missing).
2. GitHub: add the label `automerge` (master flow, when missing).
3. Asana: add the task to "VSO: Minor versions" / `<candidates section>` (minor flow).
4. Asana comment (minor flow), shown in full. Short, Russian, plain text, e.g.:
   `Нужно также в 2026.2.8. PR: https://github.com/Playrix/perfect-project/pull/20284 (в master смержен 29.10).`
   Add one line on how it was checked if the user gave it. No other text.

Ask once with AskUserQuestion: apply all / edit the comment / cancel. Nothing is written before this.

## Step 5 - apply and verify

In this order, verifying each step before the next:

1. **Version VSO**: `asana_update_task` with `custom_fields` `{"1209509889030167": [<all current option gids>, <gid of M>]}`.
   Re-read the task and check the value. The bot then adds the label `M` to the PR; check with `gh pr view`
   after a short while and report if it hasn't appeared yet (do not add it by hand).
2. **automerge**: `gh pr edit <N> --repo Playrix/perfect-project --add-label automerge`. Re-read the labels.
3. **Minor project**: look for an Asana tool that adds a task to a project (ToolSearch for asana tools with
   "project" in the name or an `add_projects` parameter in update tools). If found, add the task with the
   candidates section. If not (the V1 Asana MCP has no such tool), tell the user the exact manual step - open
   `<task link>`, "Add to project" -> "VSO: Minor versions" -> section `<name>` - wait for them to confirm, then
   re-read the task memberships and check.
4. **Comment**: `asana_create_task_story` with `text`, exactly the approved text, only after step 3 is verified.

Then report per PR: what was done, what Mergify will do next (queue -> Fast Check -> Full Check -> squash merge;
the release manager handles the minor), and where to watch it:
[Mergify dashboard](https://dashboard.mergify.com/queues/status?repository=perfect-project) and the PR page.

## Step 6 - wait for the master merge

The queue usually takes 1-3 hours. Offer: wait now / check later (re-running the skill with the same link
resumes: merged PRs skip to step 7).

To wait, run under Monitor a loop that ends on an observable change, checking every 5 minutes, up to 4 hours:
the PR is no longer OPEN, or it got `mergify/stop_deploy` or `conflicts` (dequeued). On dequeue or conflict,
read the latest Mergify comment on the PR and report the cause - do not re-add labels.

## Step 7 - after the merge

For each task whose PR is now merged to master (Руслан: close your task after the master merge, even when a
minor is requested):

1. Propose, and on confirmation do: assign to Anton Melentiev if the assignee differs (`asana_update_task`
   `assignee: 1207120594833706`), then `completed: true`. Re-read and check. Never touch tasks of other PRs.
2. Then offer to run `/am:log` to record the work (Skill tool, `skill: "am:log"`). Run it only on a yes.
