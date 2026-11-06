"""Update a Qase test case over the REST API: its automation status or its steps.

The Qase MCP server is read-only, so batch writes go through this script. Each write is a PATCH followed by a GET
that reads the field back. Output is the case id and the value read back, nothing else.

The token comes from QASE_API_TOKEN, or from the vso-engine-autotests `.env` (the file the Qase MCP server reads).
It is read inside this process and never printed, so it never has to be exported in a shell.

    qase_case.py automation 16958 2          # 0 = not automated, 1 = to be automated, 2 = automated
    qase_case.py steps 16744 steps.json      # steps.json: a list of {"action", "expected_result", "data"} objects
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Final

import httpx
from dotenv import dotenv_values

AM_PLR: Final = Path(__file__).resolve().parents[3]
DEFAULT_ENV_FILE: Final = AM_PLR.parent / "vso-engine-autotests" / ".env"
TOKEN_KEY: Final = "QASE_API_TOKEN"
API_URL: Final = "https://api.qase.io/v1/case/{project}/{case_id}"
DEFAULT_PROJECT: Final = "VSO"
AUTOMATION_VALUES: Final = (0, 1, 2)
HTTP_TIMEOUT: Final = 30.0
EXIT_USAGE: Final = 2
EXIT_MISMATCH: Final = 3


class QaseError(Exception):
    """The Qase API refused the request or answered with something unexpected."""


def read_token(env_file: Path) -> str:
    token = os.environ.get(TOKEN_KEY) or (dotenv_values(env_file).get(TOKEN_KEY) if env_file.is_file() else None)
    if not token:
        raise QaseError(f"{TOKEN_KEY} is not set in the environment or in {env_file}")
    return token


def load_steps(path: Path) -> list[dict[str, Any]]:
    steps = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(steps, list) or not all(isinstance(step, dict) and "action" in step for step in steps):
        raise ValueError(f"{path} must hold a JSON list of step objects, each with an 'action'")
    return steps


class QaseCaseClient:
    def __init__(self, token: str, project: str) -> None:
        self._client: httpx.Client = httpx.Client(headers={"Token": token}, timeout=HTTP_TIMEOUT)
        self._project: str = project

    def get(self, case_id: int) -> dict[str, Any]:
        return self._request("GET", case_id)

    def patch(self, case_id: int, payload: dict[str, Any]) -> None:
        self._request("PATCH", case_id, payload)

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, case_id: int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = API_URL.format(project=self._project, case_id=case_id)
        try:
            response = self._client.request(method, url, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise QaseError(f"{method} {self._project}-{case_id} failed: {error}") from error
        body = response.json()
        if not body.get("status"):
            raise QaseError(f"{method} {self._project}-{case_id} refused: {body.get('errorMessage', body)}")
        return body.get("result") or {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update a Qase case (automation or steps) and read it back.")
    parser.add_argument("--project", default=DEFAULT_PROJECT, help=f"Qase project code (default {DEFAULT_PROJECT})")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE, help="where to look for the token")
    commands = parser.add_subparsers(dest="command", required=True)
    automation = commands.add_parser("automation", help="set the automation status")
    automation.add_argument("case_id", type=int)
    automation.add_argument("value", type=int, choices=AUTOMATION_VALUES)
    steps = commands.add_parser("steps", help="replace the steps with the ones in a JSON file")
    steps.add_argument("case_id", type=int)
    steps.add_argument("steps_file", type=Path)
    return parser


def run(args: argparse.Namespace) -> int:
    client = QaseCaseClient(read_token(args.env_file), args.project)
    case = f"{args.project}-{args.case_id}"
    try:
        if args.command == "automation":
            client.patch(args.case_id, {"automation": args.value})
            actual = client.get(args.case_id).get("automation")
            print(f"{case}: automation={actual}")
            return 0 if actual == args.value else EXIT_MISMATCH
        new_steps = load_steps(args.steps_file)
        client.patch(args.case_id, {"steps": new_steps})
        actual_steps = client.get(args.case_id).get("steps") or []
        print(f"{case}: steps={len(actual_steps)} (sent {len(new_steps)})")
        return 0 if len(actual_steps) == len(new_steps) else EXIT_MISMATCH
    finally:
        client.close()


def main() -> int:
    args = build_parser().parse_args()
    try:
        return run(args)
    except (QaseError, ValueError, OSError) as error:
        print(f"qase_case: {error}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
