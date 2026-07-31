#!/usr/bin/env python3
"""Fail-closed cleanup for one precisely identified failed production attempt."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


TARGET_PROJECT = "sc_production"
TARGET_DATABASE = "sc_production"
CONFIRMATION = "YES_REMOVE_VERIFIED_FAILED_SC_PRODUCTION_ATTEMPT"
CONTAINERS = {
    "sc_production-db-1",
    "sc_production-nginx-1",
    "sc_production-odoo-1",
    "sc_production-redis-1",
}
NETWORK = "sc_production_default"
NAMED_VOLUMES = {
    "sce-sc_production-filestore",
    "sce-sc_production-logs",
    "sce-sc_production-postgres",
    "sce-sc_production-redis",
    "sce-sc_production-sessions",
    "sce-sc_production-tmp",
}
EXPECTED_MOUNTS = {
    ("sc_production-db-1", "/var/lib/postgresql/data"):
        "sce-sc_production-postgres",
    ("sc_production-redis-1", "/data"): "sce-sc_production-redis",
    ("sc_production-odoo-1", "/opt/sce-runtime/filestore"):
        "sce-sc_production-filestore",
    ("sc_production-odoo-1", "/opt/sce-runtime/logs"):
        "sce-sc_production-logs",
    ("sc_production-odoo-1", "/opt/sce-runtime/sessions"):
        "sce-sc_production-sessions",
    ("sc_production-odoo-1", "/opt/sce-runtime/tmp"):
        "sce-sc_production-tmp",
}
ALLOWED_ANONYMOUS_MOUNTS = {
    ("sc_production-odoo-1", "/var/lib/odoo"),
    ("sc_production-odoo-1", "/mnt/extra-addons"),
    ("sc_production-nginx-1", "/var/lib/odoo"),
    ("sc_production-nginx-1", "/mnt/extra-addons"),
}
PRESERVED_PATHS = (
    "/data/odoo/legacy_attachments",
    "/etc/letsencrypt",
    "/etc/nginx",
    "/opt/sce/config/sc_production",
)
LEGACY_ATTACHMENTS = Path("/data/odoo/legacy_attachments")
MAX_FAILED_FILESTORE_BYTES = 8 * 1024 * 1024
LOCK_PATH = Path("/run/lock/sc-production-failed-cleanup.lock")
ANONYMOUS_VOLUME = re.compile(r"^[0-9a-f]{64}$")


class CleanupError(RuntimeError):
    pass


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _run(runner: Runner, *args: str) -> subprocess.CompletedProcess[str]:
    return runner(args, check=True, text=True, capture_output=True)


def _inspect(runner: Runner, *args: str) -> list[dict[str, Any]]:
    payload = json.loads(_run(runner, "docker", "inspect", *args).stdout)
    if not isinstance(payload, list):
        raise CleanupError("docker inspect result must be a list")
    return payload


def _volume_inspect(runner: Runner, names: list[str]) -> list[dict[str, Any]]:
    payload = json.loads(
        _run(runner, "docker", "volume", "inspect", *names).stdout
    )
    if not isinstance(payload, list):
        raise CleanupError("docker volume inspect result must be a list")
    return payload


def _network_inspect(runner: Runner) -> dict[str, Any]:
    payload = json.loads(
        _run(runner, "docker", "network", "inspect", NETWORK).stdout
    )
    if not isinstance(payload, list) or len(payload) != 1:
        raise CleanupError("production network identity is ambiguous")
    return payload[0]


def _real_path_without_symlink(path: Path) -> Path:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise CleanupError(f"symlink is forbidden in cleanup path: {path}")
    return path.resolve(strict=True)


def _tree_stats(path: Path) -> dict[str, int]:
    files = 0
    bytes_total = 0
    for item in path.rglob("*"):
        if item.is_symlink():
            continue
        if item.is_file():
            files += 1
            bytes_total += item.stat().st_size
    return {"file_count": files, "bytes": bytes_total}


def preserved_fingerprint() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for raw in PRESERVED_PATHS:
        path = Path(raw)
        real = _real_path_without_symlink(path)
        stat = real.stat()
        value: dict[str, Any] = {
            "path": raw,
            "real_path": str(real),
            "device": stat.st_dev,
            "inode": stat.st_ino,
        }
        if path == LEGACY_ATTACHMENTS:
            value.update(_tree_stats(real))
        result[raw] = value
    return result


def _overlaps(left: Path, right: Path) -> bool:
    left_value = str(left)
    right_value = str(right)
    return (
        os.path.commonpath((left_value, right_value)) == left_value
        or os.path.commonpath((left_value, right_value)) == right_value
    )


def _directory_bytes(path: Path) -> int:
    return _tree_stats(path)["bytes"]


def collect_snapshot(runner: Runner = subprocess.run) -> dict[str, Any]:
    containers = _inspect(runner, *sorted(CONTAINERS))
    all_ids = _run(runner, "docker", "ps", "-aq").stdout.split()
    all_containers = _inspect(runner, *all_ids) if all_ids else []
    rows = _run(
        runner,
        "docker",
        "ps",
        "-a",
        "--filter",
        f"label=com.docker.compose.project={TARGET_PROJECT}",
        "--format",
        "{{json .}}",
    ).stdout.splitlines()
    all_containers = [json.loads(row) for row in rows if row.strip()]
    mounted_volumes = sorted(
        {
            mount["Name"]
            for container in containers
            for mount in container.get("Mounts") or []
            if mount.get("Type") == "volume"
        }
    )
    return {
        "containers": containers,
        "all_containers": all_containers,
        "project_container_rows": all_containers,
        "network": _network_inspect(runner),
        "volumes": _volume_inspect(runner, mounted_volumes),
    }


def validate_snapshot(
    snapshot: dict[str, Any],
    *,
    expected_image_id: str,
    expected_tool_sha: str,
) -> dict[str, Any]:
    containers = snapshot["containers"]
    by_name = {item["Name"].lstrip("/"): item for item in containers}
    if set(by_name) != CONTAINERS:
        raise CleanupError("container inventory differs from the fixed scope")
    project_rows = snapshot["project_container_rows"]
    row_names = {
        str(item.get("Names") or item.get("Name") or "").lstrip("/")
        for item in project_rows
    }
    if row_names != CONTAINERS:
        raise CleanupError("unexpected container belongs to sc_production")

    volumes: set[str] = set()
    mount_pairs: dict[tuple[str, str], str] = {}
    bind_sources: list[str] = []
    for name, item in by_name.items():
        labels = item.get("Config", {}).get("Labels") or {}
        if labels.get("com.docker.compose.project") != TARGET_PROJECT:
            raise CleanupError(f"container project mismatch: {name}")
        if item.get("Image") != expected_image_id and name in {
            "sc_production-odoo-1",
            "sc_production-nginx-1",
        }:
            raise CleanupError(f"application image identity mismatch: {name}")
        working_dir = labels.get("com.docker.compose.project.working_dir", "")
        if name == "sc_production-odoo-1":
            marker = Path(working_dir) / "DEPLOYMENT_TOOL_SHA"
            if not marker.is_file() or marker.read_text(encoding="utf-8").strip() != (
                expected_tool_sha
            ):
                raise CleanupError("deployment tool identity mismatch")
        for mount in item.get("Mounts") or []:
            if mount.get("Type") == "bind":
                bind_sources.append(str(mount.get("Source") or ""))
                continue
            if mount.get("Type") != "volume":
                raise CleanupError(f"unsupported mount type on {name}")
            volume = str(mount.get("Name") or "")
            destination = str(mount.get("Destination") or "")
            volumes.add(volume)
            mount_pairs[(name, destination)] = volume

    for pair, volume in EXPECTED_MOUNTS.items():
        if mount_pairs.get(pair) != volume:
            raise CleanupError(f"required volume mount mismatch: {pair}")
    for pair, volume in mount_pairs.items():
        if volume in NAMED_VOLUMES:
            if EXPECTED_MOUNTS.get(pair) != volume:
                raise CleanupError(f"named volume mounted outside approved target: {volume}")
        elif pair not in ALLOWED_ANONYMOUS_MOUNTS:
            raise CleanupError(f"anonymous volume mount is outside approved scope: {pair}")

    inspected = {item["Name"]: item for item in snapshot["volumes"]}
    if set(inspected) != volumes or not NAMED_VOLUMES.issubset(volumes):
        raise CleanupError("volume inventory is incomplete or ambiguous")
    preserve_reals = [
        _real_path_without_symlink(Path(value)) for value in PRESERVED_PATHS
    ]
    volume_paths: dict[str, str] = {}
    volume_users: dict[str, list[tuple[str, str]]] = {
        name: [] for name in inspected
    }
    for item in snapshot["all_containers"]:
        user = item["Name"].lstrip("/")
        for mount in item.get("Mounts") or []:
            if mount.get("Type") == "volume" and mount.get("Name") in volume_users:
                volume_users[mount["Name"]].append(
                    (user, str(mount.get("Destination") or ""))
                )
    for volume, item in inspected.items():
        labels = item.get("Labels") or {}
        if volume in NAMED_VOLUMES:
            if labels.get("com.docker.compose.project") != TARGET_PROJECT:
                raise CleanupError(f"named volume lacks exact ownership: {volume}")
        elif (
            not ANONYMOUS_VOLUME.fullmatch(volume)
            or labels.get("com.docker.compose.project") not in {None, TARGET_PROJECT}
        ):
            raise CleanupError(f"anonymous volume identity is unsafe: {volume}")
        users = volume_users[volume]
        if not users or any(user not in CONTAINERS for user, _ in users):
            raise CleanupError(f"volume has an external or missing user: {volume}")
        expected_users = sorted(
            pair for pair, mounted in mount_pairs.items() if mounted == volume
        )
        if sorted(users) != expected_users:
            raise CleanupError(f"volume user topology mismatch: {volume}")
        mountpoint = _real_path_without_symlink(Path(item["Mountpoint"]))
        if any(_overlaps(mountpoint, path) for path in preserve_reals):
            raise CleanupError(f"cleanup volume overlaps a preserved path: {volume}")
        volume_paths[volume] = str(mountpoint)
    for source in bind_sources:
        source_path = _real_path_without_symlink(Path(source))
        if any(_overlaps(source_path, path) for path in preserve_reals):
            raise CleanupError("project bind mount overlaps a preserved path")

    filestore = Path(volume_paths["sce-sc_production-filestore"])
    filestore_bytes = _directory_bytes(filestore)
    if filestore_bytes > MAX_FAILED_FILESTORE_BYTES:
        raise CleanupError("failed application filestore exceeds authorized size")

    network = snapshot["network"]
    if network.get("Name") != NETWORK:
        raise CleanupError("network identity mismatch")
    if (network.get("Labels") or {}).get("com.docker.compose.project") != (
        TARGET_PROJECT
    ):
        raise CleanupError("network project identity mismatch")
    members = {
        value.get("Name")
        for value in (network.get("Containers") or {}).values()
    }
    if members != CONTAINERS:
        raise CleanupError("network membership differs from the fixed scope")

    plan = {
        "schema_version": "failed-production-cleanup-plan.v1",
        "project": TARGET_PROJECT,
        "database": TARGET_DATABASE,
        "expected_image_id": expected_image_id,
        "expected_tool_sha": expected_tool_sha,
        "containers": sorted(CONTAINERS),
        "network": NETWORK,
        "volumes": sorted(volumes),
        "named_volumes": sorted(NAMED_VOLUMES),
        "anonymous_volumes": sorted(volumes - NAMED_VOLUMES),
        "volume_mountpoints": dict(sorted(volume_paths.items())),
        "application_filestore_bytes": filestore_bytes,
        "application_filestore_max_bytes": MAX_FAILED_FILESTORE_BYTES,
        "preserved_paths": list(PRESERVED_PATHS),
    }
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    plan["plan_sha256"] = hashlib.sha256(canonical).hexdigest()
    return plan


def _validate_database(runner: Runner) -> None:
    result = _run(
        runner,
        "docker",
        "exec",
        "sc_production-db-1",
        "psql",
        "-U",
        "odoo",
        "-d",
        TARGET_DATABASE,
        "-Atqc",
        "select current_database()",
    )
    if result.stdout.strip() != TARGET_DATABASE:
        raise CleanupError("database identity mismatch")


def _validate_environment(apply: bool) -> tuple[str, str, str, Path]:
    if os.environ.get("ENV") != "prod":
        raise CleanupError("ENV=prod is required")
    if os.environ.get("PRODUCTION_COMPOSE_PROJECT") != TARGET_PROJECT:
        raise CleanupError("PRODUCTION_COMPOSE_PROJECT must be sc_production")
    if os.environ.get("TARGET_DB") != TARGET_DATABASE:
        raise CleanupError("TARGET_DB must be sc_production")
    image_id = os.environ.get("EXPECTED_FAILED_IMAGE_ID", "")
    tool_sha = os.environ.get("EXPECTED_FAILED_DEPLOYMENT_TOOL_SHA", "")
    evidence_raw = os.environ.get("FAILED_CLEANUP_EVIDENCE", "")
    if not image_id.startswith("sha256:") or len(image_id) != 71:
        raise CleanupError("EXPECTED_FAILED_IMAGE_ID must be a full image ID")
    if len(tool_sha) != 40:
        raise CleanupError("EXPECTED_FAILED_DEPLOYMENT_TOOL_SHA must be a full SHA")
    if not evidence_raw:
        raise CleanupError("FAILED_CLEANUP_EVIDENCE is required")
    evidence = Path(evidence_raw)
    if not evidence.is_absolute() or evidence.exists():
        raise CleanupError("FAILED_CLEANUP_EVIDENCE must be a new absolute path")
    plan_sha = os.environ.get("EXPECTED_CLEANUP_PLAN_SHA256", "")
    if apply:
        if os.environ.get("PROD_DANGER") != "1":
            raise CleanupError("PROD_DANGER=1 is required")
        if os.environ.get("CONFIRM_FAILED_DEPLOYMENT_CLEANUP") != CONFIRMATION:
            raise CleanupError("exact failed deployment cleanup confirmation is required")
        if len(plan_sha) != 64:
            raise CleanupError("EXPECTED_CLEANUP_PLAN_SHA256 is required for apply")
    return image_id, tool_sha, plan_sha, evidence


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(runner: Runner = subprocess.run) -> int:
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    if mode not in {"plan", "apply"}:
        raise SystemExit("usage: production_failed_deployment_cleanup.py plan|apply")
    try:
        image_id, tool_sha, expected_plan_sha, evidence = _validate_environment(
            mode == "apply"
        )
        before = preserved_fingerprint()
        _validate_database(runner)
        plan = validate_snapshot(
            collect_snapshot(runner),
            expected_image_id=image_id,
            expected_tool_sha=tool_sha,
        )
        report: dict[str, Any] = {
            "schema_version": "failed-production-cleanup-evidence.v1",
            "mode": mode,
            "status": "PLAN",
            "plan": plan,
            "preserved_before": before,
        }
        if mode == "plan":
            _atomic_json(evidence, report)
            print(
                "[production.failed-deployment.cleanup] PLAN "
                + json.dumps(
                    {
                        "plan_sha256": plan["plan_sha256"],
                        "containers": len(plan["containers"]),
                        "volumes": len(plan["volumes"]),
                        "application_filestore_bytes":
                            plan["application_filestore_bytes"],
                    },
                    sort_keys=True,
                )
            )
            return 0
        if plan["plan_sha256"] != expected_plan_sha:
            raise CleanupError("live cleanup plan differs from approved dry-run")
        with LOCK_PATH.open("w", encoding="utf-8") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _run(runner, "docker", "stop", *plan["containers"])
            _run(runner, "docker", "rm", *plan["containers"])
            _run(runner, "docker", "network", "rm", plan["network"])
            _run(runner, "docker", "volume", "rm", *plan["volumes"])
        after = preserved_fingerprint()
        if after != before:
            raise CleanupError("preserved path fingerprint changed")
        report.update(
            {
                "status": "PASS",
                "removed": {
                    "containers": plan["containers"],
                    "network": plan["network"],
                    "volumes": plan["volumes"],
                },
                "preserved_after": after,
                "production_deployed": False,
            }
        )
        _atomic_json(evidence, report)
    except (
        BlockingIOError,
        CleanupError,
        json.JSONDecodeError,
        OSError,
        subprocess.CalledProcessError,
    ) as exc:
        raise SystemExit(
            f"[production.failed-deployment.cleanup] BLOCKED: {exc}"
        ) from exc
    print("[production.failed-deployment.cleanup] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
