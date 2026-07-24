#!/usr/bin/env python3
"""Fail-closed contracts for a daily-candidate clone upgrade rehearsal.

This P4 tool validates immutable candidate identity, clone isolation, migration
intent, idempotency and evidence before an operator may run any state-changing
Make target.  It deliberately performs no source-environment mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_CONTRACT = Path(__file__).with_name(
    "daily_candidate_clone_upgrade_contract_v1.json"
)
SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
IMAGE_REF = re.compile(
    r"^(?P<repository>[a-z0-9][a-z0-9._/-]*)@(?P<digest>sha256:[0-9a-f]{64})$"
)
SAFE_NAME = re.compile(r"^sc-rc6-rehearsal-[a-z0-9-]+$")
REHEARSAL_ID = re.compile(
    r"^sc_demo-rc6-rehearsal-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$"
)
FORBIDDEN_COMMAND_PATTERNS = (
    re.compile(r"(^|\s)-i(\s|$)"),
    re.compile(r"(^|\s)--init(?:=|\s|$)"),
    re.compile(r"(?:^|[^a-z0-9])(?:demo|fixture|reset)(?:[^a-z0-9]|$)", re.IGNORECASE),
    re.compile(r"\bdown\s+-v\b", re.IGNORECASE),
    re.compile(r"\b(?:dropdb|DROP\s+DATABASE|TRUNCATE)\b", re.IGNORECASE),
)
SENSITIVE_KEYS = re.compile(
    r"(?:password|passwd|secret|token|cookie|session|authorization|credential)",
    re.IGNORECASE,
)
SENSITIVE_VALUE = re.compile(
    r"(?:Bearer\s+[A-Za-z0-9._~+/=-]+|session_id=|password=|token=)",
    re.IGNORECASE,
)


class RehearsalError(RuntimeError):
    """A fail-closed rehearsal contract violation."""


class CandidateNotFrozen(RehearsalError):
    """No approved immutable RC6 candidate has been supplied."""


def _load_json(path: Path, label: str) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RehearsalError(f"{label} is missing or invalid") from exc
    if not isinstance(payload, dict):
        raise RehearsalError(f"{label} must be a JSON object")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_contract(path: Path = DEFAULT_CONTRACT) -> dict:
    contract = _load_json(path, "clone rehearsal contract")
    expected = {
        "schema_version": "daily_candidate_clone_upgrade_rehearsal.v1",
        "environment_classification": "DAILY_CANDIDATE_CLONE_REHEARSAL",
        "source_environment_classification": "DAILY_CANDIDATE_ENVIRONMENT",
        "source_database_name": "sc_demo",
        "source_database_uuid": "c838b4b6-4cd6-11f1-9590-82245e4e7b62",
        "continuity_backup_set_id": "sc_demo-20260724T032145Z-6eb277d1",
        "sentinel_set_id": "sc_demo-sentinel-20260724T040527Z-1fa42479",
        "sentinel_evidence_sha256": (
            "1083bae745568fbaef1404c060c76078bec33c4bb7c18a4a9033689c3762257f"
        ),
        "fixed_repository_base_sha": (
            "8962c8e0b831c4ac93e15a6d503740113dcd2c57"
        ),
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            raise RehearsalError(f"clone rehearsal contract identity mismatch: {key}")
    candidate = contract.get("candidate") or {}
    if candidate.get("name") != "RC6":
        raise RehearsalError("candidate name must be RC6")
    required = candidate.get("required_ancestor_commits") or []
    if expected["fixed_repository_base_sha"] not in required:
        raise RehearsalError("fixed repository base must be a candidate ancestor")
    if contract.get("source_writes_allowed") != {
        "database": False,
        "filestore": False,
        "application_upgrade": False,
    }:
        raise RehearsalError("source write policy must fail closed")
    if contract.get("production_access_allowed") is not False:
        raise RehearsalError("production access must be forbidden")
    return contract


def _git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if check and result.returncode:
        raise RehearsalError(
            f"git identity check failed: {result.stderr.strip() or args[0]}"
        )
    return result.stdout.strip()


def validate_candidate_payload(
    contract: dict,
    payload: dict,
    *,
    repository_head: str,
    worktree_clean: bool,
    ancestor_commits: set[str],
) -> dict:
    source_sha = str(payload.get("source_sha") or "")
    if not SHA.fullmatch(source_sha):
        raise CandidateNotFrozen("RC6_CANDIDATE_SHA must be a full 40-character SHA")
    if payload.get("candidate_name") != contract["candidate"]["name"]:
        raise CandidateNotFrozen("candidate declaration does not designate RC6")
    if payload.get("approval_status") != "FROZEN":
        raise CandidateNotFrozen("RC6 candidate approval status is not FROZEN")
    if payload.get("ci_status") != "PASS" or not payload.get("ci_run_url"):
        raise CandidateNotFrozen("RC6 candidate full CI evidence is unavailable")
    if repository_head != source_sha or not worktree_clean:
        raise CandidateNotFrozen("candidate checkout is not clean at the frozen SHA")
    missing = sorted(
        set(contract["candidate"]["required_ancestor_commits"]) - ancestor_commits
    )
    if missing:
        raise CandidateNotFrozen(
            "RC6 candidate does not contain required merged baselines: "
            + ",".join(missing)
        )
    image_ref = str(payload.get("image_ref") or "")
    match = IMAGE_REF.fullmatch(image_ref)
    if not match:
        raise CandidateNotFrozen("RC6 image must use repository@sha256:<digest>")
    if match.group("repository") != contract["candidate"]["image_repository"]:
        raise CandidateNotFrozen("RC6 image repository identity mismatch")
    if payload.get("image_revision_label") != source_sha:
        raise CandidateNotFrozen("RC6 image revision does not match candidate SHA")
    if payload.get("image_pull_policy") != "never":
        raise CandidateNotFrozen("RC6 rehearsal must use pull policy never")
    if payload.get("image_locally_available") is not True:
        raise CandidateNotFrozen("RC6 immutable image is not locally available")
    return {
        "rc6_candidate_sha": source_sha,
        "rc6_image_ref": image_ref,
        "rc6_image_digest": match.group("digest"),
        "candidate_frozen": True,
        "full_ci_pass": True,
        "required_baselines_present": True,
        "image_revision_traceability_pass": True,
    }


def validate_image_inspect(image_ref: str, source_sha: str, rows: Any) -> dict:
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise CandidateNotFrozen("RC6 immutable image is not locally inspectable")
    image = rows[0]
    labels = (image.get("Config") or {}).get("Labels") or {}
    if labels.get("org.opencontainers.image.revision") != source_sha:
        raise CandidateNotFrozen("local RC6 image OCI revision does not match candidate SHA")
    local_id = str(image.get("Id") or "")
    if not DIGEST.fullmatch(local_id):
        raise CandidateNotFrozen("local RC6 image config identity is invalid")
    return {
        "local_image_config_digest": local_id,
        "local_image_revision_traceability_pass": True,
        "network_image_pull_performed": False,
    }


def freeze_candidate(contract: dict, manifest_path: Path, repo: Path) -> dict:
    if not manifest_path.is_file():
        raise CandidateNotFrozen(
            "approved RC6 candidate manifest is required before clone restore"
        )
    payload = _load_json(manifest_path, "RC6 candidate manifest")
    source_sha = str(payload.get("source_sha") or "")
    head = _git(repo, "rev-parse", "HEAD")
    clean = not bool(_git(repo, "status", "--porcelain"))
    ancestors = set()
    if SHA.fullmatch(source_sha):
        for required in contract["candidate"]["required_ancestor_commits"]:
            result = subprocess.run(
                ["git", "-C", str(repo), "merge-base", "--is-ancestor", required, source_sha],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode == 0:
                ancestors.add(required)
    result = validate_candidate_payload(
        contract,
        payload,
        repository_head=head,
        worktree_clean=clean,
        ancestor_commits=ancestors,
    )
    inspected = subprocess.run(
        ["docker", "image", "inspect", result["rc6_image_ref"]],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if inspected.returncode:
        raise CandidateNotFrozen("RC6 immutable image is not present in the local daemon")
    try:
        rows = json.loads(inspected.stdout)
    except json.JSONDecodeError as exc:
        raise CandidateNotFrozen("local RC6 image inspection is invalid") from exc
    result.update(
        validate_image_inspect(result["rc6_image_ref"], result["rc6_candidate_sha"], rows)
    )
    return result


def validate_source_artifacts(contract: dict, payload: dict) -> dict:
    expected = {
        "source_database_name": contract["source_database_name"],
        "source_database_uuid": contract["source_database_uuid"],
        "continuity_backup_set_id": contract["continuity_backup_set_id"],
        "sentinel_set_id": contract["sentinel_set_id"],
        "sentinel_evidence_sha256": contract["sentinel_evidence_sha256"],
        "source_application_revision_prefix": "6095e201",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RehearsalError(f"source identity mismatch: {key}")
    if payload.get("continuity_integrity_pass") is not True:
        raise RehearsalError("continuity backup integrity is not proven")
    if payload.get("sentinel_integrity_pass") is not True:
        raise RehearsalError("sentinel evidence integrity is not proven")
    if payload.get("source_runtime_healthy") is not True:
        raise RehearsalError("source daily runtime is not healthy")
    return {"source_readonly_preflight_pass": True}


def _validate_commands(commands: list[str]) -> None:
    if not commands or not all(isinstance(row, str) and row.strip() for row in commands):
        raise RehearsalError("versioned upgrade commands are required")
    for command in commands:
        for pattern in FORBIDDEN_COMMAND_PATTERNS:
            if pattern.search(command):
                raise RehearsalError(f"forbidden upgrade path detected: {pattern.pattern}")


def validate_isolation(contract: dict, payload: dict) -> dict:
    required_names = ("project", "database_container", "odoo_container", "network")
    for key in required_names:
        if not SAFE_NAME.fullmatch(str(payload.get(key) or "")):
            raise RehearsalError(f"unsafe clone resource identity: {key}")
    names = [str(payload[key]) for key in required_names]
    names.extend(str(item) for item in payload.get("volumes") or [])
    if len(names) != len(set(names)):
        raise RehearsalError("clone resource identities must be unique")
    if not payload.get("volumes") or not all(
        SAFE_NAME.fullmatch(str(item)) for item in payload["volumes"]
    ):
        raise RehearsalError("clone volumes must use the rehearsal namespace")
    if payload.get("network_internal") is not True:
        raise RehearsalError("clone data network must be internal-only")
    if payload.get("public_egress_allowed") is not False:
        raise RehearsalError("clone public egress must be disabled")
    if payload.get("cron_enabled") is not False:
        raise RehearsalError("clone cron must be disabled")
    integrations = payload.get("external_write_integrations") or {}
    required_integrations = set(contract["isolation"]["external_write_integrations"])
    if set(integrations) != required_integrations or any(integrations.values()):
        raise RehearsalError("all external write integrations must be disabled")
    if payload.get("production_secrets_mounted") is not False:
        raise RehearsalError("production secrets must not be mounted")
    if payload.get("source_database_connected") is not False:
        raise RehearsalError("clone must not connect to the source database")
    if payload.get("source_filestore_mount_mode") not in (None, "none"):
        raise RehearsalError("source filestore must not be mounted into the clone")
    mounts = payload.get("mounts") or []
    forbidden_roots = tuple(contract["isolation"]["forbidden_mount_roots"])
    for mount in mounts:
        source = str((mount or {}).get("source") or "")
        if any(source == root or source.startswith(root + "/") for root in forbidden_roots):
            raise RehearsalError("daily or production persistent storage mount is forbidden")
    _validate_commands(payload.get("upgrade_commands") or [])
    return {
        "clone_isolation_contract_pass": True,
        "source_database_connected": False,
        "source_filestore_mounted": False,
        "external_write_integrations_disabled": True,
    }


def build_migration_plan(contract: dict, payload: dict) -> dict:
    old_modules = payload.get("old_modules") or {}
    target_modules = payload.get("target_modules") or {}
    if not isinstance(old_modules, dict) or not isinstance(target_modules, dict):
        raise RehearsalError("module inventories must be objects")
    selected = []
    for name in sorted(set(old_modules) | set(target_modules)):
        old = old_modules.get(name)
        new = target_modules.get(name)
        if old != new:
            selected.append({"module": name, "old_version": old, "target_version": new})
    commands = payload.get("upgrade_commands") or []
    _validate_commands(commands)
    operations = payload.get("operations") or []
    destructive = sorted(
        str(row.get("id"))
        for row in operations
        if row.get("destructive") is True
    )
    irreversible = sorted(
        str(row.get("id"))
        for row in operations
        if row.get("irreversible") is True
    )
    undeclared = sorted(
        str(row.get("id"))
        for row in operations
        if (row.get("destructive") or row.get("irreversible"))
        and row.get("declared") is not True
    )
    if undeclared:
        raise RehearsalError(
            "undeclared destructive or irreversible migration: " + ",".join(undeclared)
        )
    mappings = payload.get("model_mappings") or []
    if any(not row.get("versioned") for row in mappings):
        raise RehearsalError("model replacement requires a versioned mapping")
    if payload.get("demo_or_fixture_write") is not False:
        raise RehearsalError("demo or fixture writes are forbidden")
    if payload.get("unknown_origin_delete") is not False:
        raise RehearsalError("UNKNOWN_ORIGIN deletion is forbidden")
    backward_compatible = payload.get("backward_compatible") is True
    rollback_mode = (
        "APPLICATION_IMAGE_ROLLBACK"
        if backward_compatible and not irreversible
        else "PAIRED_DATABASE_FILESTORE_RESTORE"
    )
    return {
        "schema_version": contract["migration"]["plan_schema_version"],
        "database_migration_required": bool(selected or operations),
        "migration_plan_versioned": payload.get("plan_versioned") is True,
        "upgraded_modules": selected,
        "operations": sorted(operations, key=lambda row: str(row.get("id"))),
        "model_mappings": sorted(mappings, key=lambda row: str(row.get("source"))),
        "destructive_migration_detected": bool(destructive),
        "irreversible_migration_detected": bool(irreversible),
        "rollback_mode": rollback_mode,
        "upgrade_commands": commands,
    }


def validate_sentinel_preservation(payload: dict) -> dict:
    required_true = (
        "comparison_pass",
        "fixed_sample_preservation_pass",
        "core_relationship_preservation_pass",
        "attachment_preservation_pass",
        "orphan_regression_pass",
        "unknown_origin_preservation_pass",
    )
    missing = [key for key in required_true if payload.get(key) is not True]
    if missing:
        raise RehearsalError("post-upgrade sentinel regression: " + ",".join(missing))
    return {key: True for key in required_true}


def validate_repeated_upgrade(payload: dict) -> dict:
    required = (
        "same_entrypoint",
        "exit_code_zero",
        "business_record_delta_zero",
        "duplicate_xmlid_count_zero",
        "permission_regression_absent",
        "post_repeat_sentinel_compare_pass",
    )
    failed = [key for key in required if payload.get(key) is not True]
    if failed:
        raise RehearsalError("upgrade entrypoint is not idempotent: " + ",".join(failed))
    return {
        "repeated_upgrade_pass": True,
        "migration_idempotency_pass": True,
        "post_repeat_sentinel_compare_pass": True,
    }


def assert_no_sensitive_output(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if SENSITIVE_KEYS.search(str(key)):
                raise RehearsalError(f"sensitive evidence key is forbidden: {path}.{key}")
            assert_no_sensitive_output(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            assert_no_sensitive_output(item, f"{path}[{index}]")
    elif isinstance(value, str) and SENSITIVE_VALUE.search(value):
        raise RehearsalError(f"sensitive evidence value is forbidden: {path}")


def atomic_write_evidence(path: Path, payload: dict) -> str:
    assert_no_sensitive_output(payload)
    if not REHEARSAL_ID.fullmatch(str(payload.get("rehearsal_set_id") or "")):
        raise RehearsalError("rehearsal evidence identifier is invalid")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise RehearsalError("rehearsal evidence directory must not be a symlink")
    previous_umask = os.umask(0o077)
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=".incomplete-", dir=path.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o600)
        os.replace(temporary, path)
        path.chmod(0o600)
    finally:
        os.umask(previous_umask)
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise RehearsalError("rehearsal evidence mode must be 0600")
    return _sha256(path)


def _print_result(name: str, result: dict) -> None:
    print(name + "=" + json.dumps(result, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("freeze", "validate-source", "validate-isolation", "plan", "write-evidence"),
    )
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--candidate-manifest", type=Path)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    contract = load_contract(args.contract)
    if args.action == "freeze":
        if args.candidate_manifest is None:
            raise CandidateNotFrozen("approved RC6 candidate manifest is required")
        result = freeze_candidate(contract, args.candidate_manifest, args.repository)
    else:
        if args.input is None:
            raise RehearsalError("--input is required")
        payload = _load_json(args.input, "rehearsal input")
        if args.action == "validate-source":
            result = validate_source_artifacts(contract, payload)
        elif args.action == "validate-isolation":
            result = validate_isolation(contract, payload)
        elif args.action == "plan":
            result = build_migration_plan(contract, payload)
        else:
            if args.output is None:
                raise RehearsalError("--output is required")
            digest = atomic_write_evidence(args.output, payload)
            result = {"evidence_path": str(args.output), "evidence_sha256": digest}
    _print_result("RC6_DAILY_CLONE_REHEARSAL", result)


if __name__ == "__main__":
    try:
        main()
    except CandidateNotFrozen as exc:
        raise SystemExit(f"RC6_CANDIDATE_NOT_FROZEN={exc}") from exc
    except RehearsalError as exc:
        raise SystemExit(f"RC6_DAILY_CLONE_REHEARSAL_ERROR={exc}") from exc
