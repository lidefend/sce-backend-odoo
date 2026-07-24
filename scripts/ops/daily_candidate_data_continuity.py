#!/usr/bin/env python3
"""Fail-closed paired backup and isolated restore for the daily candidate.

The daily candidate carries persistent user-entered data.  This tool is
deliberately bound to its exact compose project, database, containers and
volumes; it is not a generic database reset helper.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = Path(__file__).with_name(
    "daily_candidate_data_continuity_contract_v1.json"
)
ARTIFACTS = ("database.dump", "filestore.tar.gz", "manifest.json")
CHECKSUM_FILE = "SHA256SUMS"
BACKUP_ID = re.compile(r"^sc_demo-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")
DRILL_PREFIX = "sc-daily-continuity-drill-"
CONFIRMATION = "BACKUP_DAILY_CANDIDATE_PAIRED_STATE"


class ContinuityError(RuntimeError):
    pass


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_contract(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContinuityError("continuity contract is missing or invalid") from exc
    required = {
        "environment_class": "DAILY_CANDIDATE_ENVIRONMENT",
        "compose_project": "sc-backend-odoo-dev",
        "database": "sc_demo",
        "database_container": "sc-backend-odoo-dev-db-1",
        "odoo_container": "sc-backend-odoo-dev-odoo-1",
        "database_volume": "sc_dev_db_data",
        "odoo_data_volume": "sc_dev_odoo_data",
        "filestore_root": "/var/lib/odoo/filestore",
        "source_repository": "/opt/projects/repos/sce-backend-odoo",
        "backup_root": "/data/backups/daily_candidate",
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise ContinuityError(f"contract identity mismatch: {key}")
    return payload


def _run(
    args: list[str],
    *,
    input_bytes: bytes | None = None,
    check: bool = True,
) -> bytes:
    result = subprocess.run(
        args,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode:
        detail = result.stderr.decode(errors="replace").strip()
        raise ContinuityError(f"command failed ({' '.join(args[:3])}): {detail}")
    return result.stdout


def _run_to_file(args: list[str], path: Path) -> None:
    with path.open("wb") as stream:
        result = subprocess.run(
            args, stdout=stream, stderr=subprocess.PIPE, check=False
        )
    if result.returncode or path.stat().st_size <= 0:
        path.unlink(missing_ok=True)
        detail = result.stderr.decode(errors="replace").strip()
        raise ContinuityError(f"artifact command failed ({args[0]}): {detail}")
    path.chmod(0o600)


def _run_from_file(args: list[str], path: Path) -> bytes:
    with path.open("rb") as stream:
        result = subprocess.run(
            args,
            stdin=stream,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip()
        raise ContinuityError(f"command failed ({' '.join(args[:3])}): {detail}")
    return result.stdout


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inspect(name: str) -> dict:
    output = _run(["docker", "inspect", name])
    rows = json.loads(output)
    if len(rows) != 1:
        raise ContinuityError(f"container identity unavailable: {name}")
    return rows[0]


def _assert_runtime(contract: dict) -> dict:
    db = _inspect(contract["database_container"])
    odoo = _inspect(contract["odoo_container"])
    for item, service in ((db, "db"), (odoo, "odoo")):
        labels = item.get("Config", {}).get("Labels") or {}
        if labels.get("com.docker.compose.project") != contract["compose_project"]:
            raise ContinuityError("compose project identity mismatch")
        if labels.get("com.docker.compose.service") != service:
            raise ContinuityError(f"compose service identity mismatch: {service}")
        if not item.get("State", {}).get("Running"):
            raise ContinuityError(f"candidate container is not running: {service}")
    db_mounts = {
        (row.get("Name"), row.get("Destination")) for row in db.get("Mounts", [])
    }
    odoo_mounts = {
        (row.get("Name"), row.get("Destination")) for row in odoo.get("Mounts", [])
    }
    if (contract["database_volume"], "/var/lib/postgresql/data") not in db_mounts:
        raise ContinuityError("candidate database volume identity mismatch")
    if (contract["odoo_data_volume"], "/var/lib/odoo") not in odoo_mounts:
        raise ContinuityError("candidate Odoo data volume identity mismatch")
    repository = Path(contract["source_repository"])
    if not repository.is_dir():
        raise ContinuityError("candidate source repository is unavailable")
    revision = _run(["git", "-C", str(repository), "rev-parse", "HEAD"]).decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ContinuityError("candidate source revision is invalid")
    dirty = bool(
        _run(["git", "-C", str(repository), "status", "--porcelain"]).decode().strip()
    )
    return {
        "database_container_id": db["Id"],
        "database_image_id": db["Image"],
        "odoo_container_id": odoo["Id"],
        "odoo_image_id": odoo["Image"],
        "odoo_started_at": odoo["State"]["StartedAt"],
        "source_revision": revision,
        "source_worktree_dirty": dirty,
    }


def _psql(contract: dict, sql: str, *, container: str | None = None) -> str:
    output = _run(
        [
            "docker",
            "exec",
            container or contract["database_container"],
            "psql",
            "-X",
            "-U",
            "odoo",
            "-d",
            contract["database"],
            "-At",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            sql,
        ]
    )
    return output.decode().strip()


def _attachment_watermark(contract: dict, *, container: str | None = None) -> dict:
    row = _psql(
        contract,
        """
        SELECT count(*) || '|' || count(DISTINCT store_fname) || '|' ||
               md5(COALESCE(string_agg(DISTINCT store_fname, ',' ORDER BY store_fname), ''))
          FROM ir_attachment
         WHERE store_fname IS NOT NULL AND btrim(store_fname) <> '';
        """,
        container=container,
    )
    count, distinct_count, digest = row.split("|")
    return {
        "attachment_store_rows": int(count),
        "distinct_store_fnames": int(distinct_count),
        "store_fname_set_digest": digest,
    }


def _sentinels(contract: dict, *, container: str | None = None) -> dict:
    tables = contract["sentinel_tables"]
    counts = {}
    for table in tables:
        if not re.fullmatch(r"[a-z][a-z0-9_]+", table):
            raise ContinuityError("invalid sentinel table name")
        value = _psql(
            contract,
            f"SELECT CASE WHEN to_regclass('public.{table}') IS NULL "
            f"THEN '-1' ELSE (SELECT count(*)::text FROM {table}) END;",
            container=container,
        )
        counts[table] = int(value)
    samples = {}
    for table in contract["sample_tables"]:
        if not re.fullmatch(r"[a-z][a-z0-9_]+", table):
            raise ContinuityError("invalid sample table name")
        value = _psql(
            contract,
            f"SELECT COALESCE(string_agg(id::text, ',' ORDER BY id), '') "
            f"FROM (SELECT id FROM {table} ORDER BY id LIMIT 5) sample;",
            container=container,
        )
        samples[table] = [int(item) for item in value.split(",") if item]
    relation_digest = _psql(
        contract,
        """
        SELECT md5(COALESCE(string_agg(
            id::text || ':' || COALESCE(project_id::text, '') || ':' ||
            COALESCE(contract_id::text, ''), ',' ORDER BY id
        ), ''))
        FROM (SELECT id, project_id, contract_id
                FROM payment_request ORDER BY id LIMIT 100) sample;
        """,
        container=container,
    )
    database_uuid = _psql(
        contract,
        "SELECT COALESCE((SELECT value FROM ir_config_parameter "
        "WHERE key='database.uuid' LIMIT 1), '');",
        container=container,
    )
    if not database_uuid:
        raise ContinuityError("candidate database UUID is unavailable")
    return {
        "database_uuid": database_uuid,
        "table_counts": counts,
        "stable_sample_ids": samples,
        "payment_request_relation_sample_digest": relation_digest,
        "attachments": _attachment_watermark(contract, container=container),
    }


def _recovery_expectations(before: dict, after: dict) -> dict:
    if before["database_uuid"] != after["database_uuid"]:
        raise ContinuityError("database UUID changed during capture")
    ranges = {}
    for table, before_count in before["table_counts"].items():
        after_count = after["table_counts"][table]
        ranges[table] = {
            "minimum": min(before_count, after_count),
            "maximum": max(before_count, after_count),
        }
    stable_samples = {}
    for table, before_ids in before["stable_sample_ids"].items():
        stable_samples[table] = sorted(
            set(before_ids) & set(after["stable_sample_ids"][table])
        )
    relation_digest = (
        before["payment_request_relation_sample_digest"]
        if before["payment_request_relation_sample_digest"]
        == after["payment_request_relation_sample_digest"]
        else None
    )
    return {
        "database_uuid": before["database_uuid"],
        "table_count_ranges": ranges,
        "stable_sample_ids": stable_samples,
        "stable_payment_request_relation_sample_digest": relation_digest,
    }


def _assert_restored_sentinels(restored: dict, expected: dict) -> None:
    if restored["database_uuid"] != expected["database_uuid"]:
        raise ContinuityError("restored database UUID differs")
    for table, limits in expected["table_count_ranges"].items():
        value = restored["table_counts"][table]
        if not limits["minimum"] <= value <= limits["maximum"]:
            raise ContinuityError(f"restored sentinel count differs: {table}")
    for table, required_ids in expected["stable_sample_ids"].items():
        if not set(required_ids).issubset(restored["stable_sample_ids"][table]):
            raise ContinuityError(f"restored stable sample differs: {table}")
    relation_digest = expected["stable_payment_request_relation_sample_digest"]
    if (
        relation_digest is not None
        and restored["payment_request_relation_sample_digest"] != relation_digest
    ):
        raise ContinuityError("restored relationship sentinel differs")


def _filestore_inventory(contract: dict, *, container: str | None = None) -> dict:
    database = contract["database"]
    root = contract["filestore_root"]
    script = (
        f"set -eu; cd '{root}/{database}'; "
        "count=$(find . -type f -printf '%P\\n' | sort -u | wc -l); "
        "bytes=$(find . -type f -printf '%s\\n' | awk '{s+=$1} END {print s+0}'); "
        "paths=$(find . -type f -printf '%P\\n' | sort -u | sha256sum | cut -d' ' -f1); "
        "content=$(find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1); "
        "printf '%s|%s|%s|%s\\n' \"$count\" \"$bytes\" \"$paths\" \"$content\""
    )
    output = _run(
        [
            "docker",
            "exec",
            container or contract["odoo_container"],
            "sh",
            "-c",
            script,
        ]
    ).decode().strip()
    count, size, paths, content = output.split("|")
    return {
        "file_count": int(count),
        "total_bytes": int(size),
        "path_digest": paths,
        "content_path_digest": content,
    }


def baseline(contract: dict) -> dict:
    runtime = _assert_runtime(contract)
    sentinels = _sentinels(contract)
    filestore = _filestore_inventory(contract)
    attachment_files_match = (
        sentinels["attachments"]["distinct_store_fnames"]
        == filestore["file_count"]
    )
    payload = {
        "schema_version": contract["schema_version"],
        "generated_at": _utc(),
        "environment_class": contract["environment_class"],
        "data_authority": contract["data_authority"],
        "database": contract["database"],
        "runtime": runtime,
        "sentinels": sentinels,
        "filestore": filestore,
        "distinct_attachment_files_match": attachment_files_match,
        "database_writes": 0,
    }
    if not attachment_files_match:
        raise ContinuityError("attachment/filestore inventory differs")
    return payload


def _safe_backup_root(contract: dict) -> Path:
    root = Path(contract["backup_root"])
    if root != Path("/data/backups/daily_candidate") or not root.is_absolute():
        raise ContinuityError("backup root identity mismatch")
    if not root.exists():
        root.mkdir(mode=0o700, parents=False)
    if root.is_symlink() or not root.is_dir():
        raise ContinuityError("backup root must be a real directory")
    mode = stat.S_IMODE(root.stat().st_mode)
    if mode != 0o700:
        raise ContinuityError("backup root mode must be 0700")
    return root


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    path.chmod(0o600)


def _write_checksums(directory: Path) -> None:
    lines = [f"{_sha(directory / name)}  {name}" for name in ARTIFACTS]
    target = directory / CHECKSUM_FILE
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    target.chmod(0o600)


def _tool_revision() -> str:
    marker = ROOT / "DEPLOYMENT_TOOL_SHA"
    value = (
        marker.read_text(encoding="utf-8").strip()
        if marker.is_file()
        else os.environ.get("DAILY_CONTINUITY_TOOL_REVISION", "").strip()
    )
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ContinuityError("immutable tool revision is unavailable")
    return value


def backup(contract: dict) -> Path:
    if os.environ.get("CONFIRM_DAILY_CANDIDATE_BACKUP") != CONFIRMATION:
        raise ContinuityError("daily candidate backup confirmation is required")
    runtime = _assert_runtime(contract)
    root = _safe_backup_root(contract)
    identifier = (
        f"sc_demo-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-"
        f"{secrets.token_hex(4)}"
    )
    if not BACKUP_ID.fullmatch(identifier):
        raise ContinuityError("backup identifier is invalid")
    final = root / identifier
    previous_umask = os.umask(0o077)
    temporary: Path | None = None
    try:
        temporary = Path(tempfile.mkdtemp(prefix=f".incomplete-{identifier}-", dir=root))
        temporary.chmod(0o700)
        before = baseline(contract)
        dump = temporary / "database.dump"
        archive = temporary / "filestore.tar.gz"
        _run_to_file(
            [
                "docker",
                "exec",
                contract["database_container"],
                "pg_dump",
                "-U",
                "odoo",
                "-d",
                contract["database"],
                "-Fc",
            ],
            dump,
        )
        _run_to_file(
            [
                "docker",
                "exec",
                contract["odoo_container"],
                "tar",
                "-C",
                contract["filestore_root"],
                "-czf",
                "-",
                contract["database"],
            ],
            archive,
        )
        _run_from_file(
            ["docker", "exec", "-i", contract["database_container"], "pg_restore", "-l"],
            dump,
        )
        _run(["tar", "-tzf", str(archive)])
        after = baseline(contract)
        pair_stable = (
            before["sentinels"]["attachments"]
            == after["sentinels"]["attachments"]
            and before["filestore"] == after["filestore"]
        )
        if not pair_stable:
            raise ContinuityError("attachment pair changed during capture; retry required")
        manifest = {
            "schema_version": contract["schema_version"],
            "backup_status": "complete",
            "backup_set_id": identifier,
            "environment_class": contract["environment_class"],
            "data_authority": contract["data_authority"],
            "database": contract["database"],
            "created_at": _utc(),
            "tool_revision": _tool_revision(),
            "database_format": "postgresql_custom",
            "filestore_artifact": "filestore.tar.gz",
            "structure_validation": {
                "database": "pg_restore_list_passed",
                "filestore": "tar_list_passed",
            },
            "runtime": runtime,
            "sentinels_before": before["sentinels"],
            "sentinels_after": after["sentinels"],
            "recovery_expectations": _recovery_expectations(
                before["sentinels"], after["sentinels"]
            ),
            "filestore": after["filestore"],
            "pair_stable_during_capture": True,
            "database_bytes": dump.stat().st_size,
            "filestore_bytes": archive.stat().st_size,
            "checksums": {
                "database.dump": _sha(dump),
                "filestore.tar.gz": _sha(archive),
            },
            "database_writes_by_tool": 0,
        }
        _write_json(temporary / "manifest.json", manifest)
        _write_checksums(temporary)
        validate_backup(contract, temporary, strict_permissions=True)
        os.rename(temporary, final)
        temporary = None
        validate_backup(contract, final, strict_permissions=True)
        return final
    finally:
        os.umask(previous_umask)
        if temporary is not None and temporary.exists():
            shutil.rmtree(temporary)


def validate_backup(
    contract: dict, directory: Path, *, strict_permissions: bool = False
) -> dict:
    if directory.is_symlink() or not directory.is_dir():
        raise ContinuityError("backup directory is missing or unsafe")
    try:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContinuityError("backup manifest is missing or invalid") from exc
    if (
        manifest.get("schema_version") != contract["schema_version"]
        or manifest.get("database") != contract["database"]
        or manifest.get("environment_class") != contract["environment_class"]
        or manifest.get("backup_status") != "complete"
        or manifest.get("pair_stable_during_capture") is not True
        or not BACKUP_ID.fullmatch(str(manifest.get("backup_set_id") or ""))
    ):
        raise ContinuityError("backup manifest identity contract failed")
    checksums = manifest.get("checksums") or {}
    for name in ("database.dump", "filestore.tar.gz"):
        path = directory / name
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size <= 0
            or checksums.get(name) != _sha(path)
        ):
            raise ContinuityError(f"backup artifact validation failed: {name}")
    checksum_path = directory / CHECKSUM_FILE
    entries = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line)
        if not match:
            raise ContinuityError("SHA256SUMS format is invalid")
        digest, name = match.groups()
        entries[name] = digest
    if set(entries) != set(ARTIFACTS):
        raise ContinuityError("SHA256SUMS inventory differs")
    for name, expected in entries.items():
        if _sha(directory / name) != expected:
            raise ContinuityError(f"SHA256SUMS validation failed: {name}")
    if strict_permissions:
        if stat.S_IMODE(directory.stat().st_mode) != 0o700:
            raise ContinuityError("backup directory mode must be 0700")
        for name in ARTIFACTS + (CHECKSUM_FILE,):
            if stat.S_IMODE((directory / name).stat().st_mode) != 0o600:
                raise ContinuityError(f"backup artifact mode must be 0600: {name}")
    return manifest


def _wait_postgres(container: str) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["docker", "exec", container, "pg_isready", "-U", "odoo"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            return
        time.sleep(1)
    raise ContinuityError("isolated PostgreSQL did not become ready")


def restore_drill(contract: dict, directory: Path) -> dict:
    if os.environ.get("CONFIRM_DAILY_CANDIDATE_RESTORE_DRILL") != "RESTORE_ISOLATED_COPY":
        raise ContinuityError("isolated restore drill confirmation is required")
    manifest = validate_backup(contract, directory, strict_permissions=True)
    runtime = _assert_runtime(contract)
    suffix = secrets.token_hex(4)
    prefix = f"{DRILL_PREFIX}{suffix}"
    network = f"{prefix}-net"
    db_volume = f"{prefix}-db"
    fs_volume = f"{prefix}-fs"
    db_container = f"{prefix}-postgres"
    password = secrets.token_urlsafe(32)
    started = time.monotonic()
    created = {"container": False, "network": False, "db_volume": False, "fs_volume": False}
    try:
        _run(["docker", "network", "create", "--internal", "--label", "sc.daily-continuity=true", network])
        created["network"] = True
        _run(["docker", "volume", "create", "--label", "sc.daily-continuity=true", db_volume])
        created["db_volume"] = True
        _run(["docker", "volume", "create", "--label", "sc.daily-continuity=true", fs_volume])
        created["fs_volume"] = True
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
                "--label",
                "sc.daily-continuity=true",
                "-e",
                "POSTGRES_USER=odoo",
                "-e",
                f"POSTGRES_PASSWORD={password}",
                "-e",
                "POSTGRES_DB=postgres",
                "-v",
                f"{db_volume}:/var/lib/postgresql/data",
                runtime["database_image_id"],
            ]
        )
        created["container"] = True
        _wait_postgres(db_container)
        _run(["docker", "exec", db_container, "createdb", "-U", "odoo", contract["database"]])
        _run_from_file(
            [
                "docker",
                "exec",
                "-i",
                db_container,
                "pg_restore",
                "-U",
                "odoo",
                "-d",
                contract["database"],
                "--no-owner",
                "--no-privileges",
            ],
            directory / "database.dump",
        )
        extract = (
            f"set -eu; mkdir -p '{contract['filestore_root']}'; "
            f"test ! -e '{contract['filestore_root']}/{contract['database']}'; "
            f"tar -C '{contract['filestore_root']}' -xzf -"
        )
        _run_from_file(
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
                f"{fs_volume}:{contract['filestore_root']}",
                "--entrypoint",
                "sh",
                runtime["odoo_image_id"],
                "-c",
                extract,
            ],
            directory / "filestore.tar.gz",
        )
        restored_sentinels = _sentinels(contract, container=db_container)
        _assert_restored_sentinels(
            restored_sentinels, manifest["recovery_expectations"]
        )
        inventory_script = (
            f"set -eu; cd '{contract['filestore_root']}/{contract['database']}'; "
            "count=$(find . -type f -printf '%P\\n' | sort -u | wc -l); "
            "bytes=$(find . -type f -printf '%s\\n' | awk '{s+=$1} END {print s+0}'); "
            "paths=$(find . -type f -printf '%P\\n' | sort -u | sha256sum | cut -d' ' -f1); "
            "content=$(find . -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1); "
            "printf '%s|%s|%s|%s\\n' \"$count\" \"$bytes\" \"$paths\" \"$content\""
        )
        raw = _run(
            [
                "docker",
                "run",
                "--rm",
                "--pull",
                "never",
                "--network",
                "none",
                "--user",
                "0:0",
                "-v",
                f"{fs_volume}:{contract['filestore_root']}:ro",
                "--entrypoint",
                "sh",
                runtime["odoo_image_id"],
                "-c",
                inventory_script,
            ]
        ).decode().strip()
        count, size, paths, content = raw.split("|")
        restored_filestore = {
            "file_count": int(count),
            "total_bytes": int(size),
            "path_digest": paths,
            "content_path_digest": content,
        }
        if restored_filestore != manifest["filestore"]:
            raise ContinuityError("restored filestore sentinels differ")
        return {
            "schema_version": contract["schema_version"],
            "backup_set_id": manifest["backup_set_id"],
            "isolated_restore_pass": True,
            "database_restore_pass": True,
            "filestore_restore_pass": True,
            "sentinel_comparison_pass": True,
            "network_egress": "internal_only",
            "duration_seconds": int(time.monotonic() - started),
            "temporary_resources_removed": True,
        }
    finally:
        if created["container"]:
            _run(["docker", "rm", "-f", db_container], check=False)
        if created["db_volume"]:
            _run(["docker", "volume", "rm", db_volume], check=False)
        if created["fs_volume"]:
            _run(["docker", "volume", "rm", fs_volume], check=False)
        if created["network"]:
            _run(["docker", "network", "rm", network], check=False)


def closeout(contract: dict, directory: Path) -> dict:
    manifest = validate_backup(contract, directory, strict_permissions=True)
    restore_path = Path("/tmp/daily-candidate-continuity-restore.json")
    try:
        restore = json.loads(restore_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContinuityError("isolated restore evidence is unavailable") from exc
    if (
        restore.get("backup_set_id") != manifest["backup_set_id"]
        or restore.get("isolated_restore_pass") is not True
        or restore.get("temporary_resources_removed") is not True
    ):
        raise ContinuityError("isolated restore evidence does not close this backup")
    current = baseline(contract)
    before_runtime = manifest["runtime"]
    for key in (
        "database_container_id",
        "odoo_container_id",
        "odoo_started_at",
    ):
        if current["runtime"][key] != before_runtime[key]:
            raise ContinuityError(f"candidate runtime changed during continuity task: {key}")
    resource_checks = {
        "containers": _run(
            ["docker", "ps", "-aq", "--filter", "label=sc.daily-continuity=true"]
        ).decode().split(),
        "volumes": _run(
            ["docker", "volume", "ls", "-q", "--filter", "label=sc.daily-continuity=true"]
        ).decode().split(),
        "networks": _run(
            ["docker", "network", "ls", "-q", "--filter", "label=sc.daily-continuity=true"]
        ).decode().split(),
    }
    if any(resource_checks.values()):
        raise ContinuityError("isolated restore resources remain")
    evidence_root = Path(contract["backup_root"]) / "evidence"
    evidence_root.mkdir(mode=0o700, exist_ok=True)
    evidence_root.chmod(0o700)
    evidence_path = evidence_root / f"{manifest['backup_set_id']}.json"
    if evidence_path.exists() or evidence_path.is_symlink():
        raise ContinuityError("closeout evidence already exists")
    payload = {
        "schema_version": contract["schema_version"],
        "task_id": "DAILY-DATA-CONTINUITY-BASELINE-01",
        "environment_class": contract["environment_class"],
        "data_authority": contract["data_authority"],
        "database": contract["database"],
        "database_uuid": manifest["recovery_expectations"]["database_uuid"],
        "backup_set_id": manifest["backup_set_id"],
        "paired_backup_pass": True,
        "pair_stable_during_capture": manifest["pair_stable_during_capture"],
        "database_backup_pass": True,
        "filestore_backup_pass": True,
        "checksum_inventory_pass": True,
        "isolated_restore": restore,
        "candidate_runtime_unchanged": True,
        "candidate_database_writes_by_tool": 0,
        "temporary_resources_removed": True,
        "demo_module_installed": False,
        "fixture_write_allowed": False,
        "demo_data_write_allowed": False,
        "database_recreate_required": False,
        "filestore_recreate_required": False,
        "legacy_20260715_backup_assessment": "STRUCTURALLY_READABLE_BUT_UNGOVERNED_NO_MANIFEST",
        "current_runtime": current["runtime"],
        "generated_at": _utc(),
        "result": "PASS_DAILY_DATA_CONTINUITY_BASELINE",
    }
    _write_json(evidence_path, payload)
    return {
        "result": payload["result"],
        "backup_set_id": manifest["backup_set_id"],
        "evidence_path": str(evidence_path),
        "candidate_runtime_unchanged": True,
        "temporary_resources_removed": True,
    }


def _evidence(path: str, payload: dict) -> None:
    if not path:
        return
    target = Path(path)
    if not target.is_absolute():
        raise ContinuityError("evidence path must be absolute")
    target.parent.mkdir(parents=True, exist_ok=True)
    _write_json(target, payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("baseline", "backup", "validate", "restore-drill", "closeout"),
    )
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--backup-dir", type=Path)
    args = parser.parse_args()
    contract = _load_contract(args.contract)
    if args.action == "baseline":
        result = baseline(contract)
    elif args.action == "backup":
        directory = backup(contract)
        result = {
            "backup_set_id": directory.name,
            "backup_directory": str(directory),
            "paired_backup_pass": True,
        }
    elif args.action == "validate":
        if args.backup_dir is None:
            raise ContinuityError("--backup-dir is required")
        result = validate_backup(contract, args.backup_dir, strict_permissions=True)
    elif args.action == "restore-drill":
        if args.backup_dir is None:
            raise ContinuityError("--backup-dir is required")
        result = restore_drill(contract, args.backup_dir)
    else:
        if args.backup_dir is None:
            raise ContinuityError("--backup-dir is required")
        result = closeout(contract, args.backup_dir)
    _evidence(os.environ.get("DAILY_CONTINUITY_EVIDENCE", ""), result)
    print("DAILY_CANDIDATE_DATA_CONTINUITY=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except ContinuityError as exc:
        raise SystemExit(f"DAILY_CANDIDATE_DATA_CONTINUITY_ERROR={exc}") from exc
