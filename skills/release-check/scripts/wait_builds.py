"""Wait for TeamCity builds to finish, printing one line per state change.

Meant as a Monitor command: every stdout line is an event, and the script exits once every build has
finished. On start it prints the current state of each build, so re-arming after a Monitor timeout
picks up where it left off. Every line carries the build link and branch; a finished build also carries
its finish date, and its snapshot dependencies are listed under it, so a red composite shows which child
failed without a separate get_build call.

A queued build is checked, not just waited on: it must have at least one compatible agent (composites
run on none, so their queued children are checked instead), and once its snapshot dependencies have
finished it may stay queued for at most --max-queue-minutes. Either problem prints an ERROR line and
ends the script with exit code 2.

The token comes from TEAMCITY_TOKEN, or from am_plr/mcp/.env (the file setup reads for the teamcity
MCP server). It is never printed.
"""

import argparse
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
_FIELDS: Final = (
    "id,state,status,statusText,buildTypeId,branchName,finishDate,queuedDate,waitReason,"
    "buildType(type),compatibleAgents(count)"
)
BUILD_FIELDS: Final = f"{_FIELDS},snapshot-dependencies(build({_FIELDS}))"
TEAMCITY_DATE_FORMAT: Final = "%Y%m%dT%H%M%S%z"
# Transient network errors are tolerated this many polls in a row before giving up.
MAX_CONSECUTIVE_ERRORS: Final = 10
DEFAULT_MAX_QUEUE_MINUTES: Final = 60
EXIT_QUEUE_PROBLEM: Final = 2


@dataclass(frozen=True, slots=True)
class BuildState:
    build_id: str
    build_type_id: str
    state: str
    status: str
    status_text: str
    branch: str
    finish_date: str
    queued_date: datetime | None
    wait_reason: str
    is_composite: bool
    compatible_agents: int | None
    view_url: str
    dependencies: tuple["BuildState", ...] = ()

    @property
    def finished(self) -> bool:
        return self.state == "finished"

    @property
    def queued(self) -> bool:
        return self.state == "queued"


def parse_date(value: str | None) -> datetime | None:
    return datetime.strptime(value, TEAMCITY_DATE_FORMAT) if value else None


def parse_build(data: dict[str, Any], base_url: str) -> BuildState:
    build_id = str(data["id"])
    build_type_id = data.get("buildTypeId", "")
    agents = data.get("compatibleAgents")
    deps = (data.get("snapshot-dependencies") or {}).get("build", [])
    return BuildState(
        build_id=build_id,
        build_type_id=build_type_id,
        state=data.get("state", ""),
        status=data.get("status", ""),
        status_text=data.get("statusText", ""),
        branch=data.get("branchName", ""),
        finish_date=data.get("finishDate", ""),
        queued_date=parse_date(data.get("queuedDate")),
        wait_reason=data.get("waitReason", ""),
        is_composite=(data.get("buildType") or {}).get("type") == "composite",
        compatible_agents=agents.get("count") if agents else None,
        view_url=VIEW_LOG_URL.format(base_url=base_url, build_id=build_id, build_type_id=build_type_id),
        dependencies=tuple(parse_build(dep, base_url) for dep in deps),
    )


def format_build(build: BuildState, prefix: str = "") -> str:
    line = f"{prefix}{build.build_id} {build.build_type_id} {build.state} branch={build.branch}"
    if build.finished:
        line += f' {build.status} "{build.status_text}" finishDate={build.finish_date}'
    elif build.queued and build.wait_reason:
        line += f' waitReason="{build.wait_reason}"'
    return f"{line} {build.view_url}"


def queue_problem(build: BuildState, now: datetime, max_queue: timedelta) -> str | None:
    """Why a queued build will not start on its own, or None while it can still start.

    Waiting for its own snapshot dependencies is normal (a test build waits for the game build), so the
    queue clock starts only once every dependency has finished.
    """
    if not build.queued:
        return None
    reason = build.wait_reason or "-"
    if not build.is_composite and build.compatible_agents == 0:
        return f"no compatible agents (waitReason: {reason})"
    if any(not dep.finished for dep in build.dependencies):
        return None
    dep_finishes = [d for dep in build.dependencies if (d := parse_date(dep.finish_date))]
    waiting_since = max([build.queued_date, *dep_finishes]) if build.queued_date else None
    if waiting_since and now - waiting_since > max_queue:
        minutes = int((now - waiting_since).total_seconds() // 60)
        limit = int(max_queue.total_seconds() // 60)
        return f"queued for {minutes} min after its dependencies finished (limit {limit}), waitReason: {reason}"
    return None


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


def check_queue(builds: list[BuildState], max_queue: timedelta) -> None:
    now = datetime.now(timezone.utc)
    problems = [
        (build, problem)
        for top in builds
        for build in (top, *top.dependencies)
        if (problem := queue_problem(build, now, max_queue))
    ]
    if problems:
        for build, problem in problems:
            print(f"ERROR queue {build.build_id} {build.build_type_id}: {problem} {build.view_url}", flush=True)
        sys.exit(EXIT_QUEUE_PROBLEM)


def wait(build_ids: list[str], interval: int, max_queue: timedelta) -> None:
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
            check_queue(builds, max_queue)
            time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Wait for TeamCity builds to finish.")
    parser.add_argument("build_ids", nargs="+", help="numeric TeamCity build ids")
    parser.add_argument("--interval", type=int, default=60, help="seconds between polls (default 60)")
    parser.add_argument(
        "--max-queue-minutes",
        type=int,
        default=DEFAULT_MAX_QUEUE_MINUTES,
        help=f"fail when a build stays queued longer (default {DEFAULT_MAX_QUEUE_MINUTES})",
    )
    args = parser.parse_args()
    bad = [build_id for build_id in args.build_ids if not build_id.isdigit()]
    if bad:
        parser.error(f"build ids must be numeric: {', '.join(bad)}")
    wait(args.build_ids, args.interval, timedelta(minutes=args.max_queue_minutes))


if __name__ == "__main__":
    main()
