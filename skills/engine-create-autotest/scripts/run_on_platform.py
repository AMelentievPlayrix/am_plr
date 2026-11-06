"""Run a command for one platform of vso-engine-autotests without editing or printing `.env`.

The `# App config` part of `.env` keeps one block per platform under a header line, `# mac` for the active one and
`# # ios` for a commented-out one, each holding `KEY=value` lines (commented or not). This script reads the chosen
block in-process and runs the command with those keys in its environment. The repo loads `.env` with
`load_dotenv()` without override (`config/config_base.py`), so process env wins over the file, and `.env` itself is
never changed, restored or shown.

Prints only the platform and key names (to stderr), never values. Blocks hold credentials, so never print them by
other means either.

    run_on_platform.py ios -- make ai-run-tests key=test_16958 platform_to_run=iOS
    run_on_platform.py android --set BROWSERSTACK_DEVICES_TO_RUN=110 -- make ai-run-tests key=... platform_to_run=...
    run_on_platform.py mac --env-file <main repo>/.env -- make ai-run-tests ...   # from a worktree

Keys that only another platform's block sets are not cleared: the active block still loads through `.env`.
"""

import argparse
import io
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Final

from dotenv import dotenv_values

# Header names used in the App config part of vso-engine-autotests .env / .env_example.
PLATFORM_HEADERS: Final = (
    "android",
    "android_on_linux",
    "ios",
    "ios_on_linux",
    "windows",
    "uwp",
    "mac",
    "emscripten",
    "facebook",
)
HEADER_RE: Final = re.compile(r"^#(?: #)? (" + "|".join(PLATFORM_HEADERS) + r")\s*$")
KEY_LINE_RE: Final = re.compile(r"^(?:# )?([A-Z][A-Z0-9_]*=.*)$")
KEY_NAME_RE: Final = re.compile(r"^[A-Z][A-Z0-9_]*$")
SECTION_RULE: Final = "####"
EXIT_USAGE: Final = 2


class EnvBlockError(Exception):
    """The .env file has no usable block for the requested platform."""


def read_platform_blocks(env_text: str) -> dict[str, dict[str, str]]:
    """Map each platform header to the keys of its block.

    A block runs from its header to the next blank line, section rule or header. Headers with no key lines (the
    "Available platforms" list) are skipped. Two blocks with keys for one platform are ambiguous and rejected.
    """
    blocks: dict[str, dict[str, str]] = {}
    current: str | None = None
    lines: list[str] = []

    def close_block() -> None:
        if current is None or not lines:
            return
        if current in blocks:
            raise EnvBlockError(f"two '{current}' blocks with keys in the env file")
        parsed = dotenv_values(stream=io.StringIO("\n".join(lines)))
        blocks[current] = {key: value or "" for key, value in parsed.items()}

    for raw in env_text.splitlines():
        stripped = raw.strip()
        header = HEADER_RE.match(stripped)
        if header or not stripped or stripped.startswith(SECTION_RULE):
            close_block()
            current, lines = (header.group(1) if header else None), []
            continue
        key_line = KEY_LINE_RE.match(stripped)
        if current is not None and key_line:
            lines.append(key_line.group(1))
    close_block()
    return blocks


def parse_overrides(pairs: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not KEY_NAME_RE.match(key):
            raise ValueError(f"--set expects KEY=VALUE with an upper-case key, got '{pair.split('=')[0]}=...'")
        overrides[key] = value
    return overrides


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a command with one platform block of .env as process env (values never printed).",
    )
    parser.add_argument("platform", help=f"block header: {', '.join(PLATFORM_HEADERS)}")
    parser.add_argument("--env-file", type=Path, default=Path(".env"), help="default: ./.env")
    parser.add_argument("--set", dest="overrides", action="append", default=[], metavar="KEY=VALUE")
    parser.epilog = "Put the command after a literal --."
    return parser


def split_command(argv: list[str]) -> tuple[list[str], list[str]]:
    """Split at the first `--`: script options before it, the command to run after it."""
    if "--" not in argv:
        return argv, []
    index = argv.index("--")
    return argv[:index], argv[index + 1 :]


def main() -> int:
    own_args, command = split_command(sys.argv[1:])
    args = build_parser().parse_args(own_args)
    if not command:
        print("run_on_platform: no command given after --", file=sys.stderr)
        return EXIT_USAGE
    if not args.env_file.is_file():
        print(f"run_on_platform: env file not found: {args.env_file}", file=sys.stderr)
        return EXIT_USAGE
    try:
        overrides = parse_overrides(args.overrides)
        blocks = read_platform_blocks(args.env_file.read_text(encoding="utf-8"))
        if args.platform not in blocks:
            raise EnvBlockError(f"no '{args.platform}' block with keys; blocks found: {', '.join(blocks) or 'none'}")
    except (ValueError, EnvBlockError) as error:
        print(f"run_on_platform: {error}", file=sys.stderr)
        return EXIT_USAGE

    block = blocks[args.platform]
    print(
        f"run_on_platform: {args.platform} block -> {', '.join(block)}"
        + (f"; overrides: {', '.join(overrides)}" if overrides else "")
        + " (values hidden)",
        file=sys.stderr,
    )
    env = os.environ | block | overrides
    return subprocess.run(command, env=env, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
