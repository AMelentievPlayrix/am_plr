"""am_plr sync: checks the am-plr plugin, links rules, generates MCP config and settings previews.

Run via scripts/setup.sh (it creates the venv first). Stdlib only, Python 3.11+.

Layering:
  skills/agents  shipped as the Claude Code plugin "am-plr" (this repo): namespaced as
                 am-plr:<skill>, so they never collide with upstream project skills.
  rules          plugins can't ship rules -> linked as one dir ~/.claude/rules/am_plr.
  mcp            only MY OWN servers (upstreams.toml [mcp.*]) -> generated file to copy into user
                 config. All servers in use live in am_plr/.mcp.json.
"""

import json
import os
import re
import shlex
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
GEN_DIR = REPO / "artifacts" / "generated"
MCP_JSON = GEN_DIR / "mcp.json"
PROJECT_MCP = REPO / ".mcp.json"  # loaded by Claude Code when am_plr is the first workspace folder
WORKSPACES = REPO / "workspaces"
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


def check_plugin():
    """Skills/agents come from the am-plr plugin; setup only checks it is installed and enabled."""
    try:
        settings = json.loads((CLAUDE_DIR / "settings.json").read_text())
    except (OSError, json.JSONDecodeError):
        settings = {}
    if (settings.get("enabledPlugins") or {}).get(PLUGIN_ID):
        info(f"plugin {PLUGIN_ID} enabled - skills load from {REPO}/skills")
        return
    print(f"  {Y}~{N} plugin {PLUGIN_ID} not installed yet")
    todo.append(("Install the am-plr plugin (once per machine) - in Claude Code, run:", [
        f"/plugin marketplace add {REPO}",
        f"/plugin install {PLUGIN_ID}",
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


PLACEHOLDER = re.compile(r"^<YOUR_[A-Z0-9_]+>$")  # e.g. "<YOUR_ANTHROPIC_AUTH_TOKEN>" in config/


def merge(base, ours, path=""):
    """am_plr wins for scalars, dicts merge recursively, lists are unioned. Returns changed keys.

    A placeholder value never replaces an existing one (your real token stays) and never counts as a change.
    """
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
        elif isinstance(v, str) and PLACEHOLDER.match(v):
            base.setdefault(k, v)
        elif base.get(k) != v:
            base[k] = v
            changed.append(key)
    return changed


def placeholders(d, path=""):
    """Keys still holding a <YOUR_...> placeholder."""
    out = []
    for k, v in d.items():
        key = f"{path}.{k}" if path else k
        if isinstance(v, dict):
            out += placeholders(v, key)
        elif isinstance(v, str) and PLACEHOLDER.match(v):
            out.append(key)
    return out


def preview_settings(label, src: Path, dst: Path, out_name: str):
    """config/ blueprint merged over your current settings -> artifacts/generated/<out_name>. Never writes dst.

    Without a current file the blueprint alone is the result. Placeholders (tokens) are left for you to fill in.
    """
    ours = subst(read_jsonc(src)[0])
    current, comments = read_jsonc(dst) if dst.is_file() else ({}, False)
    changed = merge(current, ours)
    out = GEN_DIR / out_name
    if not dst.is_file():
        changed = changed or ["new file"]
    if not changed:
        out.unlink(missing_ok=True)
        info(f"{label}: up to date ({dst})")
        return None
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n")
    out.chmod(0o600)  # contains everything from the current file, incl. any tokens
    print(f"  {Y}~{N} {label}: {', '.join(changed)}")
    if comments:
        warn(f"{label}: {dst} has comments - the generated file drops them, merge by hand to keep them")
    return label, dst, out, placeholders(current)


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
    if not needed:
        return
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
    for label, dst, out, holes in previews:
        if dst.is_file():
            lines = [f"diff {q(str(dst))} {q(str(out))}",
                     f"cp {q(str(dst))} {q(str(dst) + '.bak')} && cp {q(str(out))} {q(str(dst))}"]
        else:
            lines = [f"mkdir -p {q(str(dst.parent))} && cp {q(str(out))} {q(str(dst))}"]
        if holes:
            lines.append(f"then replace the placeholder(s) in {dst}: {', '.join(holes)}")
        title = ("Review and apply {} settings (your keys + am_plr keys, nothing removed)" if dst.is_file()
                 else "Create {} settings from the am_plr blueprint").format(label)
        todo.append((title, lines))


# ----------------------------------------------------------------------------- mcp

def subst(v):
    """Fill ${AM_PLR} / ${HOME}. Token ${VAR}s stay as-is: Claude Code expands them at runtime."""
    if isinstance(v, list):
        return [subst(x) for x in v]
    if isinstance(v, dict):
        return {k: subst(x) for k, x in v.items()}
    if not isinstance(v, str):
        return v
    return v.replace("${AM_PLR}", str(REPO)).replace("${HOME}", str(Path.home()))


def env_refs(server):
    return sorted(set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)", json.dumps(server))))


def build_mcp(mcp_specs):
    """My own [mcp.<name>] blocks in upstreams.toml -> artifacts/generated/mcp.json."""
    servers = {}
    for name, spec in mcp_specs.items():
        spec = dict(spec)
        install = spec.pop("install", None)
        server = {"type": "http" if "url" in spec else "stdio", **subst(spec)}
        cmd = server.get("command", "")
        if cmd.startswith("/") and not Path(cmd).exists():
            warn(f"mcp '{name}': {cmd} does not exist yet ({install or 'install it'})")
        servers[name] = server
        refs = env_refs(server)
        ok(f"mcp '{name}'" + (f" - token(s) from .env: {', '.join(refs)}" if refs else ""))

    GEN_DIR.mkdir(parents=True, exist_ok=True)
    MCP_JSON.write_text(json.dumps({"mcpServers": servers}, indent=2) + "\n")
    return servers


def project_mcp():
    try:
        return json.loads(PROJECT_MCP.read_text()).get("mcpServers") or {}
    except (OSError, json.JSONDecodeError):
        return {}


def check_workspaces():
    """am_plr must be the first folder: Claude Code starts there and loads am_plr/.mcp.json."""
    files = sorted(WORKSPACES.glob("*.code-workspace")) if WORKSPACES.is_dir() else []
    for ws in files:
        try:
            folders = read_jsonc(ws)[0].get("folders") or []
        except (OSError, json.JSONDecodeError) as e:
            warn(f"{ws.name}: unreadable ({e})")
            continue
        first = (ws.parent / folders[0]["path"]).resolve() if folders else None
        if first == REPO:
            info(f"{ws.name}: am_plr is the first folder")
        else:
            warn(f"{ws.name}: first folder is {first}, not am_plr - {PROJECT_MCP.name} won't load")
            todo.append((f"Make am_plr the first folder in {ws.name}", [
                f"Edit {ws}: move the {{\"path\": \"..\"}} entry to the top of \"folders\"."]))


def check_skill_mcp_refs(skill_dirs):
    """MCP servers my skills call (qase, cats-mcp-server, ...) that am_plr/.mcp.json doesn't define."""
    used = set()
    for skill_dir in skill_dirs:
        for f in skill_dir.rglob("*.md"):
            used |= set(re.findall(r"mcp__([A-Za-z0-9_-]+?)__", f.read_text(encoding="utf-8", errors="ignore")))
    return sorted(used - set(project_mcp()))


def mcp_todo(servers, missing):
    """All MCP servers live in am_plr/.mcp.json. Setup only reports what to add there; nothing is written."""
    current = project_mcp()
    info(f"{PROJECT_MCP.name}: {', '.join(current) or 'no servers yet'}")
    strip = lambda s: {k: v for k, v in s.items() if k != "type"}
    todo_names = [n for n in servers if strip(current.get(n, {})) != strip(servers[n])]
    for n in servers:
        print(f"    {n}: " + (f"{Y}to add / update{N}" if n in todo_names else f"{D}in {PROJECT_MCP.name}{N}"))
    if todo_names:
        todo.append((f"Add my MCP servers to {PROJECT_MCP}", [
            f"Copy {', '.join(todo_names)} from {MCP_JSON} into its \"mcpServers\".",
        ]))
    if missing:
        info(f"skills use MCP servers not in {PROJECT_MCP.name}: {', '.join(missing)}")
    lines = [f"Add new servers to {PROJECT_MCP}; my own ones are generated in {MCP_JSON}."]
    if missing:
        lines.append(f"Your am-plr skills still need: {', '.join(missing)}")
    todo.append(("Optional: extend MCP servers", lines))


# ----------------------------------------------------------------------------- main

def main():
    upstreams, mcp_specs = load_config()

    step("Plugin (skills, agents) -> Claude Code")
    remove_old_links()
    check_plugin()
    skill_dirs = [d for d in sorted((REPO / "skills").glob("*")) if (d / "SKILL.md").is_file()]
    info(f"{len(skill_dirs)} skill(s): {', '.join('am-plr:' + d.name for d in skill_dirs)}")

    step(f"Rules -> {CLAUDE_DIR / 'rules' / 'am_plr'}")
    sync_rules()

    step(f"Settings (config/) -> {GEN_DIR}")
    settings_todo(sync_settings())
    check_shell()

    step(f"MCP -> {MCP_JSON}")
    servers = build_mcp(mcp_specs)
    check_secrets(servers)
    check_workspaces()
    mcp_todo(servers, check_skill_mcp_refs(skill_dirs))

    step("Done" + (f" with {len(warnings)} warning(s)" if warnings else ""))
    for w in warnings:
        print(f"  {Y}!{N} {w}")
    order = ("Create .env", "Fill in", "Load tokens", "Install the am-plr", "Make am_plr", "Add my MCP", "Review", "Optional")
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
