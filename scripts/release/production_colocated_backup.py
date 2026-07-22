#!/usr/bin/env python3
"""Paired database/filestore backup and isolated restore drill for sc_production."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PRODUCTION_DB = "sc_production"
RESTORE_DB = re.compile(r"^r10e_restore_[a-z0-9_]+$")
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


def validate_backup(directory: Path) -> dict:
    manifest = json.loads(_manifest_path(directory).read_text(encoding="utf-8"))
    if manifest.get("database") != PRODUCTION_DB:
        raise BackupError("backup database identity is not sc_production")
    for name, expected in manifest.get("checksums", {}).items():
        path = directory / name
        if not path.is_file() or path.stat().st_size <= 0 or _sha(path) != expected:
            raise BackupError(f"backup validation failed: {name}")
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
    directory = root / f"sc_production-{stamp}"
    directory.mkdir(parents=True, exist_ok=False)
    dump = directory / "database.dump"
    filestore = directory / "filestore.tar.gz"
    dump.write_bytes(_run(["docker", "exec", db_container, "pg_dump", "-U", db_user, "-d", database, "-Fc"]))
    _run([
        "docker", "exec", odoo_container, "sh", "-eu", "-c",
        f"test -d '{filestore_root}/{database}'; test -n \"$(find '{filestore_root}/{database}' -type f -print -quit)\"",
    ])
    filestore.write_bytes(_run([
        "docker", "exec", odoo_container, "tar", "-C", filestore_root, "-czf", "-", database,
    ]))
    if dump.stat().st_size <= 0 or filestore.stat().st_size <= 0:
        raise BackupError("database and filestore backups must both be non-empty")
    identity = _run([
        "docker", "exec", db_container, "psql", "-U", db_user, "-d", database, "-Atc", "SELECT current_database()",
    ]).decode().strip()
    if identity != database:
        raise BackupError("database identity validation failed")
    _run(["docker", "exec", "-i", db_container, "pg_restore", "-l"], input_bytes=dump.read_bytes())
    manifest = {
        "schema_version": 1,
        "architecture": "single_database_colocated_platform_core",
        "database": database,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "database_bytes": dump.stat().st_size,
        "filestore_bytes": filestore.stat().st_size,
        "covered_platform_tables": list(PLATFORM_TABLES),
        "checksums": {"database.dump": _sha(dump), "filestore.tar.gz": _sha(filestore)},
    }
    _manifest_path(directory).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validate_backup(directory)
    return directory


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
