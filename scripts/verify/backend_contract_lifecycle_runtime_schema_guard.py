#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline guard for the backend contract lifecycle runtime probe artifact.

The lifecycle runtime probe is the behavioural half of the L4 evidence: fourteen
real assertions against the isolated contract-lifecycle database. Before this
guard, only the probe's own exit code protected that evidence, so the emitted
artifact could be truncated, renamed or hand-edited without any offline check.

This guard locks the declared assertion set, the bound database, the module
version and the identity digest, and it re-reads the artifact instead of trusting
a producer summary. A runtime claim that is not reproducible from this file is
not an L4 evidence artifact.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT = ROOT / os.getenv(
    "CONTRACT_LIFECYCLE_RUNTIME_PROBE_ARTIFACT",
    "artifacts/backend/backend_contract_lifecycle_runtime_probe.json",
)

PROBE_NAME = "backend_contract_lifecycle_runtime_probe"
SCHEMA_VERSION = "1.1.0"
EXPECTED_DATABASE = "sc_contract_lifecycle"
# Authority copy of the producer declaration in backend_contract_lifecycle_runtime_probe.py.
EXPECTED_CHECKS = (
    "external_version_create_rejected",
    "first_publish_hash_bound",
    "first_publish_version_one",
    "module_version_current",
    "published_definition_mutation_uses_authority",
    "published_mutation_uses_authority",
    "published_population_digest_verified",
    "published_population_integrity_complete",
    "repeat_publish_idempotent",
    "rollback_is_append_only",
    "version_deletion_rejected",
    "version_mutation_rejected",
    "version_population_digest_verified",
    "version_population_integrity_complete",
)

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def manifest_module_version() -> str:
    """The smart_core version pinned by the source manifest this guard runs in.

    The module-version lock is derived from the manifest instead of a frozen
    literal: a hand-synced literal silently rots each time a batch legitimately
    upgrades the module, while the derived value keeps binding the runtime
    evidence to the exact source tree the guard validates. An unreadable or
    versionless manifest yields "" so the identity check fails closed.
    """
    manifest_path = ROOT / "addons/smart_core/__manifest__.py"
    try:
        tree = ast.parse(manifest_path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.Expr):
                continue
            manifest = ast.literal_eval(node.value)
            if isinstance(manifest, dict):
                version = manifest.get("version")
                return str(version) if version else ""
    except (OSError, SyntaxError, ValueError):
        return ""
    return ""


def _check_assertions(payload: dict, errors: list[str]) -> None:
    """Consume the producer declaration and require the exact evaluated set."""
    declared = payload.get("declaredChecks")
    if not _string_list(declared):
        errors.append("declaredChecks must be a string list")
    else:
        if len(set(declared)) != len(declared):
            errors.append("declaredChecks must not repeat a name")
        if set(declared) != set(EXPECTED_CHECKS):
            missing = sorted(set(EXPECTED_CHECKS) - set(declared))
            extra = sorted(set(declared) - set(EXPECTED_CHECKS))
            errors.append(f"declaredChecks must equal the declared assertion set: missing={missing} extra={extra}")
    checks = payload.get("checks")
    if not isinstance(checks, dict):
        errors.append("checks must be an object")
        return
    if set(checks) != set(EXPECTED_CHECKS):
        missing = sorted(set(EXPECTED_CHECKS) - set(checks))
        extra = sorted(set(checks) - set(EXPECTED_CHECKS))
        errors.append(f"checks must contain exactly the declared assertions: missing={missing} extra={extra}")
    for name, result in checks.items():
        if result is not True:
            errors.append(f"checks.{name} must be true")
    if payload.get("checkCount") != len(EXPECTED_CHECKS):
        errors.append(f"checkCount must equal {len(EXPECTED_CHECKS)}")
    if payload.get("passedCheckCount") != len(EXPECTED_CHECKS):
        errors.append(f"passedCheckCount must equal {len(EXPECTED_CHECKS)}")
    if payload.get("errorCount") != 0:
        errors.append("errorCount must be 0")
    if payload.get("errors") != []:
        errors.append("errors must be empty")
    mismatch = payload.get("versionDigestMismatchSample")
    if not isinstance(mismatch, list):
        errors.append("versionDigestMismatchSample must be a list")
    elif mismatch:
        errors.append("versionDigestMismatchSample must be empty (published digests must be self-consistent)")


def _check_identity(payload: dict, expected_revision: str, errors: list[str]) -> None:
    if payload.get("probe") != PROBE_NAME:
        errors.append(f"probe must be {PROBE_NAME}")
    if payload.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {SCHEMA_VERSION}")
    if payload.get("database") != EXPECTED_DATABASE:
        errors.append(f"database must be {EXPECTED_DATABASE}")
    expected_module_version = manifest_module_version()
    if not expected_module_version:
        errors.append(
            "smart_core manifest version could not be derived; the artifact cannot be bound to this tree"
        )
    else:
        if payload.get("moduleVersion") != expected_module_version:
            errors.append(f"moduleVersion must be {expected_module_version}")
        if payload.get("manifestVersion") != expected_module_version:
            errors.append(f"manifestVersion must be {expected_module_version}")
    revision = payload.get("sourceRevision")
    if not isinstance(revision, str):
        errors.append("sourceRevision must be a string")
        revision = ""
    if revision and not _FULL_SHA.fullmatch(revision):
        errors.append("sourceRevision must be a full commit SHA when present")
    if expected_revision:
        if not _FULL_SHA.fullmatch(expected_revision):
            errors.append("expected revision must be a full commit SHA")
        elif revision != expected_revision:
            errors.append(f"sourceRevision must equal the expected revision {expected_revision}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    parser.add_argument("--expected-revision", default=os.getenv("ACCEPTANCE_TARGET_SHA", ""))
    args = parser.parse_args()

    path = Path(args.artifact)
    errors: list[str] = []
    payload = _load_json(path)
    if not payload:
        errors.append(f"missing or invalid json: {path}")
    else:
        _check_assertions(payload, errors)
        _check_identity(payload, str(args.expected_revision or ""), errors)

    if errors:
        print("[backend_contract_lifecycle_runtime_schema_guard] FAIL")
        for error in errors:
            print(error)
        return 2
    print("[backend_contract_lifecycle_runtime_schema_guard] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
