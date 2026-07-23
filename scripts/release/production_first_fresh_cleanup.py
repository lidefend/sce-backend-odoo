#!/usr/bin/env python3
"""Exact, fail-closed cleanup for the approved first fresh production deploy."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


CONFIRMATION = "YES_DELETE_OLD_PROJECT_DATA"
TARGET_PROJECT = "sc_production"
TARGET_DATABASE = "sc_production"

OLD_CONTAINERS = {
    "sc-backend-odoo-prod-db-1": "sc-backend-odoo-prod",
    "sc-backend-odoo-prod-nginx-1": "sc-backend-odoo-prod",
    "sc-backend-odoo-prod-odoo-1": "sc-backend-odoo-prod",
    "sc-backend-odoo-prod-redis-1": "sc-backend-odoo-prod",
    "sce-sc-production-db-1": "sce-sc-production",
    "sce-sc-production-nginx-1": "sce-sc-production",
    "sce-sc-production-odoo-1": "sce-sc-production",
    "sce-sc-production-redis-1": "sce-sc-production",
}
OLD_NETWORKS = {
    "sc-backend-odoo-prod_default": "sc-backend-odoo-prod",
    "sce-sc-production_default": "sce-sc-production",
}
OLD_VOLUMES = {
    "19b5faccb8d053f2a7402d22ad14beab56e42c3db802ef8a035bb866fc8fd25a",
    "61effd68c1622d09f90d33b761334bae94e343cf5a40ed223f545ef5fe089937",
    "804b23abe7bc26b915aa568bacf6186b5d54dedbfc7c9cf99d5d9d9fedfe39eb",
    "e78d2924f92e1b17d468718fce5ef31e12016840f04f68ad680136a9e47e4084",
    "sc_prod_db_data",
    "sc_prod_odoo_data",
    "sc_prod_redis_data",
    "sce-sc_production-filestore",
    "sce-sc_production-logs",
    "sce-sc_production-postgres",
    "sce-sc_production-redis",
    "sce-sc_production-sessions",
    "sce-sc_production-tmp",
}
PRESERVED_PATHS = (
    "/opt/sce/config/sc_production",
    "/etc/nginx",
    "/etc/letsencrypt",
    "/data/odoo/legacy_attachments",
    "/opt/sce/candidates/v1.0.0-rc.4",
    "/opt/sce/releases/e996239f1779cf510a0ca2ca5cd169121406a48b",
)


class CleanupError(RuntimeError):
    pass


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _run(runner: Runner, *args: str) -> subprocess.CompletedProcess[str]:
    return runner(args, check=True, text=True, capture_output=True)


def _inspect(runner: Runner, kind: str, names: list[str]) -> list[dict[str, Any]]:
    command = ("docker", "inspect", *names) if not kind else (
        "docker", kind, "inspect", *names
    )
    result = _run(runner, *command)
    payload = json.loads(result.stdout)
    if not isinstance(payload, list):
        raise CleanupError(f"{kind} inspect did not return a list")
    return payload


def collect_snapshot(runner: Runner = subprocess.run) -> dict[str, Any]:
    all_ids = _run(runner, "docker", "ps", "-aq").stdout.split()
    all_containers = _inspect(runner, "", all_ids) if all_ids else []
    return {
        "containers": all_containers,
        "networks": _inspect(runner, "network", sorted(OLD_NETWORKS)),
        "volumes": _inspect(runner, "volume", sorted(OLD_VOLUMES)),
    }


def validate_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    containers = snapshot["containers"]
    by_name = {item["Name"].lstrip("/"): item for item in containers}
    actual_old = {
        name
        for name, item in by_name.items()
        if (item.get("Config", {}).get("Labels") or {}).get("com.docker.compose.project")
        in set(OLD_CONTAINERS.values())
    }
    if actual_old != set(OLD_CONTAINERS):
        raise CleanupError("legacy container inventory differs from the fixed whitelist")
    if any(
        (item.get("Config", {}).get("Labels") or {}).get("com.docker.compose.project")
        == TARGET_PROJECT
        for item in containers
    ):
        raise CleanupError("new sc_production containers already exist")

    volume_users: dict[str, list[dict[str, str]]] = {name: [] for name in OLD_VOLUMES}
    binds: list[dict[str, str]] = []
    for name, item in by_name.items():
        project = (item.get("Config", {}).get("Labels") or {}).get(
            "com.docker.compose.project", ""
        )
        for mount in item.get("Mounts") or []:
            if mount.get("Type") == "volume" and mount.get("Name") in volume_users:
                volume_users[mount["Name"]].append(
                    {"container": name, "destination": mount.get("Destination", "")}
                )
            if name in OLD_CONTAINERS and mount.get("Type") == "bind":
                binds.append(
                    {
                        "container": name,
                        "source": mount.get("Source", ""),
                        "destination": mount.get("Destination", ""),
                    }
                )
        if name in OLD_CONTAINERS and project != OLD_CONTAINERS[name]:
            raise CleanupError(f"container project mismatch: {name}")

    if any(not users for users in volume_users.values()):
        raise CleanupError("every whitelisted volume must be attached to a legacy container")
    for volume, users in volume_users.items():
        if any(user["container"] not in OLD_CONTAINERS for user in users):
            raise CleanupError(f"volume has a non-legacy user: {volume}")

    inspected_volumes = {item["Name"] for item in snapshot["volumes"]}
    if inspected_volumes != OLD_VOLUMES:
        raise CleanupError("volume inventory differs from the fixed whitelist")

    inspected_networks = {item["Name"]: item for item in snapshot["networks"]}
    if set(inspected_networks) != set(OLD_NETWORKS):
        raise CleanupError("network inventory differs from the fixed whitelist")
    for name, item in inspected_networks.items():
        project = (item.get("Labels") or {}).get("com.docker.compose.project")
        if project != OLD_NETWORKS[name]:
            raise CleanupError(f"network project mismatch: {name}")
        members = {
            details.get("Name")
            for details in (item.get("Containers") or {}).values()
        }
        if any(member not in OLD_CONTAINERS for member in members):
            raise CleanupError(f"network has a non-legacy member: {name}")

    return {
        "containers": sorted(OLD_CONTAINERS),
        "networks": sorted(OLD_NETWORKS),
        "volumes": sorted(OLD_VOLUMES),
        "volume_users": volume_users,
        "bind_mounts": sorted(
            binds, key=lambda item: (item["container"], item["destination"])
        ),
        "preserved_paths": list(PRESERVED_PATHS),
    }


def _path_fingerprints() -> dict[str, tuple[int, int]]:
    result = {}
    for value in PRESERVED_PATHS:
        path = Path(value)
        if not path.exists():
            raise CleanupError(f"preserved path is missing: {value}")
        stat = path.stat()
        result[value] = (stat.st_dev, stat.st_ino)
    return result


def _validate_environment(apply: bool) -> None:
    if os.environ.get("ENV") != "prod":
        raise CleanupError("ENV=prod is required")
    if os.environ.get("PRODUCTION_COMPOSE_PROJECT") != TARGET_PROJECT:
        raise CleanupError("PRODUCTION_COMPOSE_PROJECT must be sc_production")
    if os.environ.get("TARGET_DB") != TARGET_DATABASE:
        raise CleanupError("TARGET_DB must be sc_production")
    if apply:
        if os.environ.get("PROD_DANGER") != "1":
            raise CleanupError("PROD_DANGER=1 is required")
        if os.environ.get("CONFIRM_FRESH_PRODUCTION_DEPLOY") != CONFIRMATION:
            raise CleanupError(
                "CONFIRM_FRESH_PRODUCTION_DEPLOY=YES_DELETE_OLD_PROJECT_DATA is required"
            )


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    if mode not in {"plan", "apply"}:
        raise SystemExit("usage: production_first_fresh_cleanup.py plan|apply")
    try:
        _validate_environment(mode == "apply")
        before = _path_fingerprints()
        plan = validate_snapshot(collect_snapshot())
        if mode == "plan":
            print("[production.first-fresh.cleanup] PLAN " + json.dumps(plan, sort_keys=True))
            return 0

        subprocess.run(["docker", "stop", *sorted(OLD_CONTAINERS)], check=True)
        subprocess.run(["docker", "rm", *sorted(OLD_CONTAINERS)], check=True)
        subprocess.run(["docker", "network", "rm", *sorted(OLD_NETWORKS)], check=True)
        subprocess.run(["docker", "volume", "rm", *sorted(OLD_VOLUMES)], check=True)
        if _path_fingerprints() != before:
            raise CleanupError("a preserved path identity changed during cleanup")
    except (CleanupError, json.JSONDecodeError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"[production.first-fresh.cleanup] BLOCKED: {exc}") from exc
    print("[production.first-fresh.cleanup] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
