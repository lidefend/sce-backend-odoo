#!/usr/bin/env python3
"""Paired database/filestore backup and isolated restore drill for sc_production."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


PRODUCTION_DB = "sc_production"
RESTORE_DB = re.compile(r"^r10e_restore_[a-z0-9_]+$")
BACKUP_ID = re.compile(r"^sc_production-[0-9]{8}T[0-9]{6}Z$")
ARTIFACTS = ("database.dump", "filestore.tar.gz", "manifest.json")
CHECKSUM_FILE = "SHA256SUMS"
PLATFORM_TABLES = (
    "sc_subscription_plan", "sc_subscription", "sc_entitlement", "sc_usage_counter",
    "sc_ops_job", "sc_product_policy", "sc_edition_release_snapshot", "sc_release_action", "sc_login_route",
)
BUSINESS_TABLES = ("res_users", "ir_attachment", "ir_module_module")


class BackupError(RuntimeError):
    pass


def _required(name: str) -> str:
    value = str(os.environ.get(name) or "").strip()
    if not value:
        raise BackupError(f"{name} is required")
    return value


def _run(args: list[str], *, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(args, input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise BackupError(f"command failed ({args[0:3]}): {result.stderr.decode(errors='replace').strip()}")
    return result.stdout


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_path(directory: Path) -> Path:
    return directory / "manifest.json"


def _tool_revision() -> str:
    marker = Path(__file__).resolve().parents[2] / "DEPLOYMENT_TOOL_SHA"
    value = (
        marker.read_text(encoding="utf-8").strip()
        if marker.is_file()
        else str(os.environ.get("BACKUP_TOOL_REVISION") or "").strip()
    )
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise BackupError("backup tool revision is unavailable")
    return value


def _safe_root(root: Path) -> Path:
    if not root.is_absolute() or root == Path("/"):
        raise BackupError("backup root must be a scoped absolute path")
    try:
        resolved = root.resolve(strict=True)
    except OSError as exc:
        raise BackupError("backup root is unavailable") from exc
    if resolved != root or root.is_symlink() or not root.is_dir():
        raise BackupError("backup root must not contain symlink indirection")
    metadata = root.stat()
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise BackupError("backup root permissions must not exceed 0700")
    return root


def _write_bytes(path: Path, payload: bytes) -> None:
    if not payload:
        raise BackupError(f"backup artifact is empty: {path.name}")
    path.write_bytes(payload)
    path.chmod(0o600)


def _write_text(path: Path, payload: str) -> None:
    _write_bytes(path, payload.encode("utf-8"))


def _write_checksums(directory: Path) -> None:
    lines = [f"{_sha(directory / name)}  {name}" for name in ARTIFACTS]
    _write_text(directory / CHECKSUM_FILE, "\n".join(lines) + "\n")


def _fsync_path(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | (os.O_DIRECTORY if path.is_dir() else 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _validate_checksums(directory: Path) -> None:
    checksum_path = directory / CHECKSUM_FILE
    if (
        checksum_path.is_symlink()
        or not checksum_path.is_file()
        or checksum_path.stat().st_size <= 0
    ):
        raise BackupError("SHA256SUMS is missing or invalid")
    entries: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match:
            raise BackupError("SHA256SUMS format is invalid")
        digest, name = match.groups()
        if name == CHECKSUM_FILE or name in entries or Path(name).is_absolute():
            raise BackupError("SHA256SUMS inventory is invalid")
        entries[name] = digest
    if set(entries) != set(ARTIFACTS):
        raise BackupError("SHA256SUMS artifact inventory differs")
    for name, expected in entries.items():
        if _sha(directory / name) != expected:
            raise BackupError(f"backup checksum validation failed: {name}")


def _validate_artifacts(directory: Path) -> None:
    if directory.is_symlink() or not directory.is_dir():
        raise BackupError("backup directory mode must be 0700")
    directory_metadata = directory.stat()
    if (
        stat.S_IMODE(directory_metadata.st_mode) != 0o700
        or directory_metadata.st_uid != os.geteuid()
        or directory_metadata.st_gid != os.getegid()
    ):
        raise BackupError("backup directory mode must be 0700")
    for name in ARTIFACTS + (CHECKSUM_FILE,):
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise BackupError(f"backup artifact contract failed: {name}")
        metadata = path.stat()
        if (
            metadata.st_size <= 0
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_uid != os.geteuid()
            or metadata.st_gid != os.getegid()
        ):
            raise BackupError(f"backup artifact contract failed: {name}")
    if set(item.name for item in directory.iterdir()) != set(
        ARTIFACTS + (CHECKSUM_FILE,)
    ):
        raise BackupError("backup directory contains unexpected artifacts")
    _validate_checksums(directory)


def validate_backup(
    directory: Path, *, require_artifact_contract: bool = False
) -> dict:
    try:
        manifest = json.loads(
            _manifest_path(directory).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BackupError("backup manifest is missing or invalid") from exc
    if manifest.get("database") != PRODUCTION_DB:
        raise BackupError("backup database identity is not sc_production")
    for name, expected in manifest.get("checksums", {}).items():
        path = directory / name
        if not path.is_file() or path.stat().st_size <= 0 or _sha(path) != expected:
            raise BackupError(f"backup validation failed: {name}")
    if require_artifact_contract:
        if (
            manifest.get("backup_status") != "complete"
            or manifest.get("database_format") != "postgresql_custom"
            or manifest.get("structure_validation") != "pg_restore_list_passed"
            or manifest.get("filestore_artifact") != "filestore.tar.gz"
            or not re.fullmatch(
                r"[0-9a-f]{40}", str(manifest.get("tool_revision") or "")
            )
        ):
            raise BackupError("backup manifest artifact contract is incomplete")
        _validate_artifacts(directory)
    return manifest


def backup(root: Path) -> Path:
    database = str(os.environ.get("BACKUP_TARGET_DB") or PRODUCTION_DB).strip()
    if database != PRODUCTION_DB:
        raise BackupError("production backup target must be sc_production")
    db_container = _required("BACKUP_DB_CONTAINER")
    odoo_container = _required("BACKUP_ODOO_CONTAINER")
    db_user = _required("BACKUP_DB_USER")
    filestore_root = str(os.environ.get("BACKUP_FILESTORE_ROOT") or "/opt/sce-runtime/filestore").rstrip("/")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    identifier = f"sc_production-{stamp}"
    if not BACKUP_ID.fullmatch(identifier):
        raise BackupError("backup identifier is invalid")
    root = _safe_root(root)
    final_directory = root / identifier
    existing = sorted(
        item.name
        for item in root.iterdir()
        if item.is_dir() and BACKUP_ID.fullmatch(item.name)
    )
    if existing and identifier <= existing[-1]:
        raise BackupError("new recovery point must be later than the existing one")
    if final_directory.exists() or final_directory.is_symlink():
        raise BackupError("final recovery point already exists")

    previous_umask = os.umask(0o077)
    temporary_directory: Path | None = None
    published = False
    completed = False
    try:
        temporary_directory = Path(
            tempfile.mkdtemp(prefix=f".incomplete-{identifier}-", dir=root)
        )
        temporary_directory.chmod(0o700)
        dump = temporary_directory / "database.dump"
        filestore = temporary_directory / "filestore.tar.gz"
        _write_bytes(
            dump,
            _run([
                "docker", "exec", db_container, "pg_dump", "-U", db_user,
                "-d", database, "-Fc",
            ]),
        )
        _run([
            "docker", "exec", odoo_container, "sh", "-eu", "-c",
            f"test -d '{filestore_root}/{database}'",
        ])
        _write_bytes(
            filestore,
            _run([
                "docker", "exec", odoo_container, "tar", "-C",
                filestore_root, "-czf", "-", database,
            ]),
        )
        identity = _run([
            "docker", "exec", db_container, "psql", "-U", db_user,
            "-d", database, "-Atc", "SELECT current_database()",
        ]).decode().strip()
        if identity != database:
            raise BackupError("database identity validation failed")
        _run(
            ["docker", "exec", "-i", db_container, "pg_restore", "-l"],
            input_bytes=dump.read_bytes(),
        )
        manifest = {
            "schema_version": 1,
            "architecture": "single_database_colocated_platform_core",
            "database": database,
            "backup_id": identifier,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "database_format": "postgresql_custom",
            "database_bytes": dump.stat().st_size,
            "filestore_artifact": "filestore.tar.gz",
            "filestore_bytes": filestore.stat().st_size,
            "tool_revision": _tool_revision(),
            "backup_status": "complete",
            "structure_validation": "pg_restore_list_passed",
            "covered_platform_tables": list(PLATFORM_TABLES),
            "checksums": {
                "database.dump": _sha(dump),
                "filestore.tar.gz": _sha(filestore),
            },
        }
        _write_text(
            _manifest_path(temporary_directory),
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        )
        _write_checksums(temporary_directory)
        _validate_artifacts(temporary_directory)
        for name in ARTIFACTS + (CHECKSUM_FILE,):
            _fsync_path(temporary_directory / name)
        _fsync_path(temporary_directory)
        os.rename(temporary_directory, final_directory)
        temporary_directory = None
        published = True
        _fsync_path(root)
        _validate_artifacts(final_directory)
        validate_backup(final_directory, require_artifact_contract=True)
        completed = True
        return final_directory
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BackupError("production backup artifact creation failed") from exc
    finally:
        os.umask(previous_umask)
        if temporary_directory is not None and temporary_directory.exists():
            shutil.rmtree(temporary_directory)
        if published and not completed and final_directory.exists():
            shutil.rmtree(final_directory)


def _counts(container: str, user: str, database: str) -> str:
    tables = PLATFORM_TABLES + BUSINESS_TABLES
    rows = []
    for table in tables:
        exists = _run([
            "docker", "exec", container, "psql", "-U", user, "-d", database, "-Atc",
            f"SELECT to_regclass('public.{table}') IS NOT NULL",
        ]).decode().strip()
        count = "-1"
        if exists == "t":
            count = _run([
                "docker", "exec", container, "psql", "-U", user, "-d", database, "-Atc",
                f"SELECT count(*) FROM {table}",
            ]).decode().strip()
        elif table in PLATFORM_TABLES:
            raise BackupError(f"required platform table missing: {table}")
        rows.append(f"{table}={count}")
    return "\n".join(rows) + "\n"


def _filestore_digest(container: str, root: str, database: str) -> str:
    if database != PRODUCTION_DB and not RESTORE_DB.fullmatch(database):
        raise BackupError("unsafe filestore database identity")
    command = (
        f"test -d '{root}/{database}'; cd '{root}/{database}'; "
        "find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum"
    )
    return _run(["docker", "exec", container, "sh", "-eu", "-c", command]).decode().split()[0]


def restore_drill(directory: Path) -> dict:
    validate_backup(directory)
    source_db_container = _required("BACKUP_DB_CONTAINER")
    source_odoo_container = _required("BACKUP_ODOO_CONTAINER")
    restore_db_container = _required("RESTORE_DB_CONTAINER")
    restore_odoo_container = _required("RESTORE_ODOO_CONTAINER")
    db_user = _required("BACKUP_DB_USER")
    target = _required("RESTORE_TARGET_DB")
    if not RESTORE_DB.fullmatch(target):
        raise BackupError("restore drill database must use the r10e_restore_* namespace")
    if restore_db_container == source_db_container or restore_odoo_container == source_odoo_container:
        raise BackupError("restore drill containers must be isolated from formal containers")
    exists = _run([
        "docker", "exec", restore_db_container, "psql", "-U", db_user, "-d", "postgres", "-Atc",
        f"SELECT count(*) FROM pg_database WHERE datname='{target}'",
    ]).decode().strip()
    if exists != "0":
        raise BackupError("restore drill target already exists; refusing overwrite")
    _run(["docker", "exec", restore_db_container, "createdb", "-U", db_user, target])
    dump = (directory / "database.dump").read_bytes()
    _run([
        "docker", "exec", "-i", restore_db_container, "pg_restore", "-U", db_user, "-d", target,
        "--no-owner", "--no-privileges",
    ], input_bytes=dump)
    restore_root = str(os.environ.get("RESTORE_FILESTORE_ROOT") or "/opt/sce-runtime/filestore").rstrip("/")
    _run([
        "docker", "exec", "-i", restore_odoo_container, "sh", "-eu", "-c",
        f"test ! -e '{restore_root}/{target}'; test ! -e '{restore_root}/{PRODUCTION_DB}'; mkdir -p '{restore_root}'; tar -C '{restore_root}' -xzf -; mv '{restore_root}/{PRODUCTION_DB}' '{restore_root}/{target}'",
    ], input_bytes=(directory / "filestore.tar.gz").read_bytes())
    source_counts = _counts(source_db_container, db_user, PRODUCTION_DB)
    restored_counts = _counts(restore_db_container, db_user, target)
    if source_counts != restored_counts:
        raise BackupError("restored platform/business table counts differ")
    source_root = str(os.environ.get("BACKUP_FILESTORE_ROOT") or "/opt/sce-runtime/filestore").rstrip("/")
    source_digest = _filestore_digest(source_odoo_container, source_root, PRODUCTION_DB)
    restored_digest = _filestore_digest(restore_odoo_container, restore_root, target)
    if source_digest != restored_digest:
        raise BackupError("restored filestore digest differs")
    return {
        "status": "PASS",
        "source_database": PRODUCTION_DB,
        "restored_database": target,
        "counts": restored_counts.strip().splitlines(),
        "filestore_digest": restored_digest,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("backup", "validate", "restore-drill"))
    configured_root = os.environ.get("BACKUP_ROOT")
    parser.add_argument("--backup-root", type=Path, default=Path(configured_root) if configured_root else None)
    parser.add_argument("--backup-dir", type=Path)
    args = parser.parse_args()
    if args.action == "backup":
        if args.backup_root is None:
            raise BackupError("BACKUP_ROOT is required")
        print(backup(args.backup_root))
    elif args.action == "validate":
        print(json.dumps(validate_backup(args.backup_dir or Path()), sort_keys=True))
    else:
        print(json.dumps(restore_drill(args.backup_dir or Path()), sort_keys=True))


if __name__ == "__main__":
    main()
