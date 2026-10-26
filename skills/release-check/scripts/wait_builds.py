"""Wait for TeamCity builds to finish, printing one line per state change.

Meant as a Monitor command: every stdout line is an event, and the script exits once every build has
finished. On start it prints the current state of each build, so re-arming after a Monitor timeout
picks up where it left off. Every line carries the build link, and each build's snapshot dependencies are
listed under it: the children of a composite are linked as soon as it is queued, and a red bundle shows
which child failed without a separate get_build call.

The token comes from TEAMCITY_TOKEN, or from am_plr/mcp/.env (the file setup reads for the teamcity
MCP server). It is never printed.
"""

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import httpx
from dotenv import load_dotenv

AM_PLR: Final = Path(__file__).resolve().parents[3]
MCP_ENV: Final = AM_PLR / "mcp" / ".env"
DEFAULT_URL: Final = "https://teamcity.local.playrix.com"
# The link format used in chat and Asana; TeamCity's own webUrl points to a different host and page.
VIEW_LOG_URL: Final = "{base_url}/viewLog.html?buildId={build_id}&buildTypeId={build_type_id}"
HTTP_TIMEOUT: Final = 30.0
BUILD_FIELDS: Final = (
    "id,state,status,statusText,buildTypeId,snapshot-dependencies(build(id,state,status,statusText,buildTypeId))"
)
# Transient network errors are tolerated this many polls in a row before giving up.
MAX_CONSECUTIVE_ERRORS: Final = 10


@dataclass(frozen=True, slots=True)
class BuildState:
    build_id: str
    build_type_id: str
    state: str
    status: str
    status_text: str
    view_url: str
    dependencies: tuple["BuildState", ...] = ()

    @property
    def finished(self) -> bool:
        return self.state == "finished"


def parse_build(data: dict[str, Any], base_url: str) -> BuildState:
    build_id = str(data["id"])
    build_type_id = data.get("buildTypeId", "")
    deps = (data.get("snapshot-dependencies") or {}).get("build", [])
    return BuildState(
        build_id=build_id,
        build_type_id=build_type_id,
        state=data.get("state", ""),
        status=data.get("status", ""),
        status_text=data.get("statusText", ""),
        view_url=VIEW_LOG_URL.format(base_url=base_url, build_id=build_id, build_type_id=build_type_id),
        dependencies=tuple(parse_build(dep, base_url) for dep in deps),
    )


def format_build(build: BuildState, prefix: str = "") -> str:
    line = f"{prefix}{build.build_id} {build.build_type_id} {build.state}"
    if build.finished:
        line += f' {build.status} "{build.status_text}"'
    return f"{line} {build.view_url}"


def fetch_build(client: httpx.Client, build_id: str) -> BuildState:
    resp = client.get(f"/app/rest/builds/id:{build_id}", params={"fields": BUILD_FIELDS})
    resp.raise_for_status()
    return parse_build(resp.json(), base_url=str(client.base_url).rstrip("/"))


def make_client() -> httpx.Client:
    if "TEAMCITY_TOKEN" not in os.environ:
        load_dotenv(MCP_ENV)
    token = os.environ.get("TEAMCITY_TOKEN")
    if not token:
        sys.exit(f"TEAMCITY_TOKEN is not set (env or {MCP_ENV})")
    return httpx.Client(
        base_url=os.environ.get("TEAMCITY_URL", DEFAULT_URL).rstrip("/"),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=HTTP_TIMEOUT,
        follow_redirects=True,
    )


def wait(build_ids: list[str], interval: int) -> None:
    last_state: dict[str, str] = {}
    errors = 0
    with make_client() as client:
        while True:
            try:
                builds = [fetch_build(client, build_id) for build_id in build_ids]
            except httpx.HTTPStatusError as e:
                if e.response.status_code == httpx.codes.NOT_FOUND:
                    print(f"ERROR build not found: {e.request.url}", flush=True)
                    sys.exit(1)
                raise
            except httpx.TransportError as e:
                errors += 1
                print(f"poll failed ({errors}/{MAX_CONSECUTIVE_ERRORS}): {e!r}", file=sys.stderr, flush=True)
                if errors >= MAX_CONSECUTIVE_ERRORS:
                    print(f"ERROR TeamCity unreachable for {errors} polls in a row: {e!r}", flush=True)
                    sys.exit(1)
                time.sleep(interval)
                continue
            errors = 0

            for build in builds:
                if last_state.get(build.build_id) == build.state:
                    continue
                last_state[build.build_id] = build.state
                lines = [format_build(build)]
                lines += [format_build(dep, prefix="  dep ") for dep in build.dependencies]
                print("\n".join(lines), flush=True)

            if all(build.finished for build in builds):
                print("ALL FINISHED", flush=True)
                return
            time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Wait for TeamCity builds to finish.")
    parser.add_argument("build_ids", nargs="+", help="numeric TeamCity build ids")
    parser.add_argument("--interval", type=int, default=60, help="seconds between polls (default 60)")
    args = parser.parse_args()
    bad = [build_id for build_id in args.build_ids if not build_id.isdigit()]
    if bad:
        parser.error(f"build ids must be numeric: {', '.join(bad)}")
    wait(args.build_ids, args.interval)


if __name__ == "__main__":
    main()
