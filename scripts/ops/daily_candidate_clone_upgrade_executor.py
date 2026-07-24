#!/usr/bin/env python3
"""Execute the fixed RC6 upgrade against an isolated daily-candidate clone.

The executor runs on the daily host but never connects a candidate container to
the daily database or mounts daily persistent storage.  It consumes only the
governed paired backup, sentinel evidence and offline-imported immutable image.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import time
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import daily_candidate_clone_upgrade_rehearsal as admission
import daily_candidate_data_continuity as continuity
import daily_candidate_data_sentinel as sentinel
import production_acceptance_harness as acceptance


CANDIDATE_SHA = "fb1f2b5a6e93fb4d7865023e6cda2961848c3cb8"
CANDIDATE_IMAGE_REF = (
    "ghcr.io/lidefend/sce-product@"
    "sha256:02edec2628b276834abd10ec3cc9ef96517fb499c6b0e8a60b19d59e3694fdeb"
)
CANDIDATE_MANIFEST_DIGEST = (
    "sha256:02edec2628b276834abd10ec3cc9ef96517fb499c6b0e8a60b19d59e3694fdeb"
)
CANDIDATE_CONFIG_DIGEST = (
    "sha256:f468dedc5daf5252f9d7631ee6b31a55a164b97d52f5f0e8b71e46035389e244"
)
ACCEPTANCE_PACKAGE_DIGEST = (
    "c0274b881052c463c9d3183843781a81cc42a08789b029de6374b69131298a5c"
)
FIXED_BACKUP = Path(
    "/data/backups/daily_candidate/sc_demo-20260724T032145Z-6eb277d1"
)
FIXED_SENTINEL = Path(
    "/data/backups/daily_candidate/sentinels/"
    "sc_demo-sentinel-20260724T040527Z-1fa42479.json"
)
FIXED_SENTINEL_SHA256 = (
    "1083bae745568fbaef1404c060c76078bec33c4bb7c18a4a9033689c3762257f"
)
EVIDENCE_ROOT = Path("/data/backups/daily_candidate/rehearsals")
DAILY_ENV_FILE = Path("/opt/projects/repos/sce-backend-odoo/.env.dev")
CONFIRMATION = "RUN_FROZEN_RC6_ISOLATED_CLONE_REHEARSAL"
LABEL = "sc.rc6-daily-clone"
MODULES = (
    "sc_norm_engine",
    "smart_construction_bootstrap",
    "smart_core",
    "smart_scene",
    "smart_construction_core",
    "smart_construction_portal",
    "smart_construction_scene",
    "smart_license_core",
    "smart_construction_bundle",
    "smart_construction_seed",
)
CUSTOM_MODULE = "smart_construction_custom"
SAFE_RESOURCE = re.compile(r"^sc-rc6-rehearsal-[a-z0-9-]+$")


class ExecutionError(RuntimeError):
    """A fail-closed clone execution error."""


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(
    args: list[str],
    *,
    input_bytes: bytes | None = None,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> bytes:
    completed = subprocess.run(
        args,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )
    if check and completed.returncode:
        detail = completed.stderr.decode(errors="replace").strip().splitlines()
        summary = detail[-1][:300] if detail else "no diagnostic"
        raise ExecutionError(
            f"command failed ({' '.join(args[:3])}) rc={completed.returncode}: {summary}"
        )
    return completed.stdout


def _run_logged(args: list[str], log: Path) -> None:
    log.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with log.open("wb") as stream:
        completed = subprocess.run(
            args,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
        )
    log.chmod(0o600)
    if completed.returncode:
        raise ExecutionError(
            f"versioned Odoo upgrade failed rc={completed.returncode}; "
            f"see protected log {log}"
        )


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutionError(f"{label} is unavailable or invalid") from exc
    if not isinstance(payload, dict):
        raise ExecutionError(f"{label} must be a JSON object")
    return payload


def _inspect(reference: str) -> dict[str, Any]:
    rows = json.loads(_run(["docker", "image", "inspect", reference]))
    if not isinstance(rows, list) or len(rows) != 1:
        raise ExecutionError(f"image inspection is ambiguous: {reference}")
    return rows[0]


def validate_local_candidate(image: dict[str, Any]) -> dict[str, Any]:
    labels = (image.get("Config") or {}).get("Labels") or {}
    if image.get("Id") != CANDIDATE_CONFIG_DIGEST:
        raise ExecutionError("target daemon image config digest differs from RC6")
    if labels.get("org.opencontainers.image.revision") != CANDIDATE_SHA:
        raise ExecutionError("target daemon OCI revision differs from RC6")
    repo_tags = image.get("RepoTags") or []
    if any(tag.endswith((":latest", ":rc6")) for tag in repo_tags):
        raise ExecutionError("movable RC6 image tag is present")
    return {
        "image_config_digest": CANDIDATE_CONFIG_DIGEST,
        "oci_revision": CANDIDATE_SHA,
        "oci_revision_match": True,
    }


def validate_offline_archive(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
        raise ExecutionError("offline RC6 archive is missing or unsafe")
    try:
        with tarfile.open(path) as archive:
            rows = json.load(archive.extractfile("manifest.json"))
            if not isinstance(rows, list) or len(rows) != 1:
                raise ExecutionError("offline archive must contain one image")
            row = rows[0]
            if row.get("RepoTags"):
                raise ExecutionError("offline archive must not carry movable tags")
            config_name = str(row.get("Config") or "")
            expected = "blobs/sha256/" + CANDIDATE_CONFIG_DIGEST.removeprefix(
                "sha256:"
            )
            if config_name != expected:
                raise ExecutionError("offline archive config digest differs")
            config = json.load(archive.extractfile(config_name))
    except (tarfile.TarError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ExecutionError("offline RC6 archive is invalid") from exc
    labels = (config.get("config") or {}).get("Labels") or {}
    if labels.get("org.opencontainers.image.revision") != CANDIDATE_SHA:
        raise ExecutionError("offline archive OCI revision differs")
    return {
        "archive_sha256": _sha256(path),
        "archive_tag_count": 0,
        "image_config_digest": CANDIDATE_CONFIG_DIGEST,
        "oci_revision_match": True,
    }


def _load_clone_identity(path: Path) -> tuple[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ExecutionError("daily clone identity source is unavailable") from exc
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key in {"SC_BOOTSTRAP_LOGIN", "SC_BOOTSTRAP_SECRET"}:
            values[key] = value
    login = values.get("SC_BOOTSTRAP_LOGIN", "").strip()
    secret = values.get("SC_BOOTSTRAP_SECRET", "")
    if not login or not secret:
        raise ExecutionError("approved clone login identity is not configured")
    return login, secret


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _no_leftovers() -> bool:
    checks = (
        ["docker", "ps", "-aq", "--filter", f"label={LABEL}=true"],
        ["docker", "volume", "ls", "-q", "--filter", f"label={LABEL}=true"],
        ["docker", "network", "ls", "-q", "--filter", f"label={LABEL}=true"],
    )
    return not any(_run(command).decode().split() for command in checks)


def _resource_name(prefix: str, suffix: str) -> str:
    value = f"{prefix}-{suffix}"
    if not SAFE_RESOURCE.fullmatch(value):
        raise ExecutionError(f"unsafe rehearsal resource name: {suffix}")
    return value


def _query_module_versions(container: str) -> dict[str, str]:
    names = ",".join("'" + item.replace("'", "''") + "'" for item in MODULES)
    sql = (
        "SELECT name||'|'||COALESCE(latest_version,'') FROM ir_module_module "
        f"WHERE state='installed' AND name IN ({names}) ORDER BY name"
    )
    rows = _run(
        [
            "docker",
            "exec",
            container,
            "psql",
            "-X",
            "-U",
            "odoo",
            "-d",
            "sc_demo",
            "-At",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            sql,
        ]
    ).decode().splitlines()
    return dict(line.split("|", 1) for line in rows if "|" in line)


def _target_module_versions() -> dict[str, str]:
    script = r"""
import ast,json,pathlib
names=json.loads(__import__("os").environ["RC6_MODULES"])
result={}
for name in names:
    path=pathlib.Path("/mnt/product-addons")/name/"__manifest__.py"
    if not path.is_file():
        raise SystemExit("missing candidate module: "+name)
    payload=ast.literal_eval(path.read_text())
    result[name]=str(payload.get("version") or "")
print(json.dumps(result,sort_keys=True))
"""
    env_value = json.dumps(list(MODULES))
    raw = _run(
        [
            "docker",
            "run",
            "--rm",
            "--pull",
            "never",
            "--network",
            "none",
            "-e",
            f"RC6_MODULES={env_value}",
            "--entrypoint",
            "python3",
            CANDIDATE_CONFIG_DIGEST,
            "-c",
            script,
        ]
    )
    result = json.loads(raw)
    if set(result) != set(MODULES) or any(not value for value in result.values()):
        raise ExecutionError("candidate module version inventory is incomplete")
    return result


def _daily_preflight() -> dict[str, Any]:
    continuity_contract = continuity._load_contract(continuity.DEFAULT_CONTRACT)
    sentinel_contract = sentinel._load_contract(sentinel.DEFAULT_CONTRACT)
    manifest = continuity.validate_backup(
        continuity_contract, FIXED_BACKUP, strict_permissions=True
    )
    if manifest.get("backup_set_id") != FIXED_BACKUP.name:
        raise ExecutionError("paired backup identity differs")
    if _sha256(FIXED_SENTINEL) != FIXED_SENTINEL_SHA256:
        raise ExecutionError("fixed sentinel evidence digest differs")
    runtime = continuity._assert_runtime(continuity_contract)
    if not runtime["source_revision"].startswith("6095e201"):
        raise ExecutionError("daily running application revision differs")
    if runtime["source_worktree_dirty"]:
        raise ExecutionError("daily running repository is dirty")
    baseline = continuity.baseline(continuity_contract)
    if baseline["sentinels"]["database_uuid"] != "c838b4b6-4cd6-11f1-9590-82245e4e7b62":
        raise ExecutionError("daily database UUID differs")
    sentinel_payload = _load_json(FIXED_SENTINEL, "fixed sentinel evidence")
    if sentinel_payload.get("database_uuid") != baseline["sentinels"]["database_uuid"]:
        raise ExecutionError("sentinel database UUID differs")
    image_identity = validate_local_candidate(_inspect(CANDIDATE_CONFIG_DIGEST))
    disk = shutil.disk_usage(EVIDENCE_ROOT.parent)
    required = (
        int(manifest.get("database_bytes") or 0) * 3
        + int(manifest.get("filestore_bytes") or 0) * 3
        + 8 * 1024**3
    )
    if disk.free < required:
        raise ExecutionError("insufficient disk space for clone and rollback proof")
    if not _no_leftovers():
        raise ExecutionError("an earlier RC6 clone rehearsal resource remains")
    return {
        "continuity_contract": continuity_contract,
        "sentinel_contract": sentinel_contract,
        "manifest": manifest,
        "sentinel": sentinel_payload,
        "runtime": runtime,
        "baseline": baseline,
        "image_identity": image_identity,
        "available_disk_bytes": disk.free,
        "required_disk_bytes": required,
    }


class Resources:
    def __init__(self) -> None:
        self.containers: list[str] = []
        self.volumes: list[str] = []
        self.networks: list[str] = []

    def network(self, name: str) -> None:
        _run(
            [
                "docker",
                "network",
                "create",
                "--internal",
                "--label",
                f"{LABEL}=true",
                name,
            ]
        )
        self.networks.append(name)

    def volume(self, name: str) -> None:
        _run(["docker", "volume", "create", "--label", f"{LABEL}=true", name])
        self.volumes.append(name)

    def container(self, name: str) -> None:
        self.containers.append(name)

    def cleanup(self) -> bool:
        for name in reversed(self.containers):
            _run(["docker", "rm", "-f", name], check=False)
        for name in reversed(self.volumes):
            _run(["docker", "volume", "rm", name], check=False)
        for name in reversed(self.networks):
            _run(["docker", "network", "rm", name], check=False)
        return _no_leftovers()


def _create_data_clone(
    prefix: str,
    resources: Resources,
    preflight: dict[str, Any],
) -> dict[str, str]:
    network = _resource_name(prefix, "net")
    db_volume = _resource_name(prefix, "db-volume")
    fs_volume = _resource_name(prefix, "fs-volume")
    session_volume = _resource_name(prefix, "session-volume")
    tmp_volume = _resource_name(prefix, "tmp-volume")
    log_volume = _resource_name(prefix, "log-volume")
    config_volume = _resource_name(prefix, "config-volume")
    redis_volume = _resource_name(prefix, "redis-volume")
    custom_volume = _resource_name(prefix, "custom-volume")
    db_container = _resource_name(prefix, "postgres")
    fs_container = _resource_name(prefix, "filestore")
    redis_container = _resource_name(prefix, "redis")
    resources.network(network)
    for volume in (
        db_volume,
        fs_volume,
        session_volume,
        tmp_volume,
        log_volume,
        config_volume,
        redis_volume,
        custom_volume,
    ):
        resources.volume(volume)
    db_secret = secrets.token_urlsafe(32)
    _run(
        [
            "docker",
            "run",
            "-d",
            "--pull",
            "never",
            "--name",
            db_container,
            "--network",
            network,
            "--network-alias",
            "db",
            "--label",
            f"{LABEL}=true",
            "-e",
            "POSTGRES_USER=odoo",
            "-e",
            f"POSTGRES_PASSWORD={db_secret}",
            "-e",
            "POSTGRES_DB=postgres",
            "-v",
            f"{db_volume}:/var/lib/postgresql/data",
            preflight["runtime"]["database_image_id"],
        ]
    )
    resources.container(db_container)
    continuity._wait_postgres(db_container)
    _run(["docker", "exec", db_container, "createdb", "-U", "odoo", "sc_demo"])
    continuity._run_from_file(
        [
            "docker",
            "exec",
            "-i",
            db_container,
            "pg_restore",
            "-U",
            "odoo",
            "-d",
            "sc_demo",
            "--no-owner",
            "--no-privileges",
        ],
        FIXED_BACKUP / "database.dump",
    )
    continuity._run_from_file(
        [
            "docker",
            "run",
            "--rm",
            "-i",
            "--pull",
            "never",
            "--network",
            "none",
            "--user",
            "0:0",
            "-v",
            f"{fs_volume}:/var/lib/odoo/filestore",
            "--entrypoint",
            "sh",
            CANDIDATE_CONFIG_DIGEST,
            "-c",
            "set -eu; tar -C /var/lib/odoo/filestore -xzf -",
        ],
        FIXED_BACKUP / "filestore.tar.gz",
    )
    _run(
        [
            "docker",
            "run",
            "-d",
            "--pull",
            "never",
            "--name",
            fs_container,
            "--network",
            "none",
            "--user",
            "0:0",
            "--label",
            f"{LABEL}=true",
            "-v",
            f"{fs_volume}:/var/lib/odoo/filestore:ro",
            "--entrypoint",
            "sh",
            CANDIDATE_CONFIG_DIGEST,
            "-c",
            "sleep 7200",
        ]
    )
    resources.container(fs_container)
    redis_image = _inspect("redis:7-alpine")["Id"]
    _run(
        [
            "docker",
            "run",
            "-d",
            "--pull",
            "never",
            "--name",
            redis_container,
            "--network",
            network,
            "--network-alias",
            "redis",
            "--label",
            f"{LABEL}=true",
            "-v",
            f"{redis_volume}:/data",
            redis_image,
            "redis-server",
            "--appendonly",
            "yes",
        ]
    )
    resources.container(redis_container)
    source_repository = Path(
        preflight["continuity_contract"]["source_repository"]
    )
    custom_archive = _run(
        [
            "git",
            "-C",
            str(source_repository),
            "archive",
            "HEAD",
            "addons/smart_construction_custom",
        ]
    )
    _run(
        [
            "docker",
            "run",
            "--rm",
            "-i",
            "--network",
            "none",
            "-v",
            f"{custom_volume}:/mnt/customer-addons",
            "--entrypoint",
            "sh",
            CANDIDATE_CONFIG_DIGEST,
            "-c",
            "set -eu; tar -C /mnt/customer-addons "
            "--strip-components=1 -xf -",
        ],
        input_bytes=custom_archive,
    )
    return {
        "network": network,
        "db_volume": db_volume,
        "fs_volume": fs_volume,
        "session_volume": session_volume,
        "tmp_volume": tmp_volume,
        "log_volume": log_volume,
        "config_volume": config_volume,
        "custom_volume": custom_volume,
        "db_container": db_container,
        "fs_container": fs_container,
        "redis_container": redis_container,
        "db_secret": db_secret,
    }


def _clone_capture(
    preflight: dict[str, Any], clone: dict[str, str], source_kind: str
) -> dict[str, Any]:
    return sentinel.capture(
        preflight["sentinel_contract"],
        db_container=clone["db_container"],
        odoo_container=clone["fs_container"],
        source_kind=source_kind,
        runtime={
            "restored_from_backup_set_id": FIXED_BACKUP.name,
            "candidate_revision": CANDIDATE_SHA,
            "network_egress": "internal_only",
        },
    )


def _odoo_common(clone: dict[str, str]) -> list[str]:
    return [
        "--network",
        clone["network"],
        "--label",
        f"{LABEL}=true",
        "-e",
        "DB_HOST=db",
        "-e",
        "DB_PORT=5432",
        "-e",
        "DB_USER=odoo",
        "-e",
        f"DB_PASSWORD={clone['db_secret']}",
        "-e",
        "DB_NAME=sc_demo",
        "-e",
        "ODOO_DB=sc_demo",
        "-e",
        "ODOO_DBFILTER=^sc_demo$",
        "-e",
        "PLATFORM_RELEASE_DB=sc_demo",
        "-e",
        "SC_ENVIRONMENT=release_rehearsal",
        "-e",
        "SC_ALLOW_DEMO_DATA=0",
        "-e",
        "SC_FILESTORE_SCOPE=sc_demo",
        "-e",
        "REDIS_HOST=redis",
        "-e",
        "TMPDIR=/opt/sce-runtime/tmp",
        "-v",
        f"{clone['fs_volume']}:/opt/sce-runtime/filestore",
        "-v",
        f"{clone['session_volume']}:/opt/sce-runtime/sessions",
        "-v",
        f"{clone['tmp_volume']}:/opt/sce-runtime/tmp",
        "-v",
        f"{clone['log_volume']}:/opt/sce-runtime/logs",
        "-v",
        f"{clone['config_volume']}:/opt/sce-runtime/config",
        "-v",
        f"{clone['custom_volume']}:/mnt/customer-addons:ro",
    ]


def _upgrade(
    prefix: str,
    clone: dict[str, str],
    resources: Resources,
    log: Path,
    attempt: str,
) -> None:
    container = _resource_name(prefix, f"upgrade-{attempt}")
    command = [
        "docker",
        "run",
        "--rm",
        "--pull",
        "never",
        "--name",
        container,
        *_odoo_common(clone),
        "--entrypoint",
        "odoo",
        CANDIDATE_CONFIG_DIGEST,
        "--db_host=db",
        "--db_port=5432",
        "--db_user=odoo",
        f"--db_password={clone['db_secret']}",
        "--database=sc_demo",
        "--addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/product-addons,/mnt/customer-addons,/mnt/addons_external/oca_server_ux",
        "--data-dir=/opt/sce-runtime",
        "--no-http",
        "--workers=0",
        "--max-cron-threads=0",
        "--without-demo=all",
        "--update=" + ",".join((*MODULES, CUSTOM_MODULE)),
        "--stop-after-init",
    ]
    _run_logged(command, log)


def _wait_http(port: int, path: str = "/") -> None:
    import urllib.error
    import urllib.request

    deadline = time.monotonic() + 300
    url = f"http://127.0.0.1:{port}{path}"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(2)
    raise ExecutionError(f"clone HTTP health did not pass on port {port}")


def _start_candidate_runtime(
    prefix: str,
    clone: dict[str, str],
    resources: Resources,
) -> tuple[str, str, int]:
    odoo = _resource_name(prefix, "odoo")
    nginx = _resource_name(prefix, "nginx")
    port = _free_port()
    admin_secret = secrets.token_urlsafe(32)
    jwt_secret = secrets.token_urlsafe(48)
    shell = (
        "set -eu; "
        "python3 /usr/local/bin/render_odoo_conf.py "
        "/etc/odoo/odoo.conf.template /opt/sce-runtime/config/odoo.conf; "
        "exec odoo -c /opt/sce-runtime/config/odoo.conf "
        "--workers=0 --max-cron-threads=0"
    )
    _run(
        [
            "docker",
            "run",
            "-d",
            "--pull",
            "never",
            "--name",
            odoo,
            *_odoo_common(clone),
            "--network-alias",
            "odoo",
            "-e",
            f"ADMIN_PASSWD={admin_secret}",
            "-e",
            f"JWT_SECRET={jwt_secret}",
            "--entrypoint",
            "sh",
            CANDIDATE_CONFIG_DIGEST,
            "-c",
            shell,
        ]
    )
    resources.container(odoo)
    _run(
        [
            "docker",
            "run",
            "-d",
            "--pull",
            "never",
            "--name",
            nginx,
            "--network",
            clone["network"],
            "--label",
            f"{LABEL}=true",
            "-p",
            f"127.0.0.1:{port}:80",
            "-e",
            "ODOO_DB=sc_demo",
            "--entrypoint",
            "/usr/local/bin/render_nginx_conf.sh",
            CANDIDATE_CONFIG_DIGEST,
        ]
    )
    resources.container(nginx)
    _wait_http(port)
    return odoo, nginx, port


def _stop_runtime(resources: Resources, *names: str) -> None:
    for name in names:
        _run(["docker", "rm", "-f", name], check=False)
        if name in resources.containers:
            resources.containers.remove(name)


def _accept(port: int, login: str, secret: str) -> dict[str, Any]:
    if acceptance.package_digest() != ACCEPTANCE_PACKAGE_DIGEST:
        raise ExecutionError("immutable acceptance package digest differs")
    report = acceptance.run_acceptance(
        base_url=f"http://127.0.0.1:{port}",
        db_name="sc_demo",
        login=login,
        password=secret,
        run_count=1,
        timeout=30,
    )
    if report.get("status") != "PASS":
        raise ExecutionError("fixed real-HTTP acceptance failed")
    run = report["runs"][0]
    return {
        "package_digest": report["package_digest"],
        "frontend_pass": report["frontend"]["pass"],
        "login_pass": run["login_pass"],
        "system_init_pass": run["system_init_pass"],
        "navigation_pass": run["navigation_pass"],
        "core_read_pass": run["core_read_acceptance_pass"],
        "role_boundary_pass": run["core_role_acceptance_pass"],
        "permission_boundary_pass": run["permission_boundary_pass"],
    }


def _duplicate_xmlids(container: str) -> int:
    raw = _run(
        [
            "docker",
            "exec",
            container,
            "psql",
            "-X",
            "-U",
            "odoo",
            "-d",
            "sc_demo",
            "-At",
            "-c",
            "SELECT count(*) FROM (SELECT module,name FROM ir_model_data "
            "GROUP BY module,name HAVING count(*)>1) d;",
        ]
    ).decode().strip()
    return int(raw)


def _start_rollback_runtime(
    prefix: str,
    clone: dict[str, str],
    resources: Resources,
    source_image: str,
    source_repository: Path,
) -> tuple[str, int]:
    source_volume = _resource_name(prefix, "source-volume")
    resources.volume(source_volume)
    archive = _run(["git", "-C", str(source_repository), "archive", "HEAD"])
    _run(
        [
            "docker",
            "run",
            "--rm",
            "-i",
            "--network",
            "none",
            "-v",
            f"{source_volume}:/mnt/source",
            "--entrypoint",
            "tar",
            source_image,
            "-C",
            "/mnt/source",
            "-xf",
            "-",
        ],
        input_bytes=archive,
    )
    container = _resource_name(prefix, "rollback-odoo")
    port = _free_port()
    _run(
        [
            "docker",
            "run",
            "-d",
            "--pull",
            "never",
            "--name",
            container,
            "--network",
            clone["network"],
            "--label",
            f"{LABEL}=true",
            "-p",
            f"127.0.0.1:{port}:8069",
            "-v",
            f"{source_volume}:/mnt/source:ro",
            "-v",
            f"{clone['fs_volume']}:/var/lib/odoo/filestore:rw",
            "--entrypoint",
            "odoo",
            source_image,
            "--db_host=db",
            "--db_port=5432",
            "--db_user=odoo",
            f"--db_password={clone['db_secret']}",
            "--database=sc_demo",
            "--db-filter=^sc_demo$",
            "--addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/source/addons,/mnt/source/addons_external/oca_server_ux",
            "--data-dir=/var/lib/odoo",
            "--workers=0",
            "--max-cron-threads=0",
            "--without-demo=all",
        ]
    )
    resources.container(container)
    _wait_http(port, "/web/login?db=sc_demo")
    return container, port


def execute() -> tuple[dict[str, Any], Path, str]:
    if os.environ.get("CONFIRM_RC6_DAILY_CLONE_REHEARSAL") != CONFIRMATION:
        raise ExecutionError("exact clone rehearsal confirmation is required")
    started = time.monotonic()
    started_at = _utc()
    preflight = _daily_preflight()
    runtime_before = preflight["runtime"].copy()
    login, secret = _load_clone_identity(DAILY_ENV_FILE)
    target_versions = _target_module_versions()
    identifier = (
        "sc_demo-rc6-rehearsal-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + secrets.token_hex(4)
    )
    evidence_dir = EVIDENCE_ROOT / identifier
    evidence_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    evidence_dir.chmod(0o700)
    resources = Resources()
    success = False
    cleanup_pass = False
    evidence: dict[str, Any] = {
        "rehearsal_set_id": identifier,
        "started_at": started_at,
        "control_tool_revision": continuity._tool_revision(),
        "candidate_sha": CANDIDATE_SHA,
        "candidate_image_ref": CANDIDATE_IMAGE_REF,
        "candidate_manifest_digest": CANDIDATE_MANIFEST_DIGEST,
        "candidate_config_digest": CANDIDATE_CONFIG_DIGEST,
        "oci_revision_match": True,
        "source_database_uuid": preflight["baseline"]["sentinels"]["database_uuid"],
        "source_backup_set_id": FIXED_BACKUP.name,
        "source_database_backup_sha256": preflight["manifest"]["checksums"][
            "database.dump"
        ],
        "source_filestore_backup_sha256": preflight["manifest"]["checksums"][
            "filestore.tar.gz"
        ],
        "database_filestore_pair_verified": True,
        "daily_read_only_access_only": True,
        "daily_application_upgraded": False,
        "daily_database_upgraded": False,
        "daily_filestore_modified": False,
        "production_accessed": False,
    }
    try:
        prefix = "sc-rc6-rehearsal-" + secrets.token_hex(4)
        clone = _create_data_clone(prefix, resources, preflight)
        pre_capture = _clone_capture(
            preflight, clone, "RC6_PRE_UPGRADE_ISOLATED_CLONE"
        )
        pre_compare = sentinel.compare(
            preflight["sentinel_contract"],
            preflight["sentinel"],
            pre_capture,
            restore_equivalence=True,
        )
        if not pre_compare["pass"]:
            raise ExecutionError("pre-upgrade clone sentinel comparison failed")
        old_versions = _query_module_versions(clone["db_container"])
        plan_input = {
            "old_modules": old_versions,
            "target_modules": {
                name: target_versions[name] for name in old_versions if name in target_versions
            },
            "upgrade_commands": [
                "odoo --update="
                + ",".join((*MODULES, CUSTOM_MODULE))
                + " --stop-after-init"
            ],
            "operations": [],
            "model_mappings": [],
            "demo_or_fixture_write": False,
            "unknown_origin_delete": False,
            "backward_compatible": False,
            "plan_versioned": True,
        }
        migration_plan = admission.build_migration_plan(
            admission.load_contract(), plan_input
        )
        if not migration_plan["migration_plan_versioned"]:
            raise ExecutionError("migration plan is not versioned")
        first_started = time.monotonic()
        _upgrade(
            prefix,
            clone,
            resources,
            evidence_dir / "logs" / "upgrade-first.log",
            "first",
        )
        first_duration = int(time.monotonic() - first_started)
        odoo, nginx, port = _start_candidate_runtime(prefix, clone, resources)
        first_acceptance = _accept(port, login, secret)
        post_capture = _clone_capture(
            preflight, clone, "RC6_POST_UPGRADE_ISOLATED_CLONE"
        )
        allowed_versions = {
            row["module"]: target_versions.get(row["module"], row["version"])
            for row in preflight["sentinel"]["installed_core_modules"]
        }
        post_compare = sentinel.compare(
            preflight["sentinel_contract"],
            pre_capture,
            post_capture,
            allowed_core_module_versions=allowed_versions,
        )
        preservation = admission.validate_sentinel_preservation(
            {
                "comparison_pass": post_compare["pass"],
                "fixed_sample_preservation_pass": not any(
                    row.startswith("FIXED_SAMPLE_") for row in post_compare["failures"]
                ),
                "core_relationship_preservation_pass": not any(
                    row.startswith("ORPHAN_") for row in post_compare["failures"]
                ),
                "attachment_preservation_pass": not any(
                    row.startswith("ATTACHMENT_") for row in post_compare["failures"]
                ),
                "orphan_regression_pass": not any(
                    row.startswith("ORPHAN_") for row in post_compare["failures"]
                ),
                "unknown_origin_preservation_pass": all(
                    post_capture["classifications"][model].get("UNKNOWN_ORIGIN", 0)
                    >= row.get("UNKNOWN_ORIGIN", 0)
                    for model, row in pre_capture["classifications"].items()
                ),
            }
        )
        _stop_runtime(resources, nginx, odoo)
        _upgrade(
            prefix,
            clone,
            resources,
            evidence_dir / "logs" / "upgrade-second.log",
            "second",
        )
        odoo2, nginx2, port2 = _start_candidate_runtime(prefix, clone, resources)
        second_acceptance = _accept(port2, login, secret)
        repeat_capture = _clone_capture(
            preflight, clone, "RC6_REPEAT_UPGRADE_ISOLATED_CLONE"
        )
        repeat_compare = sentinel.compare(
            preflight["sentinel_contract"],
            post_capture,
            repeat_capture,
            allowed_core_module_versions=allowed_versions,
        )
        repeated = admission.validate_repeated_upgrade(
            {
                "same_entrypoint": True,
                "exit_code_zero": True,
                "business_record_delta_zero": all(
                    repeat_capture["aggregates"][model]["record_count"]
                    == row["record_count"]
                    for model, row in post_capture["aggregates"].items()
                ),
                "duplicate_xmlid_count_zero": _duplicate_xmlids(
                    clone["db_container"]
                )
                == 0,
                "permission_regression_absent": second_acceptance[
                    "permission_boundary_pass"
                ],
                "post_repeat_sentinel_compare_pass": repeat_compare["pass"],
            }
        )
        rollback_prefix = "sc-rc6-rehearsal-" + secrets.token_hex(4)
        rollback = _create_data_clone(rollback_prefix, resources, preflight)
        rollback_capture = _clone_capture(
            preflight, rollback, "RC6_PAIRED_ROLLBACK_ISOLATED_CLONE"
        )
        rollback_compare = sentinel.compare(
            preflight["sentinel_contract"],
            preflight["sentinel"],
            rollback_capture,
            restore_equivalence=True,
        )
        if not rollback_compare["pass"]:
            raise ExecutionError("paired rollback sentinel comparison failed")
        rollback_app, _rollback_port = _start_rollback_runtime(
            rollback_prefix,
            rollback,
            resources,
            preflight["runtime"]["odoo_image_id"],
            Path(preflight["continuity_contract"]["source_repository"]),
        )
        if not _run(
            ["docker", "inspect", rollback_app, "--format", "{{.State.Running}}"]
        ).decode().strip() == "true":
            raise ExecutionError("rollback application did not stay running")
        evidence.update(
            {
                "clone_isolation_pass": True,
                "external_side_effects_blocked": True,
                "pre_upgrade_sentinels_pass": True,
                "migration_plan": migration_plan,
                "first_upgrade_pass": True,
                "first_upgrade_duration_seconds": first_duration,
                "application_health_pass": True,
                "first_acceptance": first_acceptance,
                "historical_data_sentinels_pass": preservation["comparison_pass"],
                "attachment_sentinels_pass": preservation[
                    "attachment_preservation_pass"
                ],
                "role_and_permission_sentinels_pass": first_acceptance[
                    "role_boundary_pass"
                ]
                and first_acceptance["permission_boundary_pass"],
                "second_acceptance": second_acceptance,
                "second_upgrade_idempotency_pass": repeated[
                    "migration_idempotency_pass"
                ],
                "post_repeat_sentinel_compare_pass": repeated[
                    "post_repeat_sentinel_compare_pass"
                ],
                "rollback_restore_pass": True,
                "rollback_application_health_pass": True,
                "rollback_sentinel_compare_pass": True,
            }
        )
        _stop_runtime(resources, nginx2, odoo2)
        success = True
    except Exception as exc:
        evidence["failure_class"] = type(exc).__name__
        evidence["failure_summary"] = str(exc)[:500]
        raise
    finally:
        cleanup_pass = resources.cleanup()
        runtime_after = continuity._assert_runtime(preflight["continuity_contract"])
        evidence.update(
            {
                "finished_at": _utc(),
                "duration_seconds": int(time.monotonic() - started),
                "temporary_resources_cleaned": cleanup_pass,
                "daily_container_id_unchanged": (
                    runtime_before["odoo_container_id"]
                    == runtime_after["odoo_container_id"]
                ),
                "daily_container_started_at_unchanged": (
                    runtime_before["odoo_started_at"]
                    == runtime_after["odoo_started_at"]
                ),
                "daily_source_revision_unchanged": (
                    runtime_before["source_revision"]
                    == runtime_after["source_revision"]
                ),
                "result": (
                    "PASS_RC6_DAILY_CANDIDATE_CLONE_UPGRADE_REHEARSAL"
                    if success and cleanup_pass
                    else "FAIL_RC6_DAILY_CANDIDATE_CLONE_UPGRADE_REHEARSAL"
                ),
            }
        )
        evidence_path = evidence_dir / "rehearsal.json"
        evidence_sha = admission.atomic_write_evidence(evidence_path, evidence)
    if not success or not cleanup_pass:
        raise ExecutionError("clone rehearsal did not complete successfully")
    return evidence, evidence_path, evidence_sha


def preflight() -> dict[str, Any]:
    result = _daily_preflight()
    return {
        **result["image_identity"],
        "source_database_uuid": result["baseline"]["sentinels"]["database_uuid"],
        "source_backup_set_id": result["manifest"]["backup_set_id"],
        "source_database_backup_sha256": result["manifest"]["checksums"][
            "database.dump"
        ],
        "source_filestore_backup_sha256": result["manifest"]["checksums"][
            "filestore.tar.gz"
        ],
        "database_filestore_pair_verified": True,
        "daily_source_revision": result["runtime"]["source_revision"],
        "daily_read_only_access_only": True,
        "production_accessed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=("verify-offline-archive", "preflight", "execute")
    )
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    if args.action == "verify-offline-archive":
        if args.archive is None:
            raise ExecutionError("--archive is required")
        result = validate_offline_archive(args.archive)
    elif args.action == "preflight":
        result = preflight()
    else:
        evidence, path, digest = execute()
        result = {
            "result": evidence["result"],
            "evidence_path": str(path),
            "evidence_sha256": digest,
            "temporary_resources_cleaned": evidence["temporary_resources_cleaned"],
        }
    print("RC6_DAILY_CLONE_EXECUTOR=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ExecutionError, continuity.ContinuityError, sentinel.SentinelError) as exc:
        raise SystemExit(f"RC6_DAILY_CLONE_EXECUTOR_ERROR={exc}") from exc
