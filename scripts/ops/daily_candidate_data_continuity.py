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
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_runtime_duty_identity as duty_identity  # noqa: E402

DEFAULT_CONTRACT = Path(__file__).with_name(
    "daily_candidate_data_continuity_contract_v1.json"
)
ARTIFACTS = ("database.dump", "filestore.tar.gz", "manifest.json")
CHECKSUM_FILE = "SHA256SUMS"
BACKUP_ID_PATTERN = r"{prefix}-[0-9]{{8}}T[0-9]{{6}}Z-[0-9a-f]{{8}}"
DRILL_PREFIX = "sc-daily-continuity-drill-"
CONFIRMATION = "BACKUP_DAILY_CANDIDATE_PAIRED_STATE"
RESTORE_CONFIRMATION = "RESTORE_ISOLATED_COPY"
DEFAULT_RESTORE_EVIDENCE = "/tmp/daily-candidate-continuity-restore.json"
SAFE_IDENTIFIER = duty_identity.SAFE_IDENTIFIER
FILESTORE_ROOT = duty_identity.FILESTORE_ROOT
DATABASE_MOUNT = duty_identity.DATABASE_MOUNT
ODOO_DATA_MOUNT = duty_identity.ODOO_DATA_MOUNT
DRILL_ROLE = duty_identity.DRILL_ROLE


class ContinuityError(RuntimeError):
    pass


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_duties() -> dict:
    """Read the shared authority for which database each duty owns."""
    try:
        return duty_identity.load_duties()
    except duty_identity.DutyIdentityError as exc:
        raise ContinuityError(str(exc)) from exc


def _duty_identity(duty: dict) -> dict:
    """Resolve runtime identity through the one shared resolver."""
    try:
        return duty_identity.duty_identity(duty)
    except duty_identity.DutyIdentityError as exc:
        raise ContinuityError(str(exc)) from exc


def _load_contract(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContinuityError("continuity contract is missing or invalid") from exc
    if not isinstance(payload, dict):
        raise ContinuityError("continuity contract is not an object")
    name = payload.get("duty")
    if not isinstance(name, str) or not name:
        raise ContinuityError("continuity contract must name its duty")
    duties = _load_duties()
    if name not in duties:
        raise ContinuityError(f"continuity contract names an undeclared duty: {name}")
    identity = _duty_identity(duties[name])
    for key, value in identity.items():
        stated = payload.get(key)
        if stated is not None and stated != value:
            raise ContinuityError(f"contract identity mismatch: {key}")
    prefix = payload.get("backup_id_prefix") or identity["database"]
    if not SAFE_IDENTIFIER.fullmatch(str(prefix)):
        raise ContinuityError("backup id prefix is not a safe identifier")
    repository = payload.get("source_repository")
    if not isinstance(repository, str) or not repository.startswith("/"):
        raise ContinuityError("contract identity mismatch: source_repository")
    contract = dict(payload)
    contract.update(identity)
    contract["backup_id_prefix"] = prefix
    contract["backup_id"] = re.compile(BACKUP_ID_PATTERN.format(prefix=re.escape(prefix)))
    contract.setdefault("task_id", "DAILY-DATA-CONTINUITY-BASELINE-01")
    return contract


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
    if (contract["database_volume"], DATABASE_MOUNT) not in db_mounts:
        raise ContinuityError("candidate database volume identity mismatch")
    if (contract["odoo_data_volume"], ODOO_DATA_MOUNT) not in odoo_mounts:
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


def _psql(
    contract: dict,
    sql: str,
    *,
    container: str | None = None,
    role: str | None = None,
) -> str:
    output = _run(
        [
            "docker",
            "exec",
            container or contract["database_container"],
            "psql",
            "-X",
            "-U",
            role or contract["database_role"],
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


def _attachment_watermark(
    contract: dict,
    *,
    container: str | None = None,
    role: str | None = None,
) -> dict:
    row = _psql(
        contract,
        """
        SELECT count(*) || '|' || count(DISTINCT store_fname) || '|' ||
               md5(COALESCE(string_agg(DISTINCT store_fname, ',' ORDER BY store_fname), ''))
          FROM ir_attachment
         WHERE store_fname IS NOT NULL AND btrim(store_fname) <> '';
        """,
        container=container,
        role=role,
    )
    count, distinct_count, digest = row.split("|")
    return {
        "attachment_store_rows": int(count),
        "distinct_store_fnames": int(distinct_count),
        "store_fname_set_digest": digest,
    }


def _relation_sample_sql(contract: dict) -> tuple[str, str]:
    """Build the relationship sentinel from the duty's own declaration."""
    sample = contract.get("relation_sample")
    if not isinstance(sample, dict):
        raise ContinuityError("contract lacks its relationship sample")
    table = sample.get("table")
    columns = sample.get("columns")
    limit = sample.get("limit")
    if not isinstance(table, str) or not SAFE_IDENTIFIER.fullmatch(table):
        raise ContinuityError("invalid relationship sample table")
    if not isinstance(columns, list) or not columns:
        raise ContinuityError("invalid relationship sample columns")
    for column in columns:
        if not isinstance(column, str) or not SAFE_IDENTIFIER.fullmatch(column):
            raise ContinuityError("invalid relationship sample column")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
        raise ContinuityError("invalid relationship sample limit")
    projected = " || ':' || ".join(
        [f"id::text"] + [f"COALESCE({column}::text, '')" for column in columns]
    )
    sql = (
        f"SELECT md5(COALESCE(string_agg({projected}, ',' ORDER BY id), '')) "
        f"FROM (SELECT id, {', '.join(columns)} FROM {table} "
        f"ORDER BY id LIMIT {limit}) sample;"
    )
    return f"{table}_relation_sample_digest", sql


def _sentinels(
    contract: dict,
    *,
    container: str | None = None,
    role: str | None = None,
) -> dict:
    key, sql = _relation_sample_sql(contract)
    counts = {}
    for table in contract["sentinel_tables"]:
        if not SAFE_IDENTIFIER.fullmatch(table):
            raise ContinuityError("invalid sentinel table name")
        value = _psql(
            contract,
            f"SELECT CASE WHEN to_regclass('public.{table}') IS NULL "
            f"THEN '-1' ELSE (SELECT count(*)::text FROM {table}) END;",
            container=container,
            role=role,
        )
        counts[table] = int(value)
    samples = {}
    for table in contract["sample_tables"]:
        if not SAFE_IDENTIFIER.fullmatch(table):
            raise ContinuityError("invalid sample table name")
        value = _psql(
            contract,
            f"SELECT COALESCE(string_agg(id::text, ',' ORDER BY id), '') "
            f"FROM (SELECT id FROM {table} ORDER BY id LIMIT 5) sample;",
            container=container,
            role=role,
        )
        samples[table] = [int(item) for item in value.split(",") if item]
    relation_digest = _psql(contract, sql, container=container, role=role)
    database_uuid = _psql(
        contract,
        "SELECT COALESCE((SELECT value FROM ir_config_parameter "
        "WHERE key='database.uuid' LIMIT 1), '');",
        container=container,
        role=role,
    )
    if not database_uuid:
        raise ContinuityError("candidate database UUID is unavailable")
    return {
        "database_uuid": database_uuid,
        "table_counts": counts,
        "stable_sample_ids": samples,
        key: relation_digest,
        "attachments": _attachment_watermark(contract, container=container, role=role),
    }


def _relation_digest_key(contract: dict) -> str:
    key, _ = _relation_sample_sql(contract)
    return key


def _recovery_expectations(contract: dict, before: dict, after: dict) -> dict:
    if before["database_uuid"] != after["database_uuid"]:
        raise ContinuityError("database UUID changed during capture")
    key = _relation_digest_key(contract)
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
        before[key] if before[key] == after[key] else None
    )
    return {
        "database_uuid": before["database_uuid"],
        "relation_digest_key": key,
        "table_count_ranges": ranges,
        "stable_sample_ids": stable_samples,
        f"stable_{key}": relation_digest,
    }


def _assert_restored_sentinels(restored: dict, expected: dict) -> None:
    expected = dict(expected)
    expected.setdefault("relation_digest_key", "payment_request_relation_sample_digest")
    if restored["database_uuid"] != expected["database_uuid"]:
        raise ContinuityError("restored database UUID differs")
    for table, limits in expected["table_count_ranges"].items():
        value = restored["table_counts"][table]
        if not limits["minimum"] <= value <= limits["maximum"]:
            raise ContinuityError(f"restored sentinel count differs: {table}")
    for table, required_ids in expected["stable_sample_ids"].items():
        if not set(required_ids).issubset(restored["stable_sample_ids"][table]):
            raise ContinuityError(f"restored stable sample differs: {table}")
    key = expected["relation_digest_key"]
    relation_digest = expected[f"stable_{key}"]
    if relation_digest is not None and restored[key] != relation_digest:
        raise ContinuityError("restored relationship sentinel differs")


def _sha256_lines(lines: list[str]) -> str:
    digest = hashlib.sha256()
    for line in lines:
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _attachment_store_rows(
    contract: dict,
    *,
    container: str | None = None,
    role: str | None = None,
) -> list[tuple[str, str]]:
    """The live ``store_fname``/``checksum`` pairs this duty's database declares.

    ``checksum`` is Odoo's own content digest (sha1 in 17.0) and the store name
    is derived from it, so the pair is what makes "the referenced file exists"
    and "the referenced file still holds the rows' content" two separate facts.
    """
    rows = _psql(
        contract,
        "SELECT store_fname || '|' || COALESCE(checksum, '') FROM ir_attachment "
        "WHERE store_fname IS NOT NULL AND btrim(store_fname) <> '' "
        "ORDER BY store_fname;",
        container=container,
        role=role,
    )
    parsed: list[tuple[str, str]] = []
    for line in rows.splitlines():
        line = line.strip()
        if not line:
            continue
        fname, _, checksum = line.partition("|")
        parsed.append((fname, checksum))
    return parsed


#: Odoo 17 ``_mark_for_gc`` writes an *empty* file under ``filestore/<db>/checklist``
#: for every store name it wants the filestore garbage collection to consider. That
#: file is a maintenance marker, not an attachment body: it is never referenced by
#: ``ir_attachment.store_fname`` and it must not be counted as an attachment orphan.
#: ``_file_write`` creates it for every successfully written file (so an aborted
#: transaction still leaves a marker beside its body) and ``_file_delete`` creates it
#: when a row is dropped. The scan therefore classifies by that exact shape instead
#: of by subtracting one total from another.
CHECKLIST_DIRECTORY = "checklist"
STORE_FNAME = re.compile(r"[0-9a-f]{2,3}/[0-9a-f]{40}")

FILESTORE_SCAN = r"""
import hashlib, json, os, stat, sys

root = sys.argv[1]
files = []
irregular = []


def irregular_kind(path):
    mode = os.lstat(path).st_mode
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISSOCK(mode):
        return "socket"
    if stat.S_ISFIFO(mode):
        return "fifo"
    if stat.S_ISBLK(mode):
        return "block_device"
    if stat.S_ISCHR(mode):
        return "char_device"
    return "other"


if os.path.isdir(root):
    for base, dirs, names in os.walk(root):
        for name in sorted(dirs):
            full = os.path.join(base, name)
            if os.path.islink(full):
                irregular.append(
                    {"path": os.path.relpath(full, root), "kind": "symlink"}
                )
        dirs[:] = sorted(
            name for name in dirs if not os.path.islink(os.path.join(base, name))
        )
        for name in sorted(names):
            full = os.path.join(base, name)
            relative = os.path.relpath(full, root)
            if not stat.S_ISREG(os.lstat(full).st_mode):
                irregular.append({"path": relative, "kind": irregular_kind(full)})
                continue
            try:
                size = os.path.getsize(full)
                digest = hashlib.sha1()
                with open(full, "rb") as stream:
                    for chunk in iter(lambda: stream.read(1 << 20), b""):
                        digest.update(chunk)
            except OSError as error:
                irregular.append(
                    {"path": relative, "kind": "unreadable", "detail": str(error)[:120]}
                )
                continue
            files.append({"path": relative, "size": size, "sha1": digest.hexdigest()})

files.sort(key=lambda row: row["path"])
irregular.sort(key=lambda row: row["path"])
print(json.dumps(
    {"root": root, "root_present": os.path.isdir(root), "files": files, "irregular": irregular},
    sort_keys=True,
))
"""


def _scan_filestore(contract: dict, *, container: str | None = None) -> dict:
    """Read the duty's own filestore tree without writing anywhere."""
    root = f"{contract['filestore_root']}/{contract['filestore_scope']}"
    output = _run(
        [
            "docker",
            "exec",
            "-i",
            container or contract["odoo_container"],
            "python3",
            "-",
            root,
        ],
        input_bytes=FILESTORE_SCAN.encode("utf-8"),
    )
    return _parse_filestore_scan(output)


def _scan_volume_filestore(contract: dict, *, image: str, volume: str) -> dict:
    """Scan a filestore that only exists inside a detached volume."""
    root = f"{contract['filestore_root']}/{contract['filestore_scope']}"
    output = _run(
        [
            "docker",
            "run",
            "--rm",
            # ``-i`` is not optional here: the scan program is delivered through
            # stdin, and a detached ``docker run`` without it never receives the
            # program, exits 0 with empty stdout, and looks like a scan that
            # returned no inventory.
            "-i",
            "--pull",
            "never",
            "--network",
            "none",
            "--user",
            "0:0",
            "-v",
            f"{volume}:{contract['filestore_root']}:ro",
            "--entrypoint",
            "python3",
            image,
            "-",
            root,
        ],
        input_bytes=FILESTORE_SCAN.encode("utf-8"),
    )
    return _parse_filestore_scan(output)


def _parse_filestore_scan(output: bytes) -> dict:
    text = output.decode(errors="replace").strip()
    try:
        scan = json.loads(text.splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as exc:
        raise ContinuityError("filestore scan did not return its inventory") from exc
    if not isinstance(scan, dict) or not isinstance(scan.get("files"), list):
        raise ContinuityError("filestore scan returned a malformed inventory")
    return scan


def _filestore_aggregate(scan: dict) -> dict:
    files = scan["files"]
    return {
        "file_count": len(files),
        "total_bytes": sum(int(row["size"]) for row in files),
        "path_digest": _sha256_lines(sorted(row["path"] for row in files)),
        "content_path_digest": _sha256_lines(
            sorted(
                f"{row['path']}\t{row['size']}\t{row['sha1']}" for row in files
            )
        ),
    }


def _classify_filestore(scan: dict, store_rows: list[tuple[str, str]]) -> dict:
    """Separate attachment bodies, collection markers and unexplained entries.

    Four classes, and nothing is excluded by directory name alone:

    * ``body`` -- the relative path is a live ``store_fname``. It has to exist,
      and its content digest has to equal both the store name and the row's own
      ``checksum``; either mismatch is a real attachment defect.
    * ``maintenance marker`` -- an empty file under ``checklist`` whose relative
      path has the store-name shape Odoo's ``_mark_for_gc`` writes. Counted on
      its own and kept; it is not an attachment orphan.
    * ``pending collection body`` -- a store-named body that no live row
      references *and* whose name is listed in ``checklist``. Odoo 17 never
      unlinks an attachment file on deletion: ``_file_delete`` only marks the
      name, and ``_gc_file_store_unsafe`` later unlinks the body and then the
      marker. A body in that state is a deleted attachment waiting for the
      collector, so treating it as unexplained would only assert that the
      collector had already run. It is counted separately and kept.
    * ``unknown`` -- everything else, including unreferenced files that merely
      look like store names while carrying no marker, non-empty checklist
      entries, and any non-regular entry. These keep failing the guard so they
      get investigated. Without the marker nothing in Odoo will ever collect
      such a file, which is exactly what makes it unexplained.
    """
    referenced = {fname: checksum for fname, checksum in store_rows}
    present = set()
    bodies: list[str] = []
    markers: list[str] = []
    pending: list[str] = []
    marked: set[str] = set()
    candidates: list[dict] = []
    missing: list[str] = []
    mismatched: list[dict] = []
    unknown: list[dict] = []
    body_content: list[str] = []
    for row in scan["files"]:
        path = row["path"]
        if path.startswith(CHECKLIST_DIRECTORY + "/"):
            name = path[len(CHECKLIST_DIRECTORY) + 1 :]
            if int(row["size"]) == 0 and STORE_FNAME.fullmatch(name):
                markers.append(path)
                marked.add(name)
            else:
                unknown.append(
                    {
                        "path": path,
                        "size": int(row["size"]),
                        "reason": "checklist entry that is not a collection marker",
                    }
                )
            continue
        candidates.append(row)
    for row in candidates:
        path = row["path"]
        present.add(path)
        if path in referenced:
            if not STORE_FNAME.fullmatch(path) or path.rsplit("/", 1)[-1] != row["sha1"]:
                mismatched.append(
                    {
                        "path": path,
                        "reason": "store name is not the content digest",
                        "file_sha1": row["sha1"],
                    }
                )
                continue
            expected = referenced[path]
            if expected and expected != row["sha1"]:
                mismatched.append(
                    {
                        "path": path,
                        "reason": "file content differs from the recorded checksum",
                        "database_checksum": expected,
                        "file_sha1": row["sha1"],
                    }
                )
                continue
            bodies.append(path)
            body_content.append(f"{path}\t{row['sha1']}")
        elif path in marked:
            if path.rsplit("/", 1)[-1] != row["sha1"]:
                mismatched.append(
                    {
                        "path": path,
                        "reason": "store name is not the content digest",
                        "file_sha1": row["sha1"],
                    }
                )
                continue
            pending.append(path)
        else:
            unknown.append(
                {
                    "path": path,
                    "size": int(row["size"]),
                    "reason": "unreferenced file with no collection marker",
                }
            )
    for fname in referenced:
        if fname not in present:
            missing.append(fname)
    for row in scan.get("irregular") or []:
        unknown.append(
            {
                "path": str(row.get("path")),
                "reason": "non-regular entry (%s)" % (row.get("kind"),),
            }
        )
    return {
        "referenced_attachment_count": len(referenced),
        "referenced_body_count": len(bodies),
        "maintenance_marker_count": len(markers),
        "pending_collection_body_count": len(pending),
        "unknown_entry_count": len(unknown),
        "missing_count": len(missing),
        "checksum_mismatch_count": len(mismatched),
        "missing_store_fnames": sorted(missing)[:20],
        "checksum_mismatches": mismatched[:20],
        "unknown_entries": unknown[:20],
        "referenced_body_path_digest": _sha256_lines(sorted(bodies)),
        "referenced_body_content_digest": _sha256_lines(sorted(body_content)),
        "maintenance_marker_digest": _sha256_lines(sorted(markers)),
        "pending_collection_body_path_digest": _sha256_lines(sorted(pending)),
    }


def _assert_filestore_inventory(inventory: dict) -> None:
    """Fail closed on the three ways a filestore can stop being that database's.

    The assertions are separate on purpose: "every referenced attachment is
    present and readable with its recorded content" and "nothing unexplained
    sits in the tree" are different facts, and a version that only compares two
    totals cannot tell them apart.

    Bodies pending collection are deliberately not one of the three: Odoo 17
    marks a deleted attachment's file for collection instead of unlinking it, so
    their presence says the collector has not run, not that the filestore is
    inconsistent. They are counted in the inventory and never asserted away.
    """
    if inventory["missing_count"]:
        raise ContinuityError(
            "referenced attachment files are missing: %d" % inventory["missing_count"]
        )
    if inventory["checksum_mismatch_count"]:
        raise ContinuityError(
            "referenced attachment content does not match its recorded checksum: %d"
            % inventory["checksum_mismatch_count"]
        )
    if inventory["unknown_entry_count"]:
        raise ContinuityError(
            "unknown filestore entries: %d" % inventory["unknown_entry_count"]
        )


def _read_filestore(
    contract: dict,
    *,
    container: str | None = None,
    role: str | None = None,
) -> tuple[dict, dict]:
    scan = _scan_filestore(contract, container=container)
    if not scan.get("root_present"):
        raise ContinuityError("filestore scope directory is unavailable")
    aggregate = _filestore_aggregate(scan)
    inventory = _classify_filestore(
        scan, _attachment_store_rows(contract, container=container, role=role)
    )
    return aggregate, inventory


def baseline(contract: dict) -> dict:
    runtime = _assert_runtime(contract)
    sentinels = _sentinels(contract)
    filestore, attachment_inventory = _read_filestore(contract)
    payload = {
        "schema_version": contract["schema_version"],
        "generated_at": _utc(),
        "environment_class": contract["environment_class"],
        "data_authority": contract["data_authority"],
        "database": contract["database"],
        "runtime": runtime,
        "sentinels": sentinels,
        "filestore": filestore,
        "attachment_inventory": attachment_inventory,
        "database_writes": 0,
    }
    _assert_filestore_inventory(attachment_inventory)
    return payload


def _safe_backup_root(contract: dict) -> Path:
    root = Path(contract["backup_root"])
    if not root.is_absolute() or root.parent != Path("/data/backups"):
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
        f"{contract['backup_id_prefix']}-"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-"
        f"{secrets.token_hex(4)}"
    )
    if not contract["backup_id"].fullmatch(identifier):
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
                contract["database_role"],
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
                contract["filestore_scope"],
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
            and before["attachment_inventory"] == after["attachment_inventory"]
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
                contract, before["sentinels"], after["sentinels"]
            ),
            "filestore": after["filestore"],
            "attachment_inventory": after["attachment_inventory"],
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
        or not contract["backup_id"].fullmatch(str(manifest.get("backup_set_id") or ""))
    ):
        raise ContinuityError("backup manifest identity contract failed")
    inventory = manifest.get("attachment_inventory")
    if not isinstance(inventory, dict):
        raise ContinuityError("backup manifest carries no attachment inventory")
    if inventory.get("missing_count") or inventory.get("checksum_mismatch_count"):
        raise ContinuityError("backup was captured with a broken attachment pair")
    if inventory.get("unknown_entry_count"):
        raise ContinuityError("backup was captured with unexplained filestore entries")
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
    if os.environ.get("CONFIRM_DAILY_CANDIDATE_RESTORE_DRILL") != RESTORE_CONFIRMATION:
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
        restored_sentinels = _sentinels(
            contract, container=db_container, role=DRILL_ROLE
        )
        _assert_restored_sentinels(
            restored_sentinels, manifest["recovery_expectations"]
        )
        restored_scan = _scan_volume_filestore(
            contract, image=runtime["odoo_image_id"], volume=fs_volume
        )
        restored_filestore = _filestore_aggregate(restored_scan)
        restored_inventory = _classify_filestore(
            restored_scan,
            _attachment_store_rows(contract, container=db_container, role=DRILL_ROLE),
        )
        source_inventory = manifest["attachment_inventory"]
        if restored_inventory["missing_count"] or restored_inventory["checksum_mismatch_count"]:
            raise ContinuityError(
                "restored filestore is missing or corrupt for a referenced attachment"
            )
        if restored_inventory["unknown_entry_count"]:
            raise ContinuityError("restored filestore contains unexplained entries")
        if restored_filestore != manifest["filestore"]:
            raise ContinuityError("restored filestore inventory differs from the source")
        # Two separate closures, because they can fail independently: every
        # referenced attachment is back, and the bytes that came back are the
        # bytes that went in. A single count comparison proves neither.
        if restored_inventory["referenced_body_count"] != source_inventory["referenced_body_count"]:
            raise ContinuityError(
                "restored filestore does not hold every referenced attachment"
            )
        if (
            restored_inventory["referenced_body_content_digest"]
            != source_inventory["referenced_body_content_digest"]
        ):
            raise ContinuityError(
                "restored attachment content differs from the source"
            )
        if (
            restored_inventory["maintenance_marker_digest"]
            != source_inventory["maintenance_marker_digest"]
        ):
            raise ContinuityError(
                "restored filestore maintenance markers differ from the source"
            )
        return {
            "schema_version": contract["schema_version"],
            "backup_set_id": manifest["backup_set_id"],
            "isolated_restore_pass": True,
            "database_restore_pass": True,
            "filestore_restore_pass": True,
            "all_attachments_present": True,
            "restored_content_matches_source": True,
            "maintenance_markers_preserved": True,
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
    restore_path = Path(
        os.environ.get("DAILY_CONTINUITY_RESTORE_EVIDENCE", DEFAULT_RESTORE_EVIDENCE)
    )
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
    upgrade = contract.get("upgrade_contract")
    if not isinstance(upgrade, dict):
        upgrade = {}
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
        "task_id": contract["task_id"],
        "duty": contract["duty"],
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
        "duty_data_purpose": contract["data_purpose"],
        "fixture_write_allowed": bool(
            upgrade.get("fixture_write_allowed", False)
        ),
        "demo_data_write_allowed": bool(
            upgrade.get("demo_data_write_allowed", False)
        ),
        "database_recreate_required": bool(
            upgrade.get("database_recreate_required", False)
        ),
        "filestore_recreate_required": bool(
            upgrade.get("filestore_recreate_required", False)
        ),
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
