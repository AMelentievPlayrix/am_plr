# mcp/

- `<name>/` - code of MCP servers I write myself. Configure each one as `[mcp.<name>]` in
  `../upstreams.toml`, then re-run setup.
- `.env` - tokens for **every** server in the generated `../.mcp.json` (team servers included),
  git-ignored. Setup creates it from `.env.example` and adds an empty `VAR=` line for every credential
  `../upstreams.toml` references; you only fill in the values.

Setup writes the values from `.env` literally into `../.mcp.json`. A variable left empty here is
omitted from that file, and the server falls back to its own `.env` - see `.env.example`.
