"""am_plr sync: checks the am-plr plugin, links rules, generates MCP config and settings previews.

Run via scripts/setup.sh (it creates the venv first). Stdlib only, Python 3.11+.

Layering:
  skills/agents  shipped as the Claude Code plugin "am-plr" (this repo): namespaced as
                 am-plr:<skill>, so they never collide with upstream project skills.
  rules          plugins can't ship rules -> linked as one dir ~/.claude/rules/am_plr.
  mcp            user scope (generated commands); a repo's own .mcp.json still wins inside it.
                 Not in the plugin: plugin servers get tool names mcp__plugin_am-plr_<server>__*,
                 which would break upstream skills that call mcp__qase__* etc.
"""

import json
import os
import re
import glob
import shlex
import shutil
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
CLAUDE_JSON = CLAUDE_DIR / ".claude.json" if os.environ.get("CLAUDE_CONFIG_DIR") else Path.home() / ".claude.json"
GEN_DIR = REPO / "artifacts" / "generated"
MCP_JSON = GEN_DIR / "mcp.json"
VSCODE_USER_DIR = next((d for d in (Path.home() / "Library/Application Support/Code/User",  # macOS
                                    Path.home() / ".config/Code/User") if d.is_dir()), None)  # Linux

if sys.stdout.isatty():
    B, G, Y, R, D, N = "\033[1m", "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[0m"
else:
    B = G = Y = R = D = N = ""

PLUGIN_ID = "am-plr@am-plr"
warnings = []
todo = []  # (title, [lines]) printed as numbered "Next steps" at the end


def step(msg):
    print(f"\n{B}==> {msg}{N}")


def ok(msg):
    print(f"  {G}+{N} {msg}")


def info(msg):
    print(f"  {D}{msg}{N}")


def warn(msg):
    warnings.append(msg)
    print(f"  {Y}!{N} {msg}")


def frontmatter_name(md: Path):
    """`name:` from YAML frontmatter, or None."""
    try:
        text = md.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.match(r"---\s*\n(.*?)\n---", text, re.S)
    if m:
        n = re.search(r"^name:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", m.group(1), re.M)
        if n:
            return n.group(1).strip()
    return None


def visible(p: Path):
    return not p.name.startswith((".", "_"))


# ----------------------------------------------------------------------------- config

def load_config():
    cfg_file = REPO / "upstreams.toml"
    if not cfg_file.is_file():
        return {}, {}
    cfg = tomllib.loads(cfg_file.read_text())
    upstreams = {}
    for name, u in cfg.get("upstream", {}).items():
        upstreams[name] = Path(os.path.expanduser(u["path"])).resolve()
    return upstreams, cfg.get("mcp", {})


def claude_cli():
    """`claude` on PATH, else the newest binary bundled with the VS Code extension."""
    found = shutil.which("claude")
    if found:
        return "claude"
    bundled = sorted(glob.glob(str(Path.home() / ".vscode/extensions/anthropic.claude-code-*"
                                                 "/resources/native-binary/claude")))
    return shlex.quote(bundled[-1]) if bundled else "claude"


def check_plugin(cli):
    """Skills/agents come from the am-plr plugin; setup only checks it is installed and enabled."""
    try:
        settings = json.loads((CLAUDE_DIR / "settings.json").read_text())
    except (OSError, json.JSONDecodeError):
        settings = {}
    if (settings.get("enabledPlugins") or {}).get(PLUGIN_ID):
        info(f"plugin {PLUGIN_ID} enabled - skills load from {REPO}/skills")
        return
    print(f"  {Y}~{N} plugin {PLUGIN_ID} not installed yet")
    todo.append(("Install the am-plr plugin (once per machine)", [
        f"{cli} plugin marketplace add {shlex.quote(str(REPO))}",
        f"{cli} plugin install {PLUGIN_ID}",
        "# or inside Claude Code: /plugin marketplace add <path>  then  /plugin install am-plr@am-plr",
    ]))


def remove_old_links():
    """Earlier setup versions symlinked skills/agents into ~/.claude; the plugin replaces them."""
    for kind in ("skills", "agents"):
        d = CLAUDE_DIR / kind
        for target in sorted(d.iterdir()) if d.is_dir() else []:
            if target.is_symlink() and REPO in Path(os.readlink(target)).parents:
                target.unlink()
                info(f"removed old symlink {target} (now provided by the plugin)")


def sync_rules():
    """Whole rules/ dir as one symlink: add/remove files without re-running, no name clashes."""
    rules_dir = CLAUDE_DIR / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    target, src = rules_dir / "am_plr", REPO / "rules"
    if target.is_symlink() and Path(os.readlink(target)) == src:
        info(f"{target} -> {src} up to date")
    elif target.exists() and not target.is_symlink():
        warn(f"rules NOT linked: {target} exists and is not a symlink")
        return
    else:
        if target.is_symlink():
            target.unlink()
        target.symlink_to(src)
        ok(f"{target} -> {src}")
    n = sum(1 for p in src.rglob("*.md") if visible(p))
    info(f"{n} rule file(s); new/deleted rule files are picked up without re-running setup")


# ----------------------------------------------------------------------------- settings

def read_jsonc(path: Path):
    """(data, had_comments). VS Code settings allow // and /* */ comments and trailing commas."""
    text = path.read_text(encoding="utf-8")
    comments = False

    def drop(m):  # strings are matched first, so comment-like text inside them survives
        nonlocal comments
        tok = m.group(0)
        if tok.startswith('"'):
            return tok
        comments = comments or tok.startswith("/")
        return ""

    clean = re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/|,(?=\s*[}\]])', drop, text, flags=re.S)
    return (json.loads(clean) if clean.strip() else {}), comments


def merge(base, ours, path=""):
    """am_plr wins for scalars, dicts merge recursively, lists are unioned. Returns changed keys."""
    changed = []
    for k, v in ours.items():
        key = f"{path}.{k}" if path else k
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            changed += merge(base[k], v, key)
        elif isinstance(v, list) and isinstance(base.get(k), list):
            extra = [x for x in v if x not in base[k]]
            if extra:
                base[k] += extra
                changed.append(f"{key} (+{len(extra)})")
        elif base.get(k) != v:
            base[k] = v
            changed.append(key)
    return changed


def preview_settings(label, src: Path, dst: Path, out_name: str):
    """Merge am_plr keys over the current settings into artifacts/generated/<out_name>. Never writes dst."""
    ours, _ = read_jsonc(src)
    current, comments = read_jsonc(dst) if dst.is_file() else ({}, False)
    changed = merge(current, ours)
    out = GEN_DIR / out_name
    if not changed:
        out.unlink(missing_ok=True)
        info(f"{label}: up to date ({dst})")
        return None
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(current, indent=4, ensure_ascii=False) + "\n")
    out.chmod(0o600)  # contains everything from the current file, incl. any tokens
    print(f"  {Y}~{N} {label}: {', '.join(changed)}")
    if comments:
        warn(f"{label}: {dst} has comments - the generated file drops them, merge by hand to keep them")
    return label, dst, out


def sync_settings():
    """Common settings only; project-specific settings stay in the projects themselves."""
    previews = []
    claude_src = REPO / "config" / "claude" / "settings.json"
    if claude_src.is_file():
        previews.append(preview_settings("Claude Code", claude_src, CLAUDE_DIR / "settings.json",
                                         "claude-settings.json"))
    vscode_src = REPO / "config" / "vscode" / "settings.json"
    if vscode_src.is_file():
        if VSCODE_USER_DIR:
            previews.append(preview_settings("VS Code", vscode_src, VSCODE_USER_DIR / "settings.json",
                                             "vscode-settings.json"))
        else:
            warn("VS Code user settings dir not found - is VS Code installed?")
    return [p for p in previews if p]


def check_secrets(servers):
    """Every ${VAR} used by the MCP config must be set; setup.sh loads am_plr/.env into the env first."""
    env_file, example = REPO / ".env", REPO / ".env.example"
    needed = {v: n for n, s in servers.items() for v in env_refs(s)}
    if not env_file.exists():
        warn(f"{env_file} missing")
        todo.append(("Create .env with your tokens (git-ignored)", [f"cp {example} {env_file}  # then fill it in"]))
        return
    missing = sorted(v for v in needed if not os.environ.get(v))
    for var in missing:
        warn(f"{var} (mcp '{needed[var]}') is empty in {env_file}")
    if missing:
        todo.append(("Fill in empty tokens, then open a new terminal", [f"{env_file}: {', '.join(missing)}"]))
    elif needed:
        info(f"all {len(needed)} MCP token(s) set in {env_file}")


def check_shell():
    """~/.zshrc is never edited; only report whether it sources am_plr/shell/init.zsh."""
    zshrc, init = Path.home() / ".zshrc", REPO / "shell" / "init.zsh"
    text = zshrc.read_text(errors="ignore") if zshrc.is_file() else ""
    if re.search(r"^\s*(source|\.)\s+.*am_plr/shell/init\.zsh", text, re.M):
        info(f"{zshrc} sources {init}")
        return
    print(f"  {Y}~{N} {zshrc} does not source am_plr shell config yet")
    line = f"source {str(init).replace(str(Path.home()), '~', 1)}"
    todo.append(("Load tokens, aliases and prompt in every terminal", [
        f"echo {shlex.quote(line)} >> ~/.zshrc   # then open a new terminal and restart VS Code"]))


def settings_todo(previews):
    q = shlex.quote
    for label, dst, out in previews:
        todo.append((f"Review and apply {label} settings (your keys + am_plr keys, nothing removed)", [
            f"diff {q(str(dst))} {q(str(out))}",
            f"cp {q(str(dst))} {q(str(dst) + '.bak')} && cp {q(str(out))} {q(str(dst))}",
        ]))


# ----------------------------------------------------------------------------- mcp

def subst(v, root=None):
    """Fill ${root} / ${AM_PLR} / ${HOME}. Token ${VAR}s stay as-is: Claude Code expands them at runtime."""
    if isinstance(v, list):
        return [subst(x, root) for x in v]
    if isinstance(v, dict):
        return {k: subst(x, root) for k, x in v.items()}
    if not isinstance(v, str):
        return v
    v = v.replace("${AM_PLR}", str(REPO)).replace("${HOME}", str(Path.home()))
    return v.replace("${root}", str(root)) if root is not None else v


def env_refs(server):
    return sorted(set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)", json.dumps(server))))


def build_mcp(upstreams, mcp_specs):
    """Every [mcp.<name>] block in upstreams.toml -> one entry in artifacts/generated/mcp.json.

    `from = "<upstream>"` makes ${root} that repo's path; without it the server is our own (code in mcp/).
    `manual = "..."` prints instructions instead; `install = "..."` is a hint while `command` is missing.
    """
    servers, manual = {}, {}
    for name, spec in mcp_specs.items():
        spec = dict(spec)
        src = spec.pop("from", None)
        root = upstreams.get(src) if src else REPO
        if root is None or not root.is_dir():
            warn(f"mcp '{name}' skipped: upstream '{src}' not found ({root})")
            continue
        if "manual" in spec:
            manual[name] = (src or "am_plr", subst(spec["manual"], root))
            info(f"mcp '{name}' needs manual setup, see below")
            continue
        install = spec.pop("install", None)
        server = {"type": "http" if "url" in spec else "stdio", **subst(spec, root)}
        cmd = server.get("command", "")
        if cmd.startswith("/") and not Path(cmd).exists():
            hint = install or (f"set up the {src} venv, e.g. `uv sync` there" if src else "install it")
            warn(f"mcp '{name}': {cmd} does not exist yet ({hint})")
        servers[name] = server
        refs = env_refs(server)
        ok(f"mcp '{name}' ({src or 'am_plr'})" + (f" - token(s) from .env: {', '.join(refs)}" if refs else ""))

    GEN_DIR.mkdir(parents=True, exist_ok=True)
    MCP_JSON.write_text(json.dumps({"mcpServers": servers}, indent=2) + "\n")
    return servers, manual


def check_skill_mcp_refs(servers, manual, skill_dirs):
    """Warn when skills call mcp__<server>__ that no config provides."""
    known = set(servers) | set(manual)
    try:
        known |= set(json.loads(CLAUDE_JSON.read_text()).get("mcpServers") or {})
    except (OSError, json.JSONDecodeError):
        pass
    for skill_dir in skill_dirs:
        refs = set()
        for f in skill_dir.rglob("*.md"):
            refs |= set(re.findall(r"mcp__([A-Za-z0-9_-]+?)__", f.read_text(encoding="utf-8", errors="ignore")))
        for r in sorted(refs - known):
            warn(f"skill '{skill_dir.name}' calls mcp__{r}__* but no MCP server '{r}' is configured")


def mcp_todo(servers, manual, cli):
    """Compare with user-scope MCP config and queue the commands to run. Nothing is written."""
    try:
        current = json.loads(CLAUDE_JSON.read_text()).get("mcpServers") or {}
    except (OSError, json.JSONDecodeError):
        current = {}
    strip = lambda s: {k: v for k, v in s.items() if k != "type"}
    new = [n for n in servers if n not in current]
    changed = [n for n in servers if n in current and strip(current[n]) != strip(servers[n])]
    stale = [n for n, s in current.items() if n not in servers and str(REPO) in json.dumps(s)]
    for n in servers:
        mark = f"{G}+ new{N}" if n in new else f"{Y}~ differs{N}" if n in changed else f"{D}= in sync{N}"
        print(f"    {n}: {mark}")
    for n in stale:
        print(f"    {n}: {R}- no longer in am_plr{N}")

    if new or changed or stale:
        # values are read from the generated file, so tokens never land in chat/terminal history
        lines = [f"{cli} mcp remove --scope user {shlex.quote(n)}" for n in changed + stale]
        lines += [f"{cli} mcp add-json --scope user {shlex.quote(n)} "
                  f"\"$(jq -c '.mcpServers[\"{n}\"]' {shlex.quote(str(MCP_JSON))})\"" for n in new + changed]
        todo.append(("Add MCP servers for all projects (user scope)", lines))
    for n, (src, text) in manual.items():
        if n not in current:
            todo.append((f"Set up MCP '{n}' by hand (from {src})", text.strip().splitlines()))


# ----------------------------------------------------------------------------- main

def main():
    upstreams, mcp_specs = load_config()
    cli = claude_cli()

    step("Plugin (skills, agents) -> Claude Code")
    remove_old_links()
    check_plugin(cli)
    skill_dirs = [d for d in sorted((REPO / "skills").glob("*")) if (d / "SKILL.md").is_file()]
    info(f"{len(skill_dirs)} skill(s): {', '.join('am-plr:' + d.name for d in skill_dirs)}")

    step(f"Rules -> {CLAUDE_DIR / 'rules' / 'am_plr'}")
    sync_rules()

    step(f"Settings (config/) -> {GEN_DIR}")
    settings_todo(sync_settings())
    check_shell()

    step(f"MCP -> {MCP_JSON}")
    servers, manual = build_mcp(upstreams, mcp_specs)
    check_secrets(servers)
    check_skill_mcp_refs(servers, manual, skill_dirs)
    mcp_todo(servers, manual, cli)

    step("Done" + (f" with {len(warnings)} warning(s)" if warnings else ""))
    for w in warnings:
        print(f"  {Y}!{N} {w}")
    order = ("Create .env", "Fill in", "Load tokens", "Install the am-plr", "Add MCP", "Set up MCP", "Review")
    todo.sort(key=lambda t: next((i for i, p in enumerate(order) if t[0].startswith(p)), len(order)))
    if todo:
        print(f"\n{B}Next steps{N} - setup changed nothing outside ~/.claude/rules; run these yourself:")
        for i, (title, lines) in enumerate(todo, 1):
            print(f"\n  {B}{i}. {title}{N}")
            for line in lines:
                print(f"     {line}")
        print(f"\n  {B}{len(todo) + 1}. Restart Claude Code{N}, then check with /plugin, /mcp and /skills.")
    else:
        print(f"\n  {G}All set.{N} Skill/rule edits are live (/reload-plugins in an open session).")
    info("Re-run setup after editing config/, upstreams.toml, .env, or pulling upstream repos.")


if __name__ == "__main__":
    main()
