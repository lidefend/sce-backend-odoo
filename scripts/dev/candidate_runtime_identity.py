#!/usr/bin/env python3
"""Record and verify the isolated candidate acceptance runtime identity."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable


SCHEMA = "candidate_runtime_identity.v1"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
PROJECT_RE = re.compile(r"^[A-Za-z0-9_-]+$")
NAMESPACE_RE = re.compile(r"^ns_[0-9a-f]{12}$")


class IdentityError(RuntimeError):
    """The candidate runtime identity cannot be recorded or verified."""


def _identifier(value: str, label: str) -> str:
    value = str(value or "").strip()
    if not IDENTIFIER_RE.fullmatch(value):
        raise IdentityError(f"{label} must be a database identifier")
    return value


def _project(value: str) -> str:
    value = str(value or "").strip()
    if not PROJECT_RE.fullmatch(value):
        raise IdentityError("compose_project must be a Docker project identifier")
    return value


def _sha(value: str) -> str:
    value = str(value or "").strip()
    if not SHA_RE.fullmatch(value):
        raise IdentityError("source SHA must be a full 40-character lowercase commit")
    return value


def _namespace(value: str) -> str:
    value = str(value or "").strip()
    if not NAMESPACE_RE.fullmatch(value):
        raise IdentityError("namespace_id must be ns_<12 lowercase hex>")
    return value


def make_identity(
    *,
    source_sha: str,
    database: str,
    compose_project: str,
    namespace_id: str,
) -> dict:
    return {
        "schema": SCHEMA,
        "producer": "scripts/dev/candidate_runtime_identity.py",
        "source_sha": _sha(source_sha),
        "database": _identifier(database, "database"),
        "compose_project": _project(compose_project),
        "namespace_id": _namespace(namespace_id),
    }


def query_namespace(
    *,
    compose_project: str,
    database: str,
    db_user: str = "odoo",
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> str:
    project = _project(compose_project)
    db_name = _identifier(database, "database")
    user = _identifier(db_user, "db_user")
    sql = (
        "SELECT namespace_id FROM sc_platform_namespace "
        f"WHERE database_name = '{db_name}' ORDER BY id LIMIT 2"
    )
    execute = runner or subprocess.run
    result = execute(
        [
            "docker", "exec", f"{project}-db-1",
            "psql", "-X", "-A", "-t", "-U", user, "-d", db_name, "-c", sql,
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise IdentityError(
            "candidate namespace readback failed: "
            + (result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}")
        )
    rows = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(rows) != 1:
        raise IdentityError(
            f"candidate database must resolve exactly one namespace, found {len(rows)}"
        )
    return _namespace(rows[0])


def write_identity(path: Path, identity: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(identity, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o644)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def verify_identity(
    payload: object,
    *,
    source_sha: str,
    database: str,
    compose_project: str,
) -> dict:
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise IdentityError("candidate runtime identity schema mismatch")
    identity = make_identity(
        source_sha=str(payload.get("source_sha") or ""),
        database=str(payload.get("database") or ""),
        compose_project=str(payload.get("compose_project") or ""),
        namespace_id=str(payload.get("namespace_id") or ""),
    )
    expected = {
        "source_sha": _sha(source_sha),
        "database": _identifier(database, "database"),
        "compose_project": _project(compose_project),
    }
    for key, value in expected.items():
        if identity[key] != value:
            raise IdentityError(
                f"candidate runtime identity {key} mismatch: "
                f"receipt={identity[key]} expected={value}"
            )
    return identity


def load_identity(
    path: Path,
    *,
    source_sha: str,
    database: str,
    compose_project: str,
) -> dict:
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise IdentityError(f"candidate runtime identity receipt missing: {path}") from exc
    except ValueError as exc:
        raise IdentityError(f"candidate runtime identity receipt is unreadable: {path}") from exc
    return verify_identity(
        payload,
        source_sha=source_sha,
        database=database,
        compose_project=compose_project,
    )


def _common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--compose-project", required=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    record = subparsers.add_parser("record")
    _common_arguments(record)
    record.add_argument("--db-user", default="odoo")
    record.add_argument("--output", required=True, type=Path)

    verify = subparsers.add_parser("verify")
    _common_arguments(verify)
    verify.add_argument("--receipt", required=True, type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "record":
            namespace_id = query_namespace(
                compose_project=args.compose_project,
                database=args.database,
                db_user=args.db_user,
            )
            identity = make_identity(
                source_sha=args.source_sha,
                database=args.database,
                compose_project=args.compose_project,
                namespace_id=namespace_id,
            )
            write_identity(args.output, identity)
            print(
                "[candidate.runtime.identity] RECORDED "
                f"source={identity['source_sha']} database={identity['database']} "
                f"namespace={identity['namespace_id']} output={args.output}"
            )
        else:
            identity = load_identity(
                args.receipt,
                source_sha=args.source_sha,
                database=args.database,
                compose_project=args.compose_project,
            )
            print(identity["namespace_id"])
        return 0
    except IdentityError as exc:
        print(f"[candidate.runtime.identity] DENY: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
