#!/usr/bin/env python3
"""Run one program through a declared daily duty's Odoo shell, or restart it.

A database name alone no longer identifies a daily target (the rebuilt demo
carrier and the preserved historic source both answer to ``sc_demo``).  This
entry binds the duty declaration, resolves the duty's own running Odoo
container, and never falls back to the checkout's compose project.  ``--restart``
uses the same binding to restart the duty's own container and wait for health.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DECLARATION = ROOT / "config" / "ops" / "daily_runtime_database_duties.v1.json"
DEFAULT_ODOO_CONFIG = "/var/lib/odoo/odoo.conf"
RESTART_TIMEOUT_SECONDS = 180
RESTART_POLL_SECONDS = 2
FORWARDED_ENV = (
    "SC_ENVIRONMENT",
    "SC_ALLOW_DEMO_DATA",
    "PRODUCT_MENU_CATALOG_FULL_PRODUCT_LOGIN",
    "PRODUCT_MENU_CATALOG_PRODUCT_KEYS",
)


class DutyShellError(RuntimeError):
    """The declared duty cannot provide a governed shell."""


def load_declaration(path: Path) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DutyShellError(f"duty declaration unreadable: {path} ({exc})") from exc
    if not isinstance(document, dict):
        raise DutyShellError("duty declaration must be a JSON object")
    return document


def resolve_duty(document: dict, duty_key: str) -> dict:
    for duty in document.get("duties") or []:
        if isinstance(duty, dict) and duty.get("duty") == duty_key:
            return duty
    raise DutyShellError(f"duty {duty_key!r} is not declared")


def odoo_container(duty: dict) -> str:
    project = str((duty.get("cluster") or {}).get("compose_project") or "").strip()
    services = [str(item) for item in ((duty.get("stack") or {}).get("services") or [])]
    if not project or "odoo" not in services:
        raise DutyShellError("the declared duty has no compose project or no odoo service")
    return f"{project}-odoo-1"


def declared_environment(duty: dict, extra: dict[str, str]) -> dict[str, str]:
    environment = {key: os.environ[key] for key in FORWARDED_ENV if os.environ.get(key)}
    environment.update({key: value for key, value in extra.items() if value})
    return environment


def build_command(
    duty: dict,
    container: str,
    *,
    odoo_config: str,
    environment: dict[str, str],
) -> list[str]:
    database = str(duty.get("database") or "").strip()
    if not database:
        raise DutyShellError("the declared duty has no database")
    command = ["docker", "exec", "-i"]
    for key in sorted(environment):
        command.extend(["-e", f"{key}={environment[key]}"])
    command.extend(
        [
            container,
            "odoo",
            "shell",
            "-d",
            database,
            "-c",
            odoo_config,
            "--no-http",
            "--workers=0",
            "--max-cron-threads=0",
        ]
    )
    return command


def container_is_running(container: str) -> bool:
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", container],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def container_health(container: str) -> str:
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}", container],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def restart_container(container: str, timeout: int = RESTART_TIMEOUT_SECONDS) -> str:
    """Restart the duty's own Odoo container and wait for its declared readiness."""
    result = subprocess.run(
        ["docker", "restart", container],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise DutyShellError(
            f"docker restart failed for {container}: {(result.stderr or result.stdout).strip()[:300]}"
        )
    deadline = time.monotonic() + timeout
    health = ""
    while time.monotonic() < deadline:
        health = container_health(container)
        if health == "healthy":
            return health
        if health in ("unhealthy", "exited", "dead"):
            raise DutyShellError(f"duty container {container} is {health} after restart")
        time.sleep(RESTART_POLL_SECONDS)
    raise DutyShellError(
        f"duty container {container} did not become healthy within {timeout}s (last={health or 'unknown'})"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duty", required=True)
    parser.add_argument("--database", default="")
    parser.add_argument("--declaration", default=str(DEFAULT_DECLARATION))
    parser.add_argument("--odoo-config", default=DEFAULT_ODOO_CONFIG)
    parser.add_argument("--env", action="append", default=[], metavar="NAME=VALUE")
    parser.add_argument(
        "--restart",
        action="store_true",
        help="restart the duty's Odoo container instead of running a shell program",
    )
    args = parser.parse_args(argv)

    extra: dict[str, str] = {}
    for item in args.env:
        key, separator, value = item.partition("=")
        if not separator or not key:
            print(f"[DENY] --env expects NAME=VALUE, got {item!r}", file=sys.stderr)
            return 2
        extra[key] = value

    try:
        duty = resolve_duty(load_declaration(Path(args.declaration)), args.duty)
        if args.database and args.database != duty.get("database"):
            raise DutyShellError(
                f"database {args.database!r} does not belong to duty {args.duty!r} "
                f"({duty.get('database')!r})"
            )
        container = odoo_container(duty)
        if not args.restart and not container_is_running(container):
            raise DutyShellError(f"duty {args.duty!r} odoo container is not running: {container}")
        if args.restart:
            health = restart_container(container)
            print(f"[daily.duty.restart] PASS duty={args.duty} container={container} health={health}")
            return 0
        command = build_command(
            duty,
            container,
            odoo_config=args.odoo_config,
            environment=declared_environment(duty, extra),
        )
    except DutyShellError as exc:
        print(f"[DENY] {exc}", file=sys.stderr)
        return 2

    program = sys.stdin.buffer.read()
    result = subprocess.run(command, input=program, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
