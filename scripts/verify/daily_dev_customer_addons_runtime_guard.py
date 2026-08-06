#!/usr/bin/env python3
"""Fail closed when the daily registry cannot load its installed customer module."""

from __future__ import annotations

import ast
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


CUSTOM_MODULE = "smart_construction_custom"
CUSTOM_CONTAINER_ROOT = Path("/mnt/customer-addons")
RESOLUTION_MARKER = "DAILY_CUSTOM_MODULE_RESOLUTION="


class GuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    compose_bin: str
    compose_files: str
    compose_project: str
    db_name: str
    db_user: str
    odoo_conf: str
    customer_root: Path

    @classmethod
    def from_env(cls) -> "Config":
        required = {
            "COMPOSE_PROJECT_NAME": os.getenv("COMPOSE_PROJECT_NAME", "").strip(),
            "DB_NAME": os.getenv("DB_NAME", "").strip(),
            "DB_USER": os.getenv("DB_USER", "").strip(),
            "SC_CUSTOMER_ADDONS_ROOT": os.getenv("SC_CUSTOMER_ADDONS_ROOT", "").strip(),
        }
        missing = sorted(key for key, value in required.items() if not value)
        if missing:
            raise GuardError("missing environment: " + ", ".join(missing))
        return cls(
            compose_bin=os.getenv("COMPOSE_BIN", "docker compose"),
            compose_files=os.getenv("COMPOSE_FILES", "-f docker-compose.yml"),
            compose_project=required["COMPOSE_PROJECT_NAME"],
            db_name=required["DB_NAME"],
            db_user=required["DB_USER"],
            odoo_conf=os.getenv("ODOO_CONF", "/var/lib/odoo/odoo.conf"),
            customer_root=Path(required["SC_CUSTOMER_ADDONS_ROOT"]),
        )


Runner = Callable[[list[str], str | None], str]


def run_command(args: list[str], input_text: str | None = None) -> str:
    result = subprocess.run(
        args,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[:800]
        raise GuardError(f"command failed ({result.returncode}): {args[0]}: {detail}")
    return result.stdout.strip()


def compose_args(config: Config, *args: str) -> list[str]:
    return [
        *shlex.split(config.compose_bin),
        "-p",
        config.compose_project,
        *shlex.split(config.compose_files),
        *args,
    ]


def manifest_version(module_root: Path) -> str:
    manifest = module_root / "__manifest__.py"
    if not manifest.is_file():
        raise GuardError(f"customer manifest missing: {manifest}")
    tree = ast.parse(manifest.read_text(encoding="utf-8"), filename=str(manifest))
    expression = next((node for node in tree.body if isinstance(node, ast.Expr)), None)
    values = ast.literal_eval(expression.value) if expression else {}
    version = str(values.get("version") or "").strip()
    if not version:
        raise GuardError(f"customer manifest version missing: {manifest}")
    return version


def parse_single_json(output: str, label: str) -> dict[str, object]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if len(lines) != 1:
        raise GuardError(f"{label} returned {len(lines)} rows")
    try:
        value = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise GuardError(f"{label} returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise GuardError(f"{label} did not return an object")
    return value


def audit(config: Config, runner: Runner = run_command) -> dict[str, object]:
    customer_root = config.customer_root.resolve()
    source_version = manifest_version(customer_root / CUSTOM_MODULE)

    container_id = runner(compose_args(config, "ps", "-q", "odoo"), None).strip()
    if not container_id or "\n" in container_id:
        raise GuardError("daily Odoo service container is missing or ambiguous")

    mounts_raw = runner(["docker", "inspect", container_id, "--format", "{{json .Mounts}}"], None)
    try:
        mounts = json.loads(mounts_raw)
    except json.JSONDecodeError as exc:
        raise GuardError("container mount inspection returned invalid JSON") from exc
    customer_mounts = [item for item in mounts if item.get("Destination") == str(CUSTOM_CONTAINER_ROOT)]
    if len(customer_mounts) != 1:
        raise GuardError("daily Odoo container must have exactly one /mnt/customer-addons mount")
    customer_mount = customer_mounts[0]
    if Path(str(customer_mount.get("Source") or "")).resolve() != customer_root:
        raise GuardError("daily Odoo customer mount source differs from SC_CUSTOMER_ADDONS_ROOT")
    if customer_mount.get("RW") is not False:
        raise GuardError("daily Odoo customer mount must be read-only")

    db_sql = (
        "SELECT json_build_object('state', state, 'latest_version', latest_version)::text "
        "FROM ir_module_module WHERE name = 'smart_construction_custom'"
    )
    db_output = runner(
        compose_args(
            config,
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            config.db_user,
            "-d",
            config.db_name,
            "-At",
            "-c",
            db_sql,
        ),
        None,
    )
    db_module = parse_single_json(db_output, "customer module database query")
    if db_module.get("state") != "installed":
        raise GuardError(f"customer module state is {db_module.get('state')!r}, expected 'installed'")
    if db_module.get("latest_version") != source_version:
        raise GuardError("customer module database version differs from customer package manifest")

    shell_program = f"""
import json
from odoo.modules.module import get_module_path, load_information_from_description_file
print({RESOLUTION_MARKER!r} + json.dumps({{
    'path': get_module_path({CUSTOM_MODULE!r}),
    'version': load_information_from_description_file({CUSTOM_MODULE!r}).get('version'),
}}, sort_keys=True))
env.cr.rollback()
"""
    shell_output = runner(
        compose_args(
            config,
            "exec",
            "-T",
            "odoo",
            "odoo",
            "shell",
            "-d",
            config.db_name,
            "-c",
            config.odoo_conf,
        ),
        shell_program,
    )
    marker_lines = [line for line in shell_output.splitlines() if line.startswith(RESOLUTION_MARKER)]
    if len(marker_lines) != 1:
        raise GuardError("daily Odoo registry did not report one customer-module resolution")
    resolution = parse_single_json(marker_lines[0][len(RESOLUTION_MARKER) :], "customer resolution")
    expected_path = str(CUSTOM_CONTAINER_ROOT / CUSTOM_MODULE)
    if resolution.get("path") != expected_path:
        raise GuardError(f"customer module resolved from {resolution.get('path')!r}, expected {expected_path!r}")
    if resolution.get("version") != source_version:
        raise GuardError("daily Odoo resolved customer version differs from package manifest")

    return {
        "status": "PASS",
        "container_id": container_id,
        "customer_mount": str(customer_root),
        "customer_mount_read_only": True,
        "module": CUSTOM_MODULE,
        "state": db_module["state"],
        "installed_version": source_version,
        "latest_version": db_module["latest_version"],
        "resolved_path": resolution["path"],
    }


def main() -> int:
    try:
        payload = audit(Config.from_env())
    except (GuardError, OSError, SyntaxError, ValueError) as exc:
        print(f"[daily_dev_customer_addons_runtime_guard] BLOCKED {exc}", file=sys.stderr)
        return 2
    print("[daily_dev_customer_addons_runtime_guard] PASS " + json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
