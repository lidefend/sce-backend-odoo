#!/usr/bin/env python3
"""Governed sc_production triple backup and isolated restore rehearsal.

This program is installed as an operations tool.  It never deploys an
application image and never changes the production database.  Production
access is limited to pg_dump, read-only identity queries, docker inspect, and
filestore archive reads.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import stat
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


CONTRACT_VERSION = "production_backup_restore.v1"
PROJECT = "sc_production"
DATABASE = "sc_production"
STALE_DATABASE = "sc_prod"
STALE_CONTAINER = "sc-backend-odoo-prod-db-1"
BACKUP_ID = re.compile(r"^sc_production-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
RESTORE_ID = re.compile(r"^sc_restore_[0-9]{8}t[0-9]{6}z_[0-9a-f]{8}$")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
ODOO_IMAGE_REF = re.compile(
    r"^ghcr\.io/lidefend/sce-product@sha256:[0-9a-f]{64}$"
)
POSTGRES_IMAGE_REF = re.compile(
    r"^(?:docker\.io/library/)?postgres(?::15)?@sha256:[0-9a-f]{64}$"
)
SAFE_CONTAINER = re.compile(r"^sc_production-(?:db|odoo)-1$")
ARTIFACTS = (
    "database.dump",
    "filestore.tar.gz",
    "deployment-metadata.json",
)
SENSITIVE_KEY = re.compile(
    r"(?:password|passwd|secret|token|cookie|authorization|private.?key|"
    r"database_url|dsn|connection.?string)",
    re.IGNORECASE,
)
SAFE_ODOO_OPTIONS = (
    "addons_path",
    "dbfilter",
    "proxy_mode",
    "workers",
    "max_cron_threads",
    "list_db",
    "db_host",
    "db_port",
    "db_user",
    "data_dir",
)
COUNT_TABLES = (
    "res_users",
    "ir_attachment",
    "ir_module_module",
    "project_project",
)


class ContractError(RuntimeError):
    pass


Runner = Callable[..., bytes]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(args: list[str], *, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        args,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        message = result.stderr.decode(errors="replace").strip()
        raise ContractError(f"command failed ({args[0]}): {message[:500]}")
    return result.stdout


def atomic_json(path: Path, payload: dict[str, Any], mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.chmod(mode)
        os.replace(temporary_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary_path.unlink(missing_ok=True)


def safe_root(path: Path, expected: Path) -> Path:
    if path != expected or not path.is_absolute() or path == Path("/"):
        raise ContractError(f"path must be exactly {expected}")
    if path.is_symlink():
        raise ContractError("scoped root must not be a symlink")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    resolved = path.resolve(strict=True)
    if resolved != path or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ContractError("scoped root must be a real 0700 directory")
    return path


def validate_backup_id(value: str) -> str:
    if not BACKUP_ID.fullmatch(value):
        raise ContractError("backup_set_id is invalid")
    return value


def new_backup_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"sc_production-{stamp}-{secrets.token_hex(4)}"


def _required(name: str) -> str:
    value = str(os.environ.get(name) or "").strip()
    if not value:
        raise ContractError(f"{name} is required")
    return value


@dataclass(frozen=True)
class Settings:
    project: str
    database: str
    db_container: str
    odoo_container: str
    db_user: str
    filestore_root: str
    backup_root: Path
    tool_source_sha: str
    encryption_status: str
    retention_days: int

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            settings = cls(
                project=_required("BACKUP_COMPOSE_PROJECT"),
                database=_required("BACKUP_TARGET_DB"),
                db_container=_required("BACKUP_DB_CONTAINER"),
                odoo_container=_required("BACKUP_ODOO_CONTAINER"),
                db_user=_required("BACKUP_DB_USER"),
                filestore_root=_required("BACKUP_FILESTORE_ROOT").rstrip("/"),
                backup_root=Path(_required("BACKUP_ROOT")),
                tool_source_sha=_required("BACKUP_TOOL_SOURCE_SHA"),
                encryption_status=_required("BACKUP_ENCRYPTION_STATUS"),
                retention_days=int(_required("BACKUP_RETENTION_DAYS")),
            )
        except ValueError as exc:
            raise ContractError("backup retention days must be an integer") from exc
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.project != PROJECT or self.database != DATABASE:
            raise ContractError("production project and database must be sc_production")
        if self.database == STALE_DATABASE:
            raise ContractError("stale sc_prod database identity is forbidden")
        for container in (self.db_container, self.odoo_container):
            if container == STALE_CONTAINER or not SAFE_CONTAINER.fullmatch(container):
                raise ContractError("production container identity is not approved")
        if self.db_container != "sc_production-db-1":
            raise ContractError("database container identity mismatch")
        if self.odoo_container != "sc_production-odoo-1":
            raise ContractError("Odoo container identity mismatch")
        if self.filestore_root != "/opt/sce-runtime/filestore":
            raise ContractError("filestore root identity mismatch")
        if self.backup_root != Path("/data/backups/sc_production"):
            raise ContractError("backup root identity mismatch")
        if not FULL_SHA.fullmatch(self.tool_source_sha):
            raise ContractError("backup tool source SHA must be a full commit SHA")
        if self.encryption_status not in {
            "encrypted_at_rest",
            "external_encryption_verified",
            "not_encrypted",
        }:
            raise ContractError("backup encryption status is invalid")
        if not 1 <= self.retention_days <= 3650:
            raise ContractError("backup retention days are invalid")


class NonBlockingLock:
    def __init__(self, path: Path):
        self.path = path
        self.descriptor: int | None = None

    def __enter__(self) -> "NonBlockingLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(self.descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(self.descriptor)
            self.descriptor = None
            raise ContractError("backup/restore lock is already held") from exc
        os.ftruncate(self.descriptor, 0)
        os.write(
            self.descriptor,
            f"pid={os.getpid()} contract={CONTRACT_VERSION}\n".encode(),
        )
        return self

    def __exit__(self, *_args: object) -> None:
        if self.descriptor is not None:
            fcntl.flock(self.descriptor, fcntl.LOCK_UN)
            os.close(self.descriptor)
            self.descriptor = None


def _docker_json(args: list[str], runner: Runner) -> Any:
    return json.loads(runner(["docker", *args]).decode())


def _environment_names(inspect: dict[str, Any]) -> list[str]:
    names = []
    for value in inspect.get("Config", {}).get("Env") or []:
        name = value.split("=", 1)[0]
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
            names.append(name)
    return sorted(set(names))


def _safe_mounts(inspect: dict[str, Any]) -> list[dict[str, str]]:
    mounts = []
    for value in inspect.get("Mounts") or []:
        mounts.append(
            {
                "type": str(value.get("Type") or ""),
                "name": str(value.get("Name") or ""),
                "destination": str(value.get("Destination") or ""),
                "mode": str(value.get("Mode") or ""),
                "rw": str(bool(value.get("RW"))).lower(),
            }
        )
    return mounts


def _safe_labels(inspect: dict[str, Any]) -> dict[str, str]:
    labels = inspect.get("Config", {}).get("Labels") or {}
    return {
        key: str(value)
        for key, value in sorted(labels.items())
        if key.startswith("com.docker.compose.")
        and not SENSITIVE_KEY.search(key)
        and not SENSITIVE_KEY.search(str(value))
    }


def _container_evidence(name: str, runner: Runner) -> dict[str, Any]:
    payload = _docker_json(["inspect", name], runner)
    if not isinstance(payload, list) or len(payload) != 1:
        raise ContractError(f"container inspect identity failed: {name}")
    inspect = payload[0]
    state = inspect.get("State") or {}
    health = (state.get("Health") or {}).get("Status")
    image_payload = _docker_json(["image", "inspect", str(inspect.get("Image") or "")], runner)
    image_digests = []
    if isinstance(image_payload, list) and len(image_payload) == 1:
        image_digests = sorted(str(value) for value in image_payload[0].get("RepoDigests") or [])
    networks = sorted(((inspect.get("NetworkSettings") or {}).get("Networks") or {}).keys())
    ports = {
        str(key): sorted(
            f"{item.get('HostIp', '')}:{item.get('HostPort', '')}"
            for item in (value or [])
        )
        for key, value in sorted(
            (((inspect.get("NetworkSettings") or {}).get("Ports") or {}).items())
        )
    }
    return {
        "name": str(inspect.get("Name") or "").lstrip("/"),
        "image_reference": str((inspect.get("Config") or {}).get("Image") or ""),
        "image_id": str(inspect.get("Image") or ""),
        "repo_digests": image_digests,
        "created": str(inspect.get("Created") or ""),
        "running": bool(state.get("Running")),
        "health": str(health or "not_configured"),
        "restart_policy": str(
            ((inspect.get("HostConfig") or {}).get("RestartPolicy") or {}).get("Name")
            or ""
        ),
        "environment_names": _environment_names(inspect),
        "mounts": _safe_mounts(inspect),
        "networks": networks,
        "ports": ports,
        "compose_labels": _safe_labels(inspect),
    }


def _read_odoo_options(settings: Settings, runner: Runner) -> dict[str, str]:
    program = (
        "import configparser,json;"
        "p=configparser.ConfigParser();p.read('/opt/sce-runtime/config/odoo.conf');"
        f"keys={list(SAFE_ODOO_OPTIONS)!r};"
        "s=p['options'];"
        "print(json.dumps({k:s.get(k,'') for k in keys}))"
    )
    raw = runner(
        ["docker", "exec", settings.odoo_container, "python3", "-c", program]
    )
    values = json.loads(raw.decode())
    if any(SENSITIVE_KEY.search(key) for key in values):
        raise ContractError("unsafe Odoo configuration evidence")
    return {str(key): str(value) for key, value in values.items()}


def collect_metadata(settings: Settings, runner: Runner = run) -> dict[str, Any]:
    db = _container_evidence(settings.db_container, runner)
    odoo = _container_evidence(settings.odoo_container, runner)
    if not db["running"] or not odoo["running"]:
        raise ContractError("required production container is not running")
    if db["health"] not in {"healthy", "not_configured"}:
        raise ContractError("production database container is not healthy")
    project_labels = {
        db["compose_labels"].get("com.docker.compose.project"),
        odoo["compose_labels"].get("com.docker.compose.project"),
    }
    if project_labels != {PROJECT}:
        raise ContractError("compose project labels do not match sc_production")
    identity = runner(
        [
            "docker",
            "exec",
            settings.db_container,
            "psql",
            "-U",
            settings.db_user,
            "-d",
            settings.database,
            "-Atc",
            "SELECT current_database()",
        ]
    ).decode().strip()
    if identity != DATABASE:
        raise ContractError("database identity verification failed")
    runner(
        [
            "docker",
            "exec",
            settings.odoo_container,
            "sh",
            "-eu",
            "-c",
            f"test -d '{settings.filestore_root}/{DATABASE}'; "
            f"test ! -d '{settings.filestore_root}/{STALE_DATABASE}'",
        ]
    )
    odoo_version = runner(
        ["docker", "exec", settings.odoo_container, "odoo", "--version"]
    ).decode().strip()
    postgres_version = runner(
        ["docker", "exec", settings.db_container, "postgres", "--version"]
    ).decode().strip()
    systemd = {}
    for unit in ("scems-production-backup.service", "scems-production-backup.timer"):
        raw = runner(
            [
                "systemctl",
                "show",
                unit,
                "--property=Id,LoadState,ActiveState,UnitFileState,NextElapseUSecRealtime",
                "--no-pager",
            ]
        ).decode()
        systemd[unit] = {
            key: value
            for key, value in (
                line.split("=", 1) for line in raw.splitlines() if "=" in line
            )
            if not SENSITIVE_KEY.search(key)
        }
    compose_files = {}
    config_files = str(
        odoo["compose_labels"].get("com.docker.compose.project.config_files") or ""
    )
    for raw_path in filter(None, (item.strip() for item in config_files.split(","))):
        path = Path(raw_path)
        try:
            resolved = path.resolve(strict=True)
        except OSError as exc:
            raise ContractError("compose source file is unavailable") from exc
        if (
            not str(resolved).startswith("/opt/sce/deployment-tools/")
            or resolved.is_symlink()
            or not resolved.is_file()
        ):
            raise ContractError("compose source path escaped approved deployment tools")
        compose_files[str(resolved)] = sha256(resolved)
    sanitized_compose = {
        "services": {
            "db": db,
            "odoo": odoo,
        },
        "config_file_sha256": compose_files,
    }
    serialized = json.dumps(sanitized_compose, sort_keys=True)
    if SENSITIVE_KEY.search(serialized):
        # Secret-like environment *names* are allowed only in the dedicated
        # names-only inventory, never in the structural compose evidence.
        sanitized_compose["services"]["db"]["environment_names"] = []
        sanitized_compose["services"]["odoo"]["environment_names"] = []
    return {
        "schema_version": 1,
        "contract_version": CONTRACT_VERSION,
        "captured_at": utc_now(),
        "source_host_id": hashlib.sha256(socket.gethostname().encode()).hexdigest(),
        "compose_project": settings.project,
        "database": settings.database,
        "database_container": db,
        "odoo_container": odoo,
        "postgresql_version": postgres_version,
        "odoo_version": odoo_version,
        "odoo_options": _read_odoo_options(settings, runner),
        "sanitized_compose_config": sanitized_compose,
        "filestore_root": settings.filestore_root,
        "environment_names": sorted(
            set(db["environment_names"]) | set(odoo["environment_names"])
        ),
        "required_environment_present": {
            key: key in set(db["environment_names"]) | set(odoo["environment_names"])
            for key in ("DB_NAME", "DB_USER", "ODOO_DBFILTER")
        },
        "systemd": systemd,
        "tool_source_sha": settings.tool_source_sha,
        "secret_values_exposed": False,
    }


def _write_bytes(path: Path, value: bytes) -> None:
    if not value:
        raise ContractError(f"empty backup artifact: {path.name}")
    path.write_bytes(value)
    path.chmod(0o600)


def _filestore_digest(container: str, root: str, database: str, runner: Runner) -> str:
    command = (
        f"test -d '{root}/{database}'; cd '{root}/{database}'; "
        "find . -type f -print0 | sort -z | xargs -0 -r sha256sum | sha256sum"
    )
    return runner(
        ["docker", "exec", container, "sh", "-eu", "-c", command]
    ).decode().split()[0]


def _table_counts(container: str, user: str, database: str, runner: Runner) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in COUNT_TABLES:
        query = (
            f"SELECT CASE WHEN to_regclass('public.{table}') IS NULL "
            f"THEN -1 ELSE (SELECT count(*) FROM {table}) END"
        )
        counts[table] = int(
            runner(
                [
                    "docker",
                    "exec",
                    container,
                    "psql",
                    "-U",
                    user,
                    "-d",
                    database,
                    "-Atc",
                    query,
                ]
            )
            .decode()
            .strip()
        )
    return counts


def _attachment_sample(container: str, user: str, database: str, runner: Runner) -> list[str]:
    query = (
        "SELECT coalesce(store_fname,'') || '|' || coalesce(checksum,'') "
        "FROM ir_attachment WHERE store_fname IS NOT NULL "
        "ORDER BY id DESC LIMIT 10"
    )
    raw = runner(
        [
            "docker",
            "exec",
            container,
            "psql",
            "-U",
            user,
            "-d",
            database,
            "-Atc",
            query,
        ]
    ).decode()
    return raw.splitlines()


def _module_versions(container: str, user: str, database: str, runner: Runner) -> dict[str, str]:
    query = (
        "SELECT name || '|' || coalesce(latest_version,'') "
        "FROM ir_module_module WHERE state='installed' "
        "AND (name LIKE 'smart_%' OR name LIKE 'sc_%') ORDER BY name"
    )
    raw = runner(
        [
            "docker",
            "exec",
            container,
            "psql",
            "-U",
            user,
            "-d",
            database,
            "-Atc",
            query,
        ]
    ).decode()
    return dict(line.split("|", 1) for line in raw.splitlines() if "|" in line)


def backup(
    settings: Settings,
    *,
    backup_set_id: str | None = None,
    runner: Runner = run,
    lock_root: Path = Path("/run/lock"),
    approved_backup_root: Path = Path("/data/backups/sc_production"),
) -> Path:
    started_at = utc_now()
    identifier = validate_backup_id(backup_set_id or new_backup_id())
    root = safe_root(settings.backup_root, approved_backup_root)
    final = root / identifier
    if final.exists() or final.is_symlink():
        raise ContractError("completed backup set cannot be overwritten")
    lock_path = lock_root / f"{PROJECT}-{DATABASE}-{CONTRACT_VERSION}.backup.lock"
    coordination = lock_root / f"{PROJECT}-{DATABASE}-{CONTRACT_VERSION}.coordination.lock"
    with NonBlockingLock(coordination), NonBlockingLock(lock_path):
        temporary = Path(tempfile.mkdtemp(prefix=f".incomplete-{identifier}-", dir=root))
        temporary.chmod(0o700)
        published = False
        try:
            metadata = collect_metadata(settings, runner)
            dump = temporary / "database.dump"
            filestore = temporary / "filestore.tar.gz"
            metadata_path = temporary / "deployment-metadata.json"
            _write_bytes(
                dump,
                runner(
                    [
                        "docker",
                        "exec",
                        settings.db_container,
                        "pg_dump",
                        "-U",
                        settings.db_user,
                        "-d",
                        settings.database,
                        "-Fc",
                    ]
                ),
            )
            runner(
                ["docker", "exec", "-i", settings.db_container, "pg_restore", "-l"],
                input_bytes=dump.read_bytes(),
            )
            _write_bytes(
                filestore,
                runner(
                    [
                        "docker",
                        "exec",
                        settings.odoo_container,
                        "tar",
                        "-C",
                        settings.filestore_root,
                        "-czf",
                        "-",
                        settings.database,
                    ]
                ),
            )
            atomic_json(metadata_path, metadata)
            checksums = {name: sha256(temporary / name) for name in ARTIFACTS}
            manifest = {
                "schema_version": 2,
                "contract_version": CONTRACT_VERSION,
                "backup_set_id": identifier,
                "status": "complete",
                "created_at": utc_now(),
                "started_at": started_at,
                "completed_at": utc_now(),
                "compose_project": settings.project,
                "database": settings.database,
                "database_container": settings.db_container,
                "filestore_source": f"{settings.filestore_root}/{settings.database}",
                "tool_source_sha": settings.tool_source_sha,
                "encryption_status": settings.encryption_status,
                "retention_days": settings.retention_days,
                "checksums": checksums,
                "sizes": {name: (temporary / name).stat().st_size for name in ARTIFACTS},
                "table_counts": _table_counts(
                    settings.db_container,
                    settings.db_user,
                    settings.database,
                    runner,
                ),
                "attachment_sample": _attachment_sample(
                    settings.db_container,
                    settings.db_user,
                    settings.database,
                    runner,
                ),
                "module_versions": _module_versions(
                    settings.db_container,
                    settings.db_user,
                    settings.database,
                    runner,
                ),
                "filestore_digest": _filestore_digest(
                    settings.odoo_container,
                    settings.filestore_root,
                    settings.database,
                    runner,
                ),
                "backup_pair_verified": True,
                "secret_values_exposed": False,
            }
            atomic_json(temporary / "manifest.json", manifest)
            checksum_lines = [
                f"{sha256(temporary / name)}  {name}"
                for name in (*ARTIFACTS, "manifest.json")
            ]
            _write_bytes(
                temporary / "SHA256SUMS",
                ("\n".join(checksum_lines) + "\n").encode(),
            )
            validate_backup_set(temporary)
            os.replace(temporary, final)
            published = True
            return final
        except Exception as exc:
            atomic_json(
                temporary / "failure.json",
                {
                    "schema_version": 1,
                    "contract_version": CONTRACT_VERSION,
                    "backup_set_id": identifier,
                    "status": "FAIL",
                    "error_class": type(exc).__name__,
                    "completed_at": utc_now(),
                    "published_as_complete": False,
                },
            )
            raise
        finally:
            if not published and temporary.exists():
                # Incomplete sets are not installable evidence.  Keep a compact,
                # explicit failure marker outside the final backup namespace.
                failed = root / f".failed-{identifier}-{secrets.token_hex(4)}"
                os.replace(temporary, failed)


def validate_backup_set(directory: Path) -> dict[str, Any]:
    if directory.is_symlink() or not directory.is_dir():
        raise ContractError("backup set directory is invalid")
    if stat.S_IMODE(directory.stat().st_mode) != 0o700:
        raise ContractError("backup set directory permissions are invalid")
    try:
        manifest = json.loads((directory / "manifest.json").read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("backup manifest is invalid") from exc
    if (
        manifest.get("contract_version") != CONTRACT_VERSION
        or manifest.get("status") != "complete"
        or manifest.get("database") != DATABASE
        or manifest.get("compose_project") != PROJECT
        or manifest.get("backup_pair_verified") is not True
        or manifest.get("secret_values_exposed") is not False
    ):
        raise ContractError("backup manifest identity is invalid")
    expected = set((*ARTIFACTS, "manifest.json", "SHA256SUMS"))
    if {item.name for item in directory.iterdir()} != expected:
        raise ContractError("backup set artifact inventory is invalid")
    for name in (*ARTIFACTS, "manifest.json", "SHA256SUMS"):
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
            raise ContractError(f"backup artifact is invalid: {name}")
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise ContractError(f"backup artifact permissions are invalid: {name}")
    checksum_lines = (directory / "SHA256SUMS").read_text().splitlines()
    parsed: dict[str, str] = {}
    for line in checksum_lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match or match.group(2) in parsed:
            raise ContractError("SHA256SUMS inventory is invalid")
        parsed[match.group(2)] = match.group(1)
    checksum_inventory = set((*ARTIFACTS, "manifest.json"))
    if set(parsed) != checksum_inventory:
        raise ContractError("SHA256SUMS inventory differs from backup contract")
    if any(sha256(directory / name) != digest for name, digest in parsed.items()):
        raise ContractError("SHA256SUMS validation failed")
    for name, digest in manifest.get("checksums", {}).items():
        if name not in ARTIFACTS or sha256(directory / name) != digest:
            raise ContractError(f"backup checksum mismatch: {name}")
    return manifest


def _wait_postgres(container: str, user: str, runner: Runner) -> None:
    for _ in range(30):
        try:
            runner(["docker", "exec", container, "pg_isready", "-U", user])
            return
        except ContractError:
            time.sleep(1)
    raise ContractError("isolated PostgreSQL did not become ready")


def restore_rehearsal(
    backup_dir: Path,
    *,
    restore_id: str,
    odoo_image: str,
    postgres_image: str,
    report_path: Path,
    runner: Runner = run,
    lock_root: Path = Path("/run/lock"),
    approved_backup_root: Path = Path("/data/backups/sc_production"),
) -> dict[str, Any]:
    approved_report_root = approved_backup_root / "restore-rehearsals"
    if (
        backup_dir.parent != approved_backup_root
        or not BACKUP_ID.fullmatch(backup_dir.name)
        or backup_dir.is_symlink()
    ):
        raise ContractError("backup path escaped approved backup root")
    if (
        report_path.parent != approved_report_root
        or report_path.name != f"{restore_id}.json"
        or report_path.is_symlink()
    ):
        raise ContractError("restore report path escaped approved evidence root")
    approved_report_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if stat.S_IMODE(approved_report_root.stat().st_mode) & 0o077:
        raise ContractError("restore report root permissions must not exceed 0700")
    manifest = validate_backup_set(backup_dir)
    if not RESTORE_ID.fullmatch(restore_id):
        raise ContractError("restore rehearsal identity is invalid")
    if not ODOO_IMAGE_REF.fullmatch(odoo_image):
        raise ContractError("restore Odoo image must use the approved immutable repository")
    if not POSTGRES_IMAGE_REF.fullmatch(postgres_image):
        raise ContractError("restore images must use immutable digests")
    if report_path.exists() or report_path.is_symlink():
        raise ContractError("restore report cannot be overwritten")
    names = {
        "network": f"{restore_id}_internal",
        "db_volume": f"{restore_id}_db",
        "filestore_volume": f"{restore_id}_filestore",
        "db_container": f"{restore_id}_db",
        "odoo_container": f"{restore_id}_odoo",
    }
    forbidden = ("sc_production", "sc-backend-odoo-prod", "sce-sc_production")
    if any(any(token in value for token in forbidden) for value in names.values()):
        raise ContractError("restore resource namespace overlaps production")
    lock_path = lock_root / f"{PROJECT}-{DATABASE}-{CONTRACT_VERSION}.restore.lock"
    started_at = utc_now()
    started = time.monotonic()
    password = secrets.token_urlsafe(32)
    state = "prepare"
    coordination = lock_root / f"{PROJECT}-{DATABASE}-{CONTRACT_VERSION}.coordination.lock"
    with NonBlockingLock(coordination), NonBlockingLock(lock_path):
        atomic_json(
            report_path,
            {
                "schema_version": 1,
                "contract_version": CONTRACT_VERSION,
                "restore_id": restore_id,
                "backup_set_id": manifest.get("backup_set_id"),
                "status": "PLANNED",
                "resources": names,
                "external_write_side_effects": 0,
                "production_database_connected": False,
            },
        )
        try:
            runner(["docker", "network", "create", "--internal", names["network"]])
            runner(["docker", "volume", "create", names["db_volume"]])
            runner(["docker", "volume", "create", names["filestore_volume"]])
            state = "database_restore"
            runner(
                [
                    "docker",
                    "run",
                    "-d",
                    "--name",
                    names["db_container"],
                    "--network",
                    names["network"],
                    "-e",
                    "POSTGRES_USER=odoo",
                    "-e",
                    f"POSTGRES_PASSWORD={password}",
                    "-e",
                    "POSTGRES_DB=postgres",
                    "-v",
                    f"{names['db_volume']}:/var/lib/postgresql/data",
                    postgres_image,
                ]
            )
            _wait_postgres(names["db_container"], "odoo", runner)
            target_db = f"r10e_{restore_id}"
            runner(
                [
                    "docker",
                    "exec",
                    names["db_container"],
                    "createdb",
                    "-U",
                    "odoo",
                    target_db,
                ]
            )
            runner(
                [
                    "docker",
                    "exec",
                    "-i",
                    names["db_container"],
                    "pg_restore",
                    "-U",
                    "odoo",
                    "-d",
                    target_db,
                    "--no-owner",
                    "--no-privileges",
                ],
                input_bytes=(backup_dir / "database.dump").read_bytes(),
            )
            state = "filestore_restore"
            runner(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "-i",
                    "-v",
                    f"{names['filestore_volume']}:/restore",
                    "--entrypoint",
                    "sh",
                    odoo_image,
                    "-eu",
                    "-c",
                    f"mkdir -p /restore; tar -C /restore -xzf -; "
                    f"mv /restore/{DATABASE} /restore/{target_db}",
                ],
                input_bytes=(backup_dir / "filestore.tar.gz").read_bytes(),
            )
            state = "odoo_health"
            config_payload = (
                "[options]\n"
                f"db_host = {names['db_container']}\n"
                "db_port = 5432\n"
                "db_user = odoo\n"
                f"db_password = {password}\n"
                f"dbfilter = ^{target_db}$\n"
                "list_db = False\n"
                "proxy_mode = False\n"
                "workers = 0\n"
                "max_cron_threads = 0\n"
                "smtp_server = 127.0.0.1\n"
            ).encode()
            with tempfile.NamedTemporaryFile(prefix="restore-odoo-", delete=False) as stream:
                stream.write(config_payload)
                config_path = Path(stream.name)
            config_path.chmod(0o600)
            try:
                runner(
                    [
                        "docker",
                        "run",
                        "--name",
                        names["odoo_container"],
                        "--network",
                        names["network"],
                        "--publish",
                        "127.0.0.1::8069",
                        "-v",
                        f"{names['filestore_volume']}:/var/lib/odoo/filestore",
                        "-v",
                        f"{config_path}:/etc/odoo/odoo.conf:ro",
                        "--entrypoint",
                        "odoo",
                        odoo_image,
                        "-c",
                        "/etc/odoo/odoo.conf",
                        "-d",
                        target_db,
                        "--stop-after-init",
                        "--max-cron-threads=0",
                        "--workers=0",
                    ]
                )
            finally:
                config_path.unlink(missing_ok=True)
            restored_counts = _table_counts(
                names["db_container"], "odoo", target_db, runner
            )
            if restored_counts != manifest["table_counts"]:
                raise ContractError("restored key table counts differ")
            restored_sample = _attachment_sample(
                names["db_container"], "odoo", target_db, runner
            )
            if restored_sample != manifest.get("attachment_sample"):
                raise ContractError("restored attachment sample differs")
            restored_modules = _module_versions(
                names["db_container"], "odoo", target_db, runner
            )
            if restored_modules != manifest.get("module_versions"):
                raise ContractError("restored module versions differ")
            digest_command = (
                f"cd '/restore/{target_db}'; "
                "find . -type f -print0 | sort -z | xargs -0 -r sha256sum | sha256sum"
            )
            restored_filestore = runner(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "-v",
                    f"{names['filestore_volume']}:/restore:ro",
                    "--entrypoint",
                    "sh",
                    odoo_image,
                    "-eu",
                    "-c",
                    digest_command,
                ]
            ).decode().split()[0]
            if restored_filestore != manifest["filestore_digest"]:
                raise ContractError("restored filestore digest differs")
            elapsed = round(time.monotonic() - started, 3)
            report = {
                "schema_version": 1,
                "contract_version": CONTRACT_VERSION,
                "restore_id": restore_id,
                "backup_set_id": manifest["backup_set_id"],
                "status": "PASS",
                "started_at": started_at,
                "rto_seconds": elapsed,
                "isolated_internal_network": True,
                "production_network_reused": False,
                "production_volume_reused": False,
                "production_database_connected": False,
                "cron_disabled": True,
                "mail_disabled": True,
                "webhook_queue_payment_disabled_by_no_egress": True,
                "external_write_side_effects": 0,
                "odoo_healthcheck": "stop_after_init_passed",
                "table_counts": restored_counts,
                "module_versions": restored_modules,
                "attachment_sample_verified": True,
                "filestore_digest": restored_filestore,
                "resources": names,
                "cleanup_authorized_separately": True,
            }
            atomic_json(report_path, report)
            return report
        except Exception as exc:
            atomic_json(
                report_path,
                {
                    "schema_version": 1,
                    "contract_version": CONTRACT_VERSION,
                    "restore_id": restore_id,
                    "backup_set_id": manifest.get("backup_set_id"),
                    "status": "FAIL",
                    "failure_stage": state,
                    "error_class": type(exc).__name__,
                    "external_write_side_effects": 0,
                    "production_database_connected": False,
                    "resources": names,
                },
            )
            raise


def cleanup_rehearsal(report_path: Path, *, runner: Runner = run) -> dict[str, Any]:
    approved_root = Path("/data/backups/sc_production/restore-rehearsals")
    if report_path.parent != approved_root or report_path.is_symlink():
        raise ContractError("cleanup report path escaped approved evidence root")
    try:
        report = json.loads(report_path.read_text())
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("restore report is unavailable for scoped cleanup") from exc
    restore_id = str(report.get("restore_id") or "")
    if not RESTORE_ID.fullmatch(restore_id):
        raise ContractError("restore cleanup identity is invalid")
    expected = {
        "network": f"{restore_id}_internal",
        "db_volume": f"{restore_id}_db",
        "filestore_volume": f"{restore_id}_filestore",
        "db_container": f"{restore_id}_db",
        "odoo_container": f"{restore_id}_odoo",
    }
    if report.get("resources") != expected:
        raise ContractError("restore cleanup resources differ from report")
    for kind, names in (
        ("container", (expected["odoo_container"], expected["db_container"])),
        ("volume", (expected["db_volume"], expected["filestore_volume"])),
        ("network", (expected["network"],)),
    ):
        for name in names:
            try:
                runner(["docker", kind, "inspect", name])
            except ContractError:
                continue
            command = ["docker", "rm", "-f", name] if kind == "container" else [
                "docker", kind, "rm", name
            ]
            runner(command)
    return {
        "status": "PASS",
        "restore_id": restore_id,
        "evidence_preserved": True,
        "production_resources_touched": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    backup_parser = subparsers.add_parser("backup")
    backup_parser.add_argument("--backup-set-id")
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--backup-dir", required=True, type=Path)
    restore_parser = subparsers.add_parser("restore-rehearsal")
    restore_parser.add_argument("--backup-dir", required=True, type=Path)
    restore_parser.add_argument("--restore-id", required=True)
    restore_parser.add_argument("--odoo-image", required=True)
    restore_parser.add_argument("--postgres-image", required=True)
    restore_parser.add_argument("--report", required=True, type=Path)
    cleanup_parser = subparsers.add_parser("cleanup-rehearsal")
    cleanup_parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if args.action == "backup":
        print(backup(Settings.from_env(), backup_set_id=args.backup_set_id))
    elif args.action == "validate":
        print(json.dumps(validate_backup_set(args.backup_dir), sort_keys=True))
    elif args.action == "restore-rehearsal":
        print(
            json.dumps(
                restore_rehearsal(
                    args.backup_dir,
                    restore_id=args.restore_id,
                    odoo_image=args.odoo_image,
                    postgres_image=args.postgres_image,
                    report_path=args.report,
                ),
                sort_keys=True,
            )
        )
    else:
        print(json.dumps(cleanup_rehearsal(args.report), sort_keys=True))


if __name__ == "__main__":
    main()
