#!/usr/bin/env python3
"""Resolve and validate the managed frontend acceptance runtime profile."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/frontend/acceptance_environments_v1.json"
SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_./:@^$-]+$")


def _primary_worktree() -> Path:
    common = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    common_path = Path(common).resolve()
    if common_path.name != ".git":
        raise ValueError(f"unexpected git common directory: {common_path}")
    return common_path.parent


def resolve(profile_name: str) -> dict[str, str]:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    profile = (policy.get("profiles") or {}).get(profile_name)
    if not isinstance(profile, dict):
        raise ValueError(f"unknown acceptance profile: {profile_name}")
    runtime = profile.get("managed_runtime")
    if not isinstance(runtime, dict):
        raise ValueError(f"profile {profile_name} has no managed_runtime contract")
    database = profile.get("database")
    expected_filter = f"^{database}$"
    if runtime.get("database_filter") != expected_filter:
        raise ValueError("managed runtime database_filter must exactly lock the profile database")
    volumes = runtime.get("volumes") or {}
    services = runtime.get("services") or {}
    if len({volumes.get("database"), volumes.get("redis"), volumes.get("odoo")}) != 3:
        raise ValueError("managed runtime volumes must be three distinct non-empty identities")
    frontend_port = services.get("frontend_port")
    expected_url = f"http://127.0.0.1:{frontend_port}"
    if profile.get("base_url") != expected_url:
        raise ValueError("profile base_url and managed frontend port disagree")
    base_env_name = runtime.get("base_env_file")
    if not isinstance(base_env_name, str) or Path(base_env_name).name != base_env_name:
        raise ValueError("managed runtime base_env_file must be a filename in the primary worktree")
    values = {
        "SC_ACCEPTANCE_RUNTIME_PROFILE": profile_name,
        "SC_ACCEPTANCE_BASE_ENV_FILE": str(_primary_worktree() / base_env_name),
        "COMPOSE_PROJECT_NAME": runtime.get("compose_project"),
        "PROJECT": runtime.get("compose_project"),
        "SC_ACCEPTANCE_CREDENTIAL_CONTAINER": runtime.get("credential_container"),
        "DB_NAME": database,
        "DB": database,
        "ODOO_DB": database,
        "ODOO_DBFILTER": runtime.get("database_filter"),
        "DB_DATA": volumes.get("database"),
        "REDIS_DATA": volumes.get("redis"),
        "ODOO_DATA": volumes.get("odoo"),
        "ODOO_PORT": str(services.get("compose_backend_port")),
        "BACKEND_ACCEPTANCE_NAME": services.get("backend_container"),
        "BACKEND_ACCEPTANCE_PORT": str(services.get("backend_port")),
        "BACKEND_ACCEPTANCE_DB": database,
        "FRONTEND_ACCEPTANCE_PORT": str(frontend_port),
        "FRONTEND_ACCEPTANCE_DB": database,
        "FRONTEND_ACCEPTANCE_PIDFILE": services.get("frontend_pidfile"),
        "FRONTEND_ACCEPTANCE_LOGFILE": services.get("frontend_logfile"),
        "VITE_API_PROXY_TARGET": f"http://127.0.0.1:{services.get('backend_port')}",
        "VITE_ODOO_DB": database,
        "VITE_ODOO_DB_LOCKED": "1",
        "SC_ENVIRONMENT": "acceptance",
        "SC_ALLOW_DEMO_DATA": "1",
    }
    for key, value in values.items():
        if not isinstance(value, str) or not value or not SAFE_TOKEN.fullmatch(value):
            raise ValueError(f"unsafe or missing managed runtime value: {key}")
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="local")
    parser.add_argument("--get")
    args = parser.parse_args()
    values = resolve(args.profile)
    if args.get:
        if args.get not in values:
            raise ValueError(f"unknown managed runtime key: {args.get}")
        print(values[args.get])
        return 0
    for key, value in values.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
