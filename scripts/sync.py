"""am_plr sync: links skills/agents/rules into Claude Code and generates MCP config.

Run via scripts/setup.sh (it creates the venv first). Stdlib only, Python 3.11+.

Layering (Claude Code precedence):
  skills/agents  personal (~/.claude, ours) > project (upstream repo) -> a same-named
                 am_plr item would SHADOW upstream. Ours are named am-<name>; on a collision
                 setup asks to rename ours and never links it as-is.
  rules          all levels load together -> linked as one dir ~/.claude/rules/am_plr.
  mcp            local > project (.mcp.json) > user (ours) -> upstream project config
                 always wins; we never write any MCP config, only print commands.
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
CLAUDE_JSON = CLAUDE_DIR / ".claude.json" if os.environ.get("CLAUDE_CONFIG_DIR") else Path.home() / ".claude.json"
VENV_PY = REPO / ".venv" / "bin" / "python"
GEN_DIR = REPO / "artifacts" / "generated"
MCP_JSON = GEN_DIR / "mcp.json"
ENTRYPOINTS = ("server.py", "main.py", "__main__.py")
VSCODE_USER_DIR = next((d for d in (Path.home() / "Library/Application Support/Code/User",  # macOS
                                    Path.home() / ".config/Code/User") if d.is_dir()), None)  # Linux

if sys.stdout.isatty():
    B, G, Y, R, D, N = "\033[1m", "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[0m"
else:
    B = G = Y = R = D = N = ""

warnings = []


def step(msg):
    print(f"\n{B}==> {msg}{N}")


def ok(msg):
    print(f"  {G}+{N} {msg}")


def gone(msg):
    print(f"  {R}-{N} {msg}")


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


def scan_upstream(root: Path):
    """What Claude Code loads from this repo at project scope."""
    skills, agents, mcp = {}, {}, set()
    for d in sorted((root / ".claude" / "skills").glob("*/SKILL.md")):
        skills[frontmatter_name(d) or d.parent.name] = d.parent
        skills.setdefault(d.parent.name, d.parent)
    for f in sorted((root / ".claude" / "agents").glob("*.md")):
        agents[frontmatter_name(f) or f.stem] = f
    try:
        mcp = set(json.loads((root / ".mcp.json").read_text()).get("mcpServers", {}))
    except (OSError, json.JSONDecodeError):
        pass
    return skills, agents, mcp


# ----------------------------------------------------------------------------- linking

PREFIX = "am-"


def ask(question):
    """y/N prompt; False when not interactive (e.g. piped output, CI)."""
    if not sys.stdin.isatty():
        return False
    try:
        return input(f"  {Y}?{N} {question} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def rename_skill(old: str, new: str):
    """skills/<old> -> skills/<new>: moves the dir, sets frontmatter `name:`, fixes references in all skills."""
    src, dst = REPO / "skills" / old, REPO / "skills" / new
    if dst.exists():
        raise FileExistsError(dst)
    tracked = subprocess.run(["git", "-C", str(REPO), "ls-files", "--error-unmatch", str(src)],
                             capture_output=True).returncode == 0
    if tracked:
        subprocess.run(["git", "-C", str(REPO), "mv", str(src), str(dst)], check=True)
    else:
        src.rename(dst)
    skill_md = dst / "SKILL.md"
    skill_md.write_text(re.sub(r"^name:.*$", f"name: {new}", skill_md.read_text(), count=1, flags=re.M))
    o = re.escape(old)
    if re.search(r"[-_]", old):  # distinctive name: replace every whole-token occurrence
        patterns = [rf"(?<![\w-]){o}(?![\w-])"]
    else:  # plain word like "commit": only where it clearly names the skill
        patterns = [rf"(?<=/){o}(?![\w-])", rf"(?<=`){o}(?=` skill)", rf"(?<=the ){o}(?= skill)"]
    for f in (REPO / "skills").rglob("*.md"):
        text = f.read_text()
        fixed = text
        for p in patterns:
            fixed = re.sub(p, new, fixed)
        if fixed != text:
            f.write_text(fixed)


def resolve_collisions(kind, items, upstream_names):
    """Ask to rename our skills that collide with an upstream one (personal scope would hide theirs)."""
    resolved = {}
    for link_name, (src, logical) in sorted(items.items()):
        clash = upstream_names.get(logical) or upstream_names.get(link_name)
        if not clash:
            resolved[link_name] = (src, logical)
            continue
        new = PREFIX + re.sub(r"[_\s]+", "-", link_name.removeprefix(PREFIX))
        warn(f"{kind} '{logical}' collides with upstream {clash}: linking it would hide theirs in every project")
        if kind == "skill" and not (REPO / "skills" / new).exists() and ask(f"Rename ours to '{new}'?"):
            rename_skill(link_name, new)
            ok(f"renamed skill '{link_name}' -> '{new}' (review with `git diff`, then commit)")
            resolved[new] = (REPO / "skills" / new, new)
        else:
            warn(f"{kind} '{logical}' NOT linked - rename it (re-run setup in a terminal to get the prompt)")
    return resolved


def sync_links(kind, items, dst: Path, upstream_names):
    """items: {link_name: (source_path, logical_name)}; links them into dst, prunes ours."""
    dst.mkdir(parents=True, exist_ok=True)
    wanted = {name: src for name, (src, _) in resolve_collisions(kind, items, upstream_names).items()}

    for link_name, src in wanted.items():
        target = dst / link_name
        if target.is_symlink():
            cur = os.readlink(target)
            if Path(cur) == src:
                info(f"{kind} '{link_name}' up to date")
                continue
            target.unlink()
            target.symlink_to(src)
            ok(f"{kind} '{link_name}' relinked (was -> {cur})")
        elif target.exists():
            warn(f"{kind} '{link_name}' NOT linked: {target} exists and is not a symlink "
                 f"(remove it to let am_plr manage it)")
        else:
            target.symlink_to(src)
            ok(f"{kind} '{link_name}' linked")

    # prune: our links (pointing into this repo) that are no longer wanted
    for target in sorted(dst.iterdir()):
        if not target.is_symlink():
            continue
        cur = Path(os.readlink(target))
        if REPO not in cur.parents:
            continue
        if wanted.get(target.name) != cur:
            target.unlink()
            gone(f"{kind} '{target.name}' unlinked (removed/renamed in am_plr or now conflicting)")

    info(f"{len(wanted)} am_plr {kind}(s) active in {dst}")


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
    mdc = sorted(p.relative_to(src) for p in src.rglob("*.mdc"))
    if mdc:
        warn(f"{len(mdc)} .mdc rule(s) are ignored by Claude Code, which loads only *.md "
             f"(frontmatter `paths:` instead of `globs:`/`alwaysApply`): {', '.join(map(str, mdc))}")


# ----------------------------------------------------------------------------- settings

def read_jsonc(path: Path):
    """(data, had_comments). JSONC = JSON + // and /* */ comments + trailing commas."""
    text = path.read_text(encoding="utf-8")
    out, i, in_str, comments = [], 0, False, False
    while i < len(text):
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\":
                out.append(text[i + 1])
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif text.startswith("//", i):
            comments = True
            i = text.find("\n", i)
            i = len(text) if i < 0 else i
            continue
        elif text.startswith("/*", i):
            comments = True
            i = text.index("*/", i) + 2
            continue
        else:
            out.append(c)
        i += 1
    clean = re.sub(r",(\s*[}\]])", r"\1", "".join(out))
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


def load_dotenv():
    """Keys set in am_plr/.env (git-ignored; also exported to the shell by shell/init.zsh)."""
    f = REPO / ".env"
    if not f.is_file():
        return set()
    keys = set()
    for line in f.read_text().splitlines():
        m = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)", line)
        if m and m.group(2).strip().strip("'\""):
            keys.add(m.group(1))
    return keys


def check_secrets(servers):
    """Every ${VAR} used by generated MCP config must be set in .env (or already in the shell env)."""
    env_file, example = REPO / ".env", REPO / ".env.example"
    needed = {v: n for n, s in servers.items() for v in env_refs(s)}
    if not env_file.exists():
        warn(f"{env_file} missing: cp {example} {env_file}  # then fill in tokens")
        return
    have = load_dotenv()
    for var, server in sorted(needed.items()):
        if var not in have and not os.environ.get(var):
            warn(f"{var} (mcp '{server}') is empty in {env_file}")
    if needed and not (set(needed) - have):
        info(f"all {len(needed)} MCP token(s) set in {env_file}")


def check_shell():
    """~/.zshrc is never edited; only report whether it sources am_plr/shell/init.zsh."""
    zshrc, init = Path.home() / ".zshrc", REPO / "shell" / "init.zsh"
    if not init.is_file():
        return None
    text = zshrc.read_text(errors="ignore") if zshrc.is_file() else ""
    if re.search(r"^\s*(source|\.)\s+.*am_plr/shell/init\.zsh", text, re.M):
        info(f"{zshrc} sources {init}")
        return None
    print(f"  {Y}~{N} {zshrc} does not source am_plr shell config yet")
    return f"source {shlex.quote(str(init).replace(str(Path.home()), '~', 1))}"


def print_settings_instructions(previews):
    step("Settings - nothing was applied, copy what you need")
    if not previews:
        print(f"  {G}Claude Code and VS Code user settings are in sync.{N}")
        return
    print("  Each generated file = your current settings + am_plr keys (nothing of yours removed).")
    for label, dst, out in previews:
        q = shlex.quote
        print(f"\n  {B}{label}{N}")
        print(f"    diff {q(str(dst))} {q(str(out))}")
        print(f"    cp {q(str(dst))} {q(str(dst) + '.bak')} && cp {q(str(out))} {q(str(dst))}")


# ----------------------------------------------------------------------------- mcp

def subst(v, root=None):
    """Fill am_plr placeholders. Other ${VAR} (tokens) stay as-is: Claude Code expands them at runtime."""
    if isinstance(v, list):
        return [subst(x, root) for x in v]
    if isinstance(v, dict):
        return {k: subst(x, root) for k, x in v.items()}
    if not isinstance(v, str):
        return v
    v = v.replace("${AM_PLR_PYTHON}", str(VENV_PY)).replace("${AM_PLR}", str(REPO))
    v = v.replace("${HOME}", str(Path.home()))
    return v.replace("${root}", str(root)) if root is not None else v


def env_refs(server):
    return sorted(set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)", json.dumps(server))))


def finalize(server):
    server = {"type": "http" if "url" in server else "stdio", **server}
    if server.get("env") == {}:
        del server["env"]
    return server


def build_mcp(upstreams, upstream_mcp, upstream_project_mcp):
    servers, origin, manual = {}, {}, {}

    for name, spec in upstream_mcp.items():
        spec = dict(spec)
        if not spec.pop("enabled", True):
            info(f"mcp '{name}' disabled in upstreams.toml")
            continue
        src = spec.pop("from", None)
        root = upstreams.get(src)
        if src and (root is None or not root.is_dir()):
            warn(f"mcp '{name}' skipped: upstream '{src}' not found ({root})")
            continue
        if "manual" in spec:
            manual[name] = (src, subst(spec["manual"], root))
            continue
        server = finalize(subst({k: v for k, v in spec.items() if k != "install"}, root))
        cmd = server.get("command", "")
        if cmd.startswith("/") and not Path(cmd).exists():
            hint = spec.get("install") or f"set up the {src} venv, e.g. `uv sync` there"
            warn(f"mcp '{name}': {cmd} does not exist yet ({hint})")
        servers[name], origin[name] = server, f"upstream {src}"

    mcp_dir = REPO / "mcp"
    for d in sorted(p for p in mcp_dir.iterdir() if p.is_dir() and visible(p)) if mcp_dir.is_dir() else []:
        cfg = {}
        if (d / "config.json").is_file():
            try:
                cfg = json.loads((d / "config.json").read_text())
            except json.JSONDecodeError as e:
                warn(f"mcp '{d.name}' skipped: bad config.json ({e})")
                continue
        if cfg.pop("disabled", False):
            info(f"mcp '{d.name}' disabled in config.json")
            continue
        name = cfg.pop("name", d.name)
        if name in servers or name in manual:
            warn(f"mcp '{name}' (am_plr/mcp/{d.name}) skipped: name taken by upstream - rename it")
            continue
        entry = next((d / e for e in ENTRYPOINTS + (f"{d.name}.py",) if (d / e).is_file()), None)
        server = {"command": str(VENV_PY), "args": [str(entry)]} if entry else {}
        server.update(subst(cfg))
        if "command" not in server and "url" not in server:
            warn(f"mcp '{d.name}' skipped: no {'/'.join(ENTRYPOINTS)} and no command/url in config.json")
            continue
        servers[name], origin[name] = finalize(server), "am_plr"
        manual.pop(name, None)

    GEN_DIR.mkdir(parents=True, exist_ok=True)
    MCP_JSON.write_text(json.dumps({"mcpServers": servers}, indent=2) + "\n")
    for n in servers:
        refs = env_refs(servers[n])
        ok(f"mcp '{n}' ({origin[n]})" + (f" - token(s) from .env: {', '.join(refs)}" if refs else ""))
    for n, (src, _) in manual.items():
        info(f"mcp '{n}' (upstream {src}) needs manual setup, see below")
    for n in servers:
        for repo_name, names in upstream_project_mcp.items():
            if n in names:
                info(f"mcp '{n}': {repo_name}/.mcp.json also defines it - that one wins inside {repo_name}")
    return servers, manual


def check_skill_mcp_refs(servers, manual, extra_dirs):
    """Warn when skills call mcp__<server>__ that no config provides."""
    known = set(servers) | set(manual)
    try:
        cur = json.loads(CLAUDE_JSON.read_text())
        known |= set(cur.get("mcpServers") or {})
    except (OSError, json.JSONDecodeError):
        pass
    for skill_dir in extra_dirs:
        refs = set()
        for f in skill_dir.rglob("*.md"):
            refs |= set(re.findall(r"mcp__([A-Za-z0-9_-]+?)__", f.read_text(encoding="utf-8", errors="ignore")))
        for r in sorted(refs - known):
            close = [k for k in known if r in k or k in r]
            hint = f" (did you mean '{close[0]}'?)" if close else ""
            warn(f"skill '{skill_dir.name}' calls mcp__{r}__* but no MCP server '{r}' is configured{hint}")


def print_mcp_instructions(servers, manual):
    try:
        current = json.loads(CLAUDE_JSON.read_text()).get("mcpServers") or {}
    except (OSError, json.JSONDecodeError):
        current = {}

    strip = lambda s: {k: v for k, v in s.items() if k != "type"}
    new = [n for n in servers if n not in current]
    changed = [n for n in servers if n in current and strip(current[n]) != strip(servers[n])]
    same = [n for n in servers if n in current and n not in changed]
    stale = [n for n, s in current.items() if n not in servers and str(REPO) in json.dumps(s)]
    manual_todo = {n: m for n, m in manual.items() if n not in current}

    step("MCP setup - nothing was applied, copy what you need")
    if not servers and not manual:
        info("no MCP servers configured")
        return
    print(f"  Compared with user scope in {CLAUDE_JSON}:")
    for n in same:
        info(f"= {n} (already configured)")
    for n in new:
        print(f"    {G}+ {n} (new){N}")
    for n in changed:
        print(f"    {Y}~ {n} (differs){N}")
    for n in stale:
        print(f"    {R}- {n} (no longer provided by am_plr){N}")
    for n in manual_todo:
        print(f"    {Y}? {n} (manual){N}")

    if new or changed or stale:
        # values are read from the generated file, so tokens never land in chat/terminal history
        print(f"\n  {B}Claude Code, all projects (user scope){N} - run in a terminal:\n")
        for n in changed + stale:
            print(f"    claude mcp remove --scope user {shlex.quote(n)}")
        for n in new + changed:
            print(f"    claude mcp add-json --scope user {shlex.quote(n)} "
                  f"\"$(jq -c '.mcpServers[\"{n}\"]' {shlex.quote(str(MCP_JSON))})\"")
    else:
        print(f"\n  {G}User-scope MCP config is in sync.{N}")

    for n, (src, text) in manual_todo.items():
        print(f"\n  {B}{n}{N} (manual, from {src}):")
        for line in text.strip().splitlines():
            print(f"    {line}")

    print(f"""
  {B}Other options{N}
    - one session:    claude --mcp-config {MCP_JSON}
    - one project:    copy entries from {MCP_JSON} into <project>/.mcp.json
  Then restart Claude Code or check with /mcp.""")


# ----------------------------------------------------------------------------- main

def main():
    upstreams, upstream_mcp = load_config()

    step("Upstream repos (upstreams.toml)")
    up_skills, up_agents, up_mcp = {}, {}, {}
    for name, root in upstreams.items():
        if not root.is_dir():
            warn(f"upstream '{name}': {root} not found - its MCP servers are skipped")
            continue
        s, a, m = scan_upstream(root)
        for k in s:
            up_skills.setdefault(k, f"{name}/.claude/skills")
        for k in a:
            up_agents.setdefault(k, f"{name}/.claude/agents")
        up_mcp[name] = m
        ok(f"{name}: {root} ({len(set(p for p in s.values()))} skills, {len(a)} agents"
           f"{f', .mcp.json: {len(m)} servers' if m else ''})")

    skills = {}
    for d in sorted((REPO / "skills").iterdir()) if (REPO / "skills").is_dir() else []:
        if not d.is_dir() or not visible(d):
            continue
        if not (d / "SKILL.md").is_file():
            warn(f"skill '{d.name}' skipped: no SKILL.md")
            continue
        skills[d.name] = (d, frontmatter_name(d / "SKILL.md") or d.name)
        if not d.name.startswith(PREFIX):
            warn(f"skill '{d.name}' has no '{PREFIX}' prefix - our skills are named {PREFIX}<name> "
                 f"to never collide with upstream ones")
    step(f"Skills -> {CLAUDE_DIR / 'skills'}")
    sync_links("skill", skills, CLAUDE_DIR / "skills", up_skills)

    agents = {}
    for f in sorted((REPO / "agents").glob("*.md")) if (REPO / "agents").is_dir() else []:
        if visible(f) and f.name != "README.md":
            agents[f.name] = (f, frontmatter_name(f) or f.stem)
    step(f"Agents -> {CLAUDE_DIR / 'agents'}")
    sync_links("agent", agents, CLAUDE_DIR / "agents", up_agents)

    step(f"Rules -> {CLAUDE_DIR / 'rules' / 'am_plr'}")
    sync_rules()

    step(f"Settings (config/) -> {GEN_DIR}")
    previews = sync_settings()
    shell_line = check_shell()

    step(f"MCP -> {MCP_JSON}")
    servers, manual = build_mcp(upstreams, upstream_mcp, up_mcp)
    check_secrets(servers)
    check_skill_mcp_refs(servers, manual, [src for src, _ in skills.values()])

    print_mcp_instructions(servers, manual)

    print_settings_instructions(previews)
    if shell_line:
        step("Shell - nothing was applied")
        print(f"  Add to the end of ~/.zshrc (then open a new terminal):\n")
        print(f"    {shell_line}")

    step("Done" + (f" with {len(warnings)} warning(s)" if warnings else ""))
    for w in warnings:
        print(f"  {Y}!{N} {w}")
    info("SKILL.md/rule edits are live. Re-run after adding/renaming/deleting skills or agents,")
    info("editing config/ mcp/ upstreams.toml, or pulling upstream repos.")


if __name__ == "__main__":
    main()
