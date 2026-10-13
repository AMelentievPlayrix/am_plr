"""am_plr sync: checks the am plugin, links rules, generates .mcp.json and settings previews.

Run via scripts/setup.sh (it creates the venv first). Stdlib only, Python 3.11+.
The Windows twin is scripts/sync_win.py - update both when the repo layout changes.

Layering:
  skills/agents  shipped as the Claude Code plugin "am" (this repo): namespaced as
                 am:<skill>, so they never collide with upstream project skills.
  rules          plugins can't ship rules -> linked as one dir ~/.claude/rules/am_plr.
  mcp            every server in upstreams.toml [mcp.*] -> generated am_plr/.mcp.json with this
                 machine's paths and the tokens from mcp/.env. Both files are git-ignored.
"""

import json
import os
import re
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
GEN_DIR = REPO / "artifacts" / "generated"
PROJECT_MCP = REPO / ".mcp.json"  # generated; loaded by Claude Code when am_plr is the first workspace folder
MCP_ENV = REPO / "mcp" / ".env"  # tokens, git-ignored (template: mcp/.env.example)
MCP_ENV_EXAMPLE = REPO / "mcp" / ".env.example"
LEGACY_ENV = REPO / ".env"  # pre-mcp/.env location, still read as a fallback
VENV_PYTHON = REPO / ".venv" / "bin" / "python"
UV = os.environ.get("AM_PLR_UV") or "uv"
WORKSPACES = REPO / "workspaces"
VSCODE_USER_DIR = next((d for d in (Path.home() / "Library/Application Support/Code/User",  # macOS
                                    Path.home() / ".config/Code/User") if d.is_dir()), None)  # Linux

if sys.stdout.isatty():
    B, G, Y, R, D, N = "\033[1m", "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[0m"
else:
    B = G = Y = R = D = N = ""

PLUGIN_ID = "am@am-plr"
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
    cfg = tomllib.loads(cfg_file.read_text(encoding="utf-8"))
    upstreams = {}
    for name, u in cfg.get("upstream", {}).items():
        p = Path(os.path.expanduser(u["path"]))
        upstreams[name] = (p if p.is_absolute() else REPO / p).resolve()
    return upstreams, cfg.get("mcp", {})


def check_plugin():
    """Skills/agents come from the am plugin; setup only checks it is installed and enabled."""
    try:
        settings = json.loads((CLAUDE_DIR / "settings.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        settings = {}
    if (settings.get("enabledPlugins") or {}).get(PLUGIN_ID):
        info(f"plugin {PLUGIN_ID} enabled - skills load from {REPO}/skills")
        return
    print(f"  {Y}~{N} plugin {PLUGIN_ID} not installed yet")
    todo.append(("Install the am plugin (once per machine) - in Claude Code, run:", [
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

    # Two passes: comments first, so a trailing comma followed by a comment (`"x",  // note`) is seen as trailing.
    clean = re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/', drop, text, flags=re.S)
    clean = re.sub(r'"(?:\\.|[^"\\])*"|,(?=\s*[}\]])', drop, clean)
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


def preview_settings(label, src: Path, dst: Path, out_name: str, upstreams):
    """config/ blueprint merged over your current settings -> artifacts/generated/<out_name>. Never writes dst.

    Without a current file the blueprint alone is the result. Placeholders (tokens) are left for you to fill in.
    """
    ours = subst(read_jsonc(src)[0], upstreams)
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
    out.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    out.chmod(0o600)  # contains everything from the current file, incl. any tokens
    print(f"  {Y}~{N} {label}: {', '.join(changed)}")
    if comments:
        warn(f"{label}: {dst} has comments - the generated file drops them, merge by hand to keep them")
    return label, dst, out, placeholders(current)


def sync_settings(upstreams):
    """Common settings only; project-specific settings stay in the projects themselves."""
    previews = []
    claude_src = REPO / "config" / "claude" / "settings.json"
    if claude_src.is_file():
        previews.append(preview_settings("Claude Code", claude_src, CLAUDE_DIR / "settings.json",
                                         "claude-settings.json", upstreams))
    vscode_src = REPO / "config" / "vscode" / "settings.json"
    if vscode_src.is_file():
        if VSCODE_USER_DIR:
            previews.append(preview_settings("VS Code", vscode_src, VSCODE_USER_DIR / "settings.json",
                                             "vscode-settings.json", upstreams))
        else:
            warn("VS Code user settings dir not found - is VS Code installed?")
    return [p for p in previews if p]


def check_tokens(unset):
    """Credentials come from mcp/.env and are written literally into the generated .mcp.json."""
    if not MCP_ENV.is_file():
        info(f"{MCP_ENV} missing - every server falls back to its own repo .env")
        todo.append(("Create mcp/.env with your tokens (git-ignored)", [
            f"cp {shlex.quote(str(MCP_ENV_EXAMPLE))} {shlex.quote(str(MCP_ENV))}  # then fill it in"]))
    for name, names in unset.items():
        warn(f"mcp '{name}': {', '.join(names)} not set in {MCP_ENV} - omitted from {PROJECT_MCP.name}")
    if unset:
        todo.append((f"Fill in the missing token(s) in {MCP_ENV}, then re-run setup",
                     sorted({v for vs in unset.values() for v in vs})))
    elif MCP_ENV.is_file():
        info(f"all MCP token(s) resolved from {MCP_ENV}")


def check_shell():
    """~/.zshrc is never edited; only report whether it sources am_plr/shell/init.zsh.

    Tokens no longer travel through the shell (they are written into .mcp.json), so this is
    only about aliases and the prompt.
    """
    zshrc, init = Path.home() / ".zshrc", REPO / "shell" / "init.zsh"
    text = zshrc.read_text(encoding="utf-8", errors="ignore") if zshrc.is_file() else ""
    if re.search(r"^\s*(source|\.)\s+.*am_plr/shell/init\.zsh", text, re.M):
        info(f"{zshrc} sources {init}")
        return
    print(f"  {Y}~{N} {zshrc} does not source am_plr shell config yet")
    line = f"source {str(init).replace(str(Path.home()), '~', 1)}"
    todo.append(("Load the am_plr aliases and prompt in every terminal", [
        f"echo {shlex.quote(line)} >> ~/.zshrc   # then open a new terminal"]))


def ensure_venv():
    """uv sync -> .venv. The generated .mcp.json runs every server on its python, so this comes first."""
    existed = VENV_PYTHON.exists()
    r = subprocess.run([UV, "sync", "--project", str(REPO)], capture_output=True, text=True, errors="replace")
    if r.returncode:
        warn(f"uv sync failed (rc={r.returncode}) - MCP servers will not start")
        for line in (r.stderr or r.stdout).strip().splitlines()[-4:]:
            info(line)
        todo.append(("Create the MCP venv by hand (needs the VPN: ci-tc comes from the internal index)", [
            f"cd {shlex.quote(str(REPO))} && {UV} sync"]))
        return
    for line in (r.stderr or "").strip().splitlines()[-3:]:  # uv's "Resolved N / Installed N" summary
        info(line)
    ok(f"{'.venv up to date' if existed else 'created .venv'}: {VENV_PYTHON}")


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

PATH_PLACEHOLDER = re.compile(r"\$\{(AM_PLR|HOME|VENV_PYTHON|upstream\.[A-Za-z0-9._-]+)\}")


def subst(v, upstreams=None):
    """Fill the path placeholders. Credential ${VAR}s are left to resolve_tokens()."""
    if isinstance(v, list):
        return [subst(x, upstreams) for x in v]
    if isinstance(v, dict):
        return {k: subst(x, upstreams) for k, x in v.items()}
    if not isinstance(v, str):
        return v
    roots = {"AM_PLR": str(REPO), "HOME": str(Path.home()), "VENV_PYTHON": str(VENV_PYTHON),
             **{f"upstream.{n}": str(p) for n, p in (upstreams or {}).items()}}

    def rep(m):
        key = m.group(1)
        if key not in roots:
            warn(f"unknown placeholder ${{{key}}} in upstreams.toml")
            return m.group(0)
        return roots[key]

    return PATH_PLACEHOLDER.sub(rep, v)


def load_env_file():
    """mcp/.env over the legacy root .env. Tiny parser on purpose: sync runs on a bare interpreter, no deps."""
    values = {}
    for f in (LEGACY_ENV, MCP_ENV):  # mcp/.env parsed last, so it wins
        if not f.is_file():
            continue
        for raw in f.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.removeprefix("export ").partition("=")
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            else:  # unquoted: a trailing ` # comment` is not part of the value (same as python-dotenv)
                v = re.split(r"\s+#", v, maxsplit=1)[0].rstrip()
            values[k.strip()] = v
    return values


TOKEN_REF = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)(\?)?\}$")  # trailing ? = optional override


def resolve_tokens(server, env_values):
    """Replace a whole-value ${VAR} in the env block with its literal value; drop the key when unset.

    Dropping (rather than leaving "${VAR}") is what lets each server fall back to its own repo .env:
    python-dotenv does not override a variable already in the environment, so an injected value wins,
    and an absent one leaves the server's own load_dotenv in charge.
    A ${VAR?} is an optional override: unset is the normal case, so it is reported, not warned about.
    Returns (server, [required but unset], [vars taken from mcp/.env], [optional and unset]).
    """
    block = server.get("env")
    if not isinstance(block, dict):
        return server, [], [], []
    out, missing, filled, optional = {}, [], [], []
    for k, v in block.items():
        m = TOKEN_REF.match(v) if isinstance(v, str) else None
        if not m:
            out[k] = v
            continue
        name = m.group(1)
        # Only mcp/.env (and the legacy root .env) decide this - deliberately NOT os.environ, so
        # emptying a token here drops it from the config instead of silently reusing a stale export.
        value = env_values.get(name)
        if value:
            out[k] = value
            filled.append(name)
        elif m.group(2):
            optional.append(name)
        else:
            missing.append(name)
    server = dict(server)
    if out:
        server["env"] = out
    else:
        server.pop("env", None)
    return server, missing, filled, optional


def project_mcp():
    try:
        return json.loads(PROJECT_MCP.read_text(encoding="utf-8")).get("mcpServers") or {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_project_mcp(mcp_specs, upstreams):
    """upstreams.toml [mcp.*] -> .mcp.json for this machine. Generated + git-ignored: it holds real tokens."""
    env_values = load_env_file()
    servers, unset, fallbacks = {}, {}, {}
    for name, spec in mcp_specs.items():
        spec = dict(spec)
        install = spec.pop("install", None)
        server = {"type": "http" if "url" in spec else "stdio", **subst(spec, upstreams)}
        server, missing, filled, optional = resolve_tokens(server, env_values)
        if optional:
            fallbacks[name] = optional
        if "command" in server:
            for p in [server["command"], *server.get("args", [])]:
                if Path(p).is_absolute() and not Path(p).exists():
                    warn(f"mcp '{name}': {p} does not exist ({install or 'pull the repo / run uv sync'})")
        servers[name] = server
        if missing:
            unset[name] = missing
        ok(f"mcp '{name}'" + (f" - token(s) from {MCP_ENV.name}: {', '.join(filled)}" if filled else ""))

    before = project_mcp()
    extra = {n: s for n, s in before.items() if n not in servers}
    for n, s in extra.items():  # .mcp.json is git-ignored: a hand-added server has no other copy
        warn(f"mcp '{n}': in {PROJECT_MCP.name} but not in upstreams.toml - kept; add it there to make it permanent")
        servers[n] = s
    PROJECT_MCP.write_text(json.dumps({"mcpServers": servers}, indent=2) + "\n", encoding="utf-8", newline="\n")
    PROJECT_MCP.chmod(0o600)  # holds real tokens
    if before == servers:
        info(f"{PROJECT_MCP.name}: unchanged ({len(servers)} server(s))")
    else:
        ok(f"{PROJECT_MCP.name}: {len(servers)} server(s) written - {', '.join(servers)}")
        todo.append(("Restart Claude Code so it picks up the new MCP config", [
            "VS Code: Developer: Reload Window, then /mcp (approve the project servers if asked)."]))
    for name, names in fallbacks.items():
        info(f"mcp '{name}': {', '.join(names)} not overridden - the server reads its own .env")
    return servers, unset


def check_workspaces():
    """am_plr must be the first folder: Claude Code starts there and loads am_plr/.mcp.json."""
    files = sorted(WORKSPACES.glob("*.code-workspace")) if WORKSPACES.is_dir() else []
    for ws in files:
        try:
            folders = read_jsonc(ws)[0].get("folders") or []
            first = (ws.parent / folders[0]["path"]).resolve() if folders else None
        except (OSError, json.JSONDecodeError, KeyError, IndexError) as e:
            warn(f"{ws.name}: unreadable ({e})")
            continue
        if first == REPO:
            info(f"{ws.name}: am_plr is the first folder")
        else:
            warn(f"{ws.name}: first folder is {first}, not am_plr - {PROJECT_MCP.name} won't load")
            todo.append((f"Make am_plr the first folder in {ws.name}", [
                f"Edit {ws}: move the {{\"path\": \"..\"}} entry to the top of \"folders\"."]))


def check_skill_mcp_refs(skill_dirs, servers):
    """MCP servers my skills call (qase, cats-mcp-server, ...) that upstreams.toml doesn't define."""
    used = set()
    for skill_dir in skill_dirs:
        for f in skill_dir.rglob("*.md"):
            used |= set(re.findall(r"mcp__([A-Za-z0-9_-]+?)__", f.read_text(encoding="utf-8", errors="ignore")))
    missing = sorted(used - set(servers))
    if missing:
        warn(f"skills use MCP servers not in upstreams.toml: {', '.join(missing)}")


# ----------------------------------------------------------------------------- main

def main():
    upstreams, mcp_specs = load_config()

    step("Plugin (skills, agents) -> Claude Code")
    remove_old_links()
    check_plugin()
    skill_dirs = [d for d in sorted((REPO / "skills").glob("*")) if (d / "SKILL.md").is_file()]
    info(f"{len(skill_dirs)} skill(s): {', '.join('am:' + d.name for d in skill_dirs)}")

    step(f"Rules -> {CLAUDE_DIR / 'rules' / 'am_plr'}")
    sync_rules()

    step(f"Settings (config/) -> {GEN_DIR}")
    settings_todo(sync_settings(upstreams))
    check_shell()

    step(f"Python env -> {REPO / '.venv'}")
    ensure_venv()  # before the MCP step: .mcp.json points every server at this venv's python

    step(f"MCP -> {PROJECT_MCP}")
    servers, unset = write_project_mcp(mcp_specs, upstreams)
    check_tokens(unset)
    check_workspaces()
    check_skill_mcp_refs(skill_dirs, servers)

    step("Done" + (f" with {len(warnings)} warning(s)" if warnings else ""))
    for w in warnings:
        print(f"  {Y}!{N} {w}")
    order = ("Create mcp", "Fill in", "Install the am", "Make am_plr", "Create the MCP venv", "Load the am_plr",
             "Review", "Restart")
    todo.sort(key=lambda t: next((i for i, p in enumerate(order) if t[0].startswith(p)), len(order)))
    if todo:
        print(f"\n{B}Next steps{N} - setup wrote only .venv, .mcp.json and the rules link; run these yourself:")
        for i, (title, lines) in enumerate(todo, 1):
            print(f"\n  {B}{i}. {title}{N}")
            for line in lines:
                print(f"     {line}")
        print(f"\n  {B}{len(todo) + 1}. Restart Claude Code{N} (VS Code: Developer: Reload Window), then check /plugin, /mcp, /skills.")
    else:
        print(f"\n  {G}All set.{N} Skill/rule edits are live (/reload-plugins in an open session).")
    info("Re-run setup after editing config/, upstreams.toml, mcp/.env, or pulling upstream repos.")


if __name__ == "__main__":
    main()
