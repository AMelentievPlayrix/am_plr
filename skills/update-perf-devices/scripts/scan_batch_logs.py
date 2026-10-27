"""Print the lines that matter from the batch logs of a BrowserStack perf build, with credentials masked.

Reads batch_logs/*.log straight from test_artifacts.zip (nothing is extracted) and prints, per batch, the
capabilities the SDK was started with (deviceName, osVersion, deviceOrientation, appiumVersion) and the lines
matching known failure and success markers. The batch logs carry the BrowserStack accessKey in plain text
inside that config, so every printed line is masked first; quote only this script's output, never the raw log.
"""

import argparse
import os
import re
import zipfile
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Final

BATCH_LOG: Final = re.compile(r"^batch_logs/[^/]+\.log$")
MARKERS: Final = (
    "BROWSERSTACK_",
    "error code",
    "NOT SUPPORTED",
    "Driver created successfully",
    "Unknown mobile command",
    "fchown",
    "Unable To Rotate",
    "timed out after",
    "All done",
)
SESSION_REQUEST: Final = "Parsed config file"
CAPABILITIES: Final = ("deviceName", "osVersion", "deviceOrientation", "appiumVersion")
SECRET_PATTERNS: Final = (
    re.compile(
        r"""(['"]?(?:accessKey|access_key|userName|username|BROWSERSTACK_ACCESS_KEY|BROWSERSTACK_USERNAME)"""
        r"""['"]?\s*[:=]\s*['"]?)[^'",\s}]+"""
    ),
    # https://user:key@hub-cloud.browserstack.com/...
    re.compile(r"(://)[^/\s:@]+:[^/\s@]+@"),
)
SECRET_ENV: Final = ("BROWSERSTACK_USERNAME", "BROWSERSTACK_ACCESS_KEY")
MAX_LINE: Final = 400
MASK: Final = "<redacted>"


def mask(line: str) -> str:
    for name in SECRET_ENV:
        if value := os.environ.get(name):
            line = line.replace(value, MASK)
    line = SECRET_PATTERNS[0].sub(rf"\1{MASK}", line)
    line = SECRET_PATTERNS[1].sub(rf"\1{MASK}@", line)
    return line if len(line) <= MAX_LINE else f"{line[:MAX_LINE]} ...[cut]"


def session_capabilities(line: str) -> tuple[tuple[str, str], ...]:
    found = []
    for name in CAPABILITIES:
        if match := re.search(rf"""['"]{name}['"]\s*:\s*['"]?([^'",}}]+)""", line):
            found.append((name, match.group(1).strip()))
    return tuple(found)


def scan(text: str, patterns: Sequence[re.Pattern[str]], after: int) -> None:
    lines = text.splitlines()
    requests: Counter[tuple[tuple[str, str], ...]] = Counter()
    hits: Counter[str] = Counter()
    for index, line in enumerate(lines):
        if SESSION_REQUEST in line and (capabilities := session_capabilities(line)):
            requests[capabilities] += 1
        if any(pattern.search(line) for pattern in patterns):
            block = [mask(line), *(f"    | {mask(next_line)}" for next_line in lines[index + 1 : index + 1 + after])]
            hits["\n".join(block)] += 1
    for capabilities, count in requests.items():
        print(f"  requested x{count}: " + ", ".join(f"{name}={value}" for name, value in capabilities))
    for block, count in hits.items():
        print(f"  [x{count}] {block}")
    if not requests and not hits:
        print("  no matching lines")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("zip", type=Path, help="test_artifacts.zip of a *_Test_Benchmark_BrowserStack build")
    parser.add_argument("--grep", action="append", default=[], help="extra regex to match (repeatable)")
    parser.add_argument("--only-grep", action="store_true", help="match only --grep, not the built-in markers")
    parser.add_argument("--after", type=int, default=0, help="lines to print after each match")
    args = parser.parse_args()
    if args.only_grep and not args.grep:
        parser.error("--only-grep needs --grep")

    sources = list(args.grep) if args.only_grep else [*map(re.escape, MARKERS), *args.grep]
    patterns = [re.compile(source) for source in sources]
    with zipfile.ZipFile(args.zip) as archive:
        logs = sorted(name for name in archive.namelist() if BATCH_LOG.match(name))
        if not logs:
            raise SystemExit(f"No batch_logs/*.log in {args.zip}")
        for name in logs:
            print(f"== {name}")
            scan(archive.read(name).decode("utf-8", errors="replace"), patterns, args.after)


if __name__ == "__main__":
    main()
