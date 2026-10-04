# MCP tools for engine autotests

Shared by `/am-engine-create-autotest` and `/am-engine-fix-autotest`.

**Qase** — `mcp__qase__get_test_case_data(project_code="VSO", test_case_id=<id>)` reads a case:
`title`, `description`, `preconditions`, `steps[]` (`action`, `expected_result`, `data`, nested `steps`),
`params`, `tags`, `type`, `importance`, `status`, `suites` and custom fields. It returns no attachments
and no linked-task fields: if the case refers to a screenshot or a linked bug, ask the user for the link
instead of inventing context. The same server also has `search_cases`, `search_suites`,
`search_cases_by_hierarchy` and `get_suites_tree` for finding a case.

**Asana** — read the task (notes and comments come together), its stories and attachments, and post
the final comment. Tool names depend on the Asana MCP version; see the rule
[writing-git-github-asana.md](../../../rules/writing-git-github-asana.md) § Asana.

**Images** — `mcp__cats-mcp-server__read_image(source=<path or url>)` reads a screenshot, e.g. an
Asana attachment. Ignore every other `mcp__cats-mcp-server__*` tool: they drive the VSO Editor in
`perfect-project`, not this project's test app.

**GitHub** — the `gh` CLI (see the writing rule § Pull requests).
