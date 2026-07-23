#!/usr/bin/env python3
"""Fail-closed contract for formal database lifecycle commands."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

SAFE_NAME = re.compile(r"^[a-z][a-z0-9_]{2,62}$")
FORMAL_DATABASES = {"sc_migration_rehearsal", "sc_production"}
RESERVED_DATABASES = {"postgres", "template0", "template1", "sc_prod"}
MUTATING_ACTIONS = {"init", "install", "upgrade", "configure-platform", "initialize-platform-snapshot"}
PRODUCTION_CONFIRMATION = "I_ACKNOWLEDGE_SC_PRODUCTION_CHANGE"


class ContractError(ValueError):
    pass


def _truthy(value: str | None) -> bool:
    return (value or "").lower() in {"1", "true", "yes"}


def _validate_release_manifest(env: dict[str, str], expected_sha: str) -> None:
    manifest_value = (env.get("RELEASE_MANIFEST_PATH") or "").strip()
    checksum_value = (env.get("RELEASE_MANIFEST_CHECKSUM_PATH") or "").strip()
    expected_digest = (env.get("EXPECTED_IMAGE_DIGEST") or "").strip()
    if not manifest_value or not checksum_value:
        raise ContractError("release manifest and checksum paths are required")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", expected_digest):
        raise ContractError("EXPECTED_IMAGE_DIGEST must be a sha256 digest")
    manifest = Path(manifest_value)
    checksum = Path(checksum_value)
    try:
        raw = manifest.read_bytes()
        locked_sha256 = checksum.read_text(encoding="utf-8").strip().split()[0]
        payload = json.loads(raw)
    except (OSError, IndexError, json.JSONDecodeError) as exc:
        raise ContractError("release manifest or checksum is missing or invalid") from exc
    if not re.fullmatch(r"[0-9a-f]{64}", locked_sha256):
        raise ContractError("release manifest checksum is invalid")
    if hashlib.sha256(raw).hexdigest() != locked_sha256:
        raise ContractError("release manifest checksum mismatch")
    if not isinstance(payload, dict):
        raise ContractError("release manifest must be a JSON object")
    for field in ("source_sha", "oci_revision"):
        if payload.get(field) != expected_sha:
            raise ContractError(f"release manifest {field} must match EXPECTED_RELEASE_SHA")
    if payload.get("image_digest") != expected_digest:
        raise ContractError("release manifest image_digest must match EXPECTED_IMAGE_DIGEST")


def validate(action: str, env: dict[str, str] | None = None) -> str:
    env = dict(os.environ if env is None else env)
    if action not in {"runtime", "preflight", "health", *MUTATING_ACTIONS}:
        raise ContractError(f"unsupported action: {action}")

    db = (env.get("TARGET_DB") or env.get("ODOO_DB") or env.get("DB_NAME") or "").strip()
    if not db:
        raise ContractError("TARGET_DB/ODOO_DB is required")
    if not SAFE_NAME.fullmatch(db) or db in RESERVED_DATABASES:
        raise ContractError(f"database name is forbidden: {db}")

    contract_test = env.get("SC_ENVIRONMENT") == "contract_test" and _truthy(env.get("SC_CONTRACT_TEST_MODE"))
    if db not in FORMAL_DATABASES and not (contract_test and db.startswith("sc_contract_hardening_test_")):
        raise ContractError("database is outside the formal release contract")

    if db == "sc_production" and env.get("SC_ENVIRONMENT") != "production":
        raise ContractError("sc_production requires SC_ENVIRONMENT=production")
    if db == "sc_migration_rehearsal" and env.get("SC_ENVIRONMENT") != "migration_rehearsal":
        raise ContractError("rehearsal database requires SC_ENVIRONMENT=migration_rehearsal")

    platform_db = (env.get("PLATFORM_RELEASE_DB") or "").strip()
    if not platform_db:
        raise ContractError("PLATFORM_RELEASE_DB is required")
    if platform_db != db:
        raise ContractError("PLATFORM_RELEASE_DB must match the target database")

    allow_demo = _truthy(env.get("SC_ALLOW_DEMO_DATA"))
    if db == "sc_production" and allow_demo:
        raise ContractError("demo/fixture data is forbidden for sc_production")
    if action in {"runtime", "preflight", "health"} and allow_demo:
        raise ContractError("normal runtime and read-only checks cannot enable demo data")

    expected_scope = db
    if env.get("SC_FILESTORE_SCOPE") != expected_scope:
        raise ContractError("filestore scope must exactly match the target database")
    volume_pairs = {
        "SC_DATABASE_VOLUME": f"sce-{db}-postgres",
        "SC_REDIS_VOLUME": f"sce-{db}-redis",
        "SC_FILESTORE_VOLUME": f"sce-{db}-filestore",
        "SC_SESSION_VOLUME": f"sce-{db}-sessions",
        "SC_TMP_VOLUME": f"sce-{db}-tmp",
        "SC_LOG_VOLUME": f"sce-{db}-logs",
    }
    for key, expected in volume_pairs.items():
        if env.get(key) != expected:
            raise ContractError(f"{key} must be {expected}")

    if action in MUTATING_ACTIONS:
        expected_sha = env.get("EXPECTED_RELEASE_SHA", "")
        image_sha = env.get("SC_SOURCE_REVISION", "")
        if not re.fullmatch(r"[0-9a-f]{40}", expected_sha) or expected_sha != image_sha:
            raise ContractError("EXPECTED_RELEASE_SHA must match the immutable image revision")
        _validate_release_manifest(env, expected_sha)
        if db == "sc_production" and env.get("SC_PRODUCTION_CHANGE_APPROVED") != PRODUCTION_CONFIRMATION:
            raise ContractError("explicit sc_production change approval is required")
        module = env.get("TARGET_MODULE", "base" if action == "init" else "")
        if action in {"install", "upgrade"} and not re.fullmatch(r"[a-z][a-z0-9_]*", module):
            raise ContractError("TARGET_MODULE is required and invalid")
        if db == "sc_production" and re.search(r"(?:demo|fixture)", module):
            raise ContractError("demo/fixture modules are forbidden for sc_production")
    return db


def main() -> None:
    action = sys.argv[1] if len(sys.argv) == 2 else ""
    try:
        db = validate(action)
    except ContractError as exc:
        raise SystemExit(f"[production-db-contract] BLOCKED: {exc}") from exc
    print(f"[production-db-contract] PASS action={action} database={db}")


if __name__ == "__main__":
    main()
