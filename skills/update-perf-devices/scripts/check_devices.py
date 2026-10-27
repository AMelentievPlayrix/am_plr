"""Compare the BrowserStack perf device lists with what the farm offers.

Two sources: devices.json from the App Automate API (what CapabilitiesCheck asks) and the public device list
(BrowserStack drops a device from it first when retiring it, while devices.json may still return it).

- `check` prints the status of every device in devices_*.yml at the given git refs of perfect-project, and of
  devices given with --device (replacement candidates).
- `list` prints every phone and tablet of one platform on the public list, with the OS versions devices.json
  has for it, for picking a replacement.

Credentials come only from BROWSERSTACK_USERNAME / BROWSERSTACK_ACCESS_KEY and are never printed. Without
them devices.json is skipped and the output says so.
"""

import argparse
import os
import subprocess
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Final

import httpx
import yaml

AM_PLR: Final = Path(__file__).resolve().parents[3]
DEFAULT_REPO: Final = AM_PLR.parent / "perfect-project"
PLATFORMS: Final = ("android", "ios")
DEVICES_YML: Final = {
    "android": "ci/bs_performance/configurations/devices_android.yml",
    "ios": "ci/bs_performance/configurations/devices_ios.yml",
}
DEVICES_JSON_URL: Final = "https://api-cloud.browserstack.com/app-automate/devices.json"
PUBLIC_LIST_URL: Final = "https://www.browserstack.com/list-of-browsers-and-platforms/app_automate"
HTTP_TIMEOUT: Final = 30.0
# The page serves a reduced layout without a browser User-Agent.
BROWSER_HEADERS: Final = {"User-Agent": "Mozilla/5.0"}
# Groups on the public page, by their aria-label. Android names there drop the brand ("Galaxy S25" under
# "Samsung mobile devices"); devices.json and the YAML use the full name ("Samsung Galaxy S25").
APPLE_GROUPS: Final = {"iPhone devices": "phone", "iPad devices": "tablet"}
ANDROID_GROUP_SUFFIXES: Final = {" mobile devices": "phone", " tablet devices": "tablet"}
# A long group is split into columns: "iPhone devices", then "iPhone devices (continued)".
CONTINUED_SUFFIX: Final = " (continued)"
NOT_CHECKED: Final = "not checked"

# (platform, device name) -> OS versions as strings, compared the way is_device_supported compares them.
Versions = Mapping[tuple[str, str], set[str]]


@dataclass(frozen=True, slots=True)
class Device:
    platform: str
    name: str
    os_version: str


@dataclass(frozen=True, slots=True)
class PublicDevice:
    platform: str
    kind: str
    name: str
    os_version: str


class _PublicListParser(HTMLParser):
    """Collects (group label, device name, OS version) from the desktop layout of the public list."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[tuple[str, str, str]] = []
        self._group = ""
        self._field: str | None = None
        self._text: list[str] = []
        self._name = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = (dict(attrs).get("class") or "").split()
        if "device-listing__list-container" in classes:
            self._group = (dict(attrs).get("aria-label") or "").removesuffix(CONTINUED_SUFFIX)
        elif tag == "div" and "device-listing__device-name" in classes:
            self._field, self._text = "name", []
        elif tag == "div" and "device-listing__device-os" in classes:
            self._field, self._text = "os", []

    def handle_endtag(self, tag: str) -> None:
        # Only spans and svg sit inside these divs, so the first closing div ends the field.
        if tag != "div" or self._field is None:
            return
        value = " ".join("".join(self._text).split())
        if self._field == "name":
            self._name = value
        elif self._name:
            self.rows.append((self._group, self._name, value))
            self._name = ""
        self._field = None

    def handle_data(self, data: str) -> None:
        if self._field is not None:
            self._text.append(data)


def fetch_public_list() -> list[PublicDevice]:
    response = httpx.get(PUBLIC_LIST_URL, headers=BROWSER_HEADERS, follow_redirects=True, timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    parser = _PublicListParser()
    parser.feed(response.text)
    devices = [device for row in parser.rows if (device := _to_public_device(*row)) is not None]
    for platform in PLATFORMS:
        if not any(device.platform == platform for device in devices):
            raise RuntimeError(f"No {platform} devices parsed from {PUBLIC_LIST_URL}: the page layout has changed")
    return devices


def _to_public_device(group: str, name: str, os_version: str) -> PublicDevice | None:
    if group in APPLE_GROUPS:
        return PublicDevice("ios", APPLE_GROUPS[group], name, os_version)
    for suffix, kind in ANDROID_GROUP_SUFFIXES.items():
        if group.endswith(suffix):
            return PublicDevice("android", kind, f"{group.removesuffix(suffix)} {name}", os_version)
    return None  # TV and other non-mobile groups


def fetch_devices_json() -> Versions | None:
    username = os.environ.get("BROWSERSTACK_USERNAME")
    access_key = os.environ.get("BROWSERSTACK_ACCESS_KEY")
    if not username or not access_key:
        return None
    response = httpx.get(DEVICES_JSON_URL, auth=(username, access_key), timeout=HTTP_TIMEOUT)
    if response.status_code != httpx.codes.OK:
        # The body is not printed: an error page may echo request details.
        raise RuntimeError(f"devices.json request failed with HTTP {response.status_code}")
    versions: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    for entry in response.json():
        versions[(str(entry.get("os")), str(entry.get("device")))].add(str(entry.get("os_version")))
    return versions


def read_yaml_devices(repo: Path, ref: str, platform: str) -> list[Device]:
    path = DEVICES_YML[platform]
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "show", f"{ref}:{path}"], check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        raise SystemExit(f"git show {ref}:{path} failed: {e.stderr.strip()}") from e
    platforms = (yaml.safe_load(result.stdout) or {}).get("platforms") or []
    return [Device(platform, str(item["deviceName"]), str(item["osVersion"])) for item in platforms]


def status(versions: Versions | None, device: Device) -> str:
    if versions is None:
        return NOT_CHECKED
    available = versions.get((device.platform, device.name))
    if not available:
        return "device missing"
    if device.os_version in available:
        return "OK"
    return f"OS missing (has {', '.join(sort_versions(available))})"


def sort_versions(versions: Iterable[str]) -> list[str]:
    def key(version: str) -> tuple[float, ...]:
        try:
            return tuple(float(part) for part in version.split("."))
        except ValueError:
            return (float("inf"),)

    return sorted(versions, key=key)


def public_versions(devices: Iterable[PublicDevice]) -> Versions:
    versions: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    for device in devices:
        versions[(device.platform, device.name)].add(device.os_version)
    return versions


def print_source_header(farm: Versions | None, public: Sequence[PublicDevice]) -> None:
    if farm is None:
        print(
            "devices.json: not checked - BROWSERSTACK_USERNAME / BROWSERSTACK_ACCESS_KEY not set; "
            "results are not verified via devices.json"
        )
    else:
        print(f"devices.json: {sum(len(v) for v in farm.values())} device/OS pairs")
    print(f"public list: {len(public)} phone/tablet entries ({PUBLIC_LIST_URL})")


def print_devices(title: str, devices: Sequence[Device], farm: Versions | None, public: Versions) -> None:
    print(f"\n{title}")
    width = max((len(device.name) for device in devices), default=0)
    for device in devices:
        print(
            f"  {device.name.ljust(width)}  {device.os_version:<5}  "
            f"devices.json: {status(farm, device):<24}  public: {status(public, device)}"
        )


def run_check(repo: Path, refs: Sequence[str], candidates: Sequence[Sequence[str]]) -> None:
    public = fetch_public_list()
    farm = fetch_devices_json()
    by_public = public_versions(public)
    print_source_header(farm, public)
    for ref in refs:
        for platform in PLATFORMS:
            devices = read_yaml_devices(repo, ref, platform)
            print_devices(f"{ref} {platform} ({DEVICES_YML[platform]})", devices, farm, by_public)
    if candidates:
        devices = [Device(platform, name, os_version) for platform, name, os_version in candidates]
        print_devices("candidates", devices, farm, by_public)


def run_list(platform: str) -> None:
    public = [device for device in fetch_public_list() if device.platform == platform]
    farm = fetch_devices_json()
    print_source_header(farm, public)
    kinds = {(device.kind, device.name) for device in public}
    by_public = public_versions(public)
    width = max(len(name) for _, name in kinds)
    for kind, name in sorted(kinds):
        listed = ", ".join(sort_versions(by_public[(platform, name)]))
        on_farm = NOT_CHECKED if farm is None else ", ".join(sort_versions(farm.get((platform, name), set()))) or "-"
        print(f"  {kind:<6}  {name.ljust(width)}  public: {listed:<16}  devices.json: {on_farm}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="status of the YAML device lists and of candidate devices")
    check.add_argument("--repo", type=Path, default=DEFAULT_REPO, help="perfect-project checkout or worktree")
    check.add_argument("--ref", action="append", default=[], help="git ref, e.g. origin/master (repeatable)")
    check.add_argument(
        "--device",
        action="append",
        nargs=3,
        default=[],
        metavar=("PLATFORM", "NAME", "OS"),
        help='candidate, e.g. --device android "Huawei Nova 11 SE" 12.0 (repeatable)',
    )
    listing = commands.add_parser("list", help="every phone and tablet of a platform on the public list")
    listing.add_argument("platform", choices=PLATFORMS)
    args = parser.parse_args()

    if args.command == "list":
        run_list(args.platform)
        return
    if not args.ref and not args.device:
        parser.error("check needs --ref and/or --device")
    for platform, _, _ in args.device:
        if platform not in PLATFORMS:
            parser.error(f"--device platform must be one of {', '.join(PLATFORMS)}, got {platform!r}")
    run_check(args.repo, args.ref, args.device)


if __name__ == "__main__":
    main()
