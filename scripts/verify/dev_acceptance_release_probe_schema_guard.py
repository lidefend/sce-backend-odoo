#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import importlib.util


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_LIFECYCLE_PATH = ROOT / "addons/smart_core/core/contract_lifecycle.py"
REPORT_JSON = ROOT / os.getenv(
    "ACCEPTANCE_PROBE_OUTPUT",
    "artifacts/backend/dev_acceptance_release_probe.json",
)


def _sha256_hex(value: object) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def _sha40_hex(value: object) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{40}", value))


def _semantic_sha256(snapshot: dict) -> str:
    """Recompute the approved semantic digest with the producer protocol itself."""
    spec = importlib.util.spec_from_file_location("acceptance_guard_contract_lifecycle", CONTRACT_LIFECYCLE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.payload_sha256(module.contract_semantic_payload(snapshot))


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_receipt_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _check_persisted_custody(contract: dict, errors: list[str]) -> None:
    """Prove the exact live bytes are persisted and re-derivable without the runtime.

    The receipt only carries the parsed contract; this guard re-reads the persisted
    raw response, recomputes its byte digest, and re-derives the declared semantic
    digest and lifecycle declaration from those bytes. A re-serialized snapshot can
    never satisfy this, so custody is reproducible offline instead of asserted.
    """
    custody = contract.get("custody")
    if not isinstance(custody, dict):
        errors.append("contract.custody must be object when contract passes")
        return
    declared_sha = custody.get("response_sha256")
    if not _sha256_hex(declared_sha):
        errors.append("contract.custody.response_sha256 must be sha256 when contract passes")
        return
    response_bytes = custody.get("response_bytes")
    if not isinstance(response_bytes, int) or isinstance(response_bytes, bool) or response_bytes <= 0:
        errors.append("contract.custody.response_bytes must be positive int when contract passes")
        return
    path_value = custody.get("response_path")
    if not isinstance(path_value, str) or not path_value:
        errors.append("contract.custody.response_path must be non-empty string when contract passes")
        return
    path = _resolve_receipt_path(path_value)
    if not path.is_file():
        errors.append("contract.custody.response_path must resolve to an existing file when contract passes")
        return
    raw = path.read_bytes()
    if len(raw) != response_bytes:
        errors.append("contract.custody.response_bytes must equal the persisted byte length")
    if hashlib.sha256(raw).hexdigest() != declared_sha:
        errors.append("contract.custody.response_sha256 must equal the persisted byte digest")
        return
    try:
        envelope = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        errors.append("contract.custody.response_path must decode as utf-8 json")
        return
    data = envelope.get("data") if isinstance(envelope, dict) else None
    if not isinstance(data, dict):
        errors.append("contract.custody.response_path envelope must carry a data object")
        return
    if data != contract.get("snapshot"):
        errors.append("contract.custody.response_path data must equal the embedded snapshot")
        return
    approved = contract.get("approved_semantic_sha256")
    if _sha256_hex(approved) and _semantic_sha256(data) != approved:
        errors.append("contract.custody.response_path semantics must match approved_semantic_sha256")
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    lifecycle = meta.get("lifecycle") if isinstance(meta.get("lifecycle"), dict) else {}
    if not lifecycle:
        errors.append("contract.custody.response_path data must carry meta.lifecycle")
        return
    definition = lifecycle.get("definition") if isinstance(lifecycle.get("definition"), dict) else {}
    integrity = lifecycle.get("integrity") if isinstance(lifecycle.get("integrity"), dict) else {}
    schema = contract.get("schema_asset") if isinstance(contract.get("schema_asset"), dict) else {}
    if schema.get("sha256") and definition.get("schemaSha256") != schema.get("sha256"):
        errors.append("contract.custody.response_path definition.schemaSha256 must equal schema_asset.sha256")
    if integrity.get("contractSha256") != approved:
        errors.append("contract.custody.response_path integrity.contractSha256 must equal approved_semantic_sha256")


def _string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _nav_action_mismatch_list(value: object) -> bool:
    if not isinstance(value, list):
        return False
    for item in value:
        if not isinstance(item, dict):
            return False
        if not isinstance(item.get("path"), str) or not item.get("path"):
            return False
        if not isinstance(item.get("expected_action_id"), int):
            return False
        actual = item.get("actual_action_id")
        if actual is not None and not isinstance(actual, int):
            return False
    return True


def _check_status_block(prefix: str, value: object, errors: list[str]) -> dict:
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be object")
        return {}
    status = value.get("status")
    enabled = value.get("enabled")
    if enabled is not False and status not in {"PASS", "FAIL"}:
        errors.append(f"{prefix}.status must be PASS or FAIL when enabled")
    block_errors = value.get("errors")
    if block_errors is not None and not _string_list(block_errors):
        errors.append(f"{prefix}.errors must be string list")
        block_errors = []
    if status == "PASS" and block_errors:
        errors.append(f"{prefix}.status=PASS must not contain errors")
    if status == "FAIL" and not block_errors:
        errors.append(f"{prefix}.status=FAIL must contain errors")
    return value


def _check_backup(value: object, errors: list[str]) -> str:
    backup = _check_status_block("backup", value, errors)
    if not backup:
        return "FAIL"
    enabled = backup.get("enabled")
    if not isinstance(enabled, bool):
        errors.append("backup.enabled must be bool")
    if enabled is False:
        return "PASS"
    if not isinstance(backup.get("dir"), str) or not backup.get("dir"):
        errors.append("backup.dir must be non-empty string when enabled")
    if not isinstance(backup.get("checks"), dict):
        errors.append("backup.checks must be object when enabled")
    return str(backup.get("status") or "FAIL")


def _check_frontend(value: object, errors: list[str]) -> str:
    frontend = _check_status_block("frontend", value, errors)
    if not frontend:
        return "FAIL"
    if not isinstance(frontend.get("base_url"), str) or not frontend.get("base_url"):
        errors.append("frontend.base_url must be non-empty string")
    checks = frontend.get("checks")
    if not isinstance(checks, dict):
        errors.append("frontend.checks must be object")
        return str(frontend.get("status") or "FAIL")
    for key in ("root_status", "asset_status", "intent_options_status", "intent_get_status"):
        if key in checks and not isinstance(checks.get(key), int):
            errors.append(f"frontend.checks.{key} must be int")
    for key in (
        "asset_has_db",
        "asset_has_app_env",
        "asset_has_forbidden_db_token",
        "asset_forbidden_db_is_default",
    ):
        if key in checks and not isinstance(checks.get(key), bool):
            errors.append(f"frontend.checks.{key} must be bool")
    asset_path = checks.get("asset_path")
    if frontend.get("status") == "PASS" and (not isinstance(asset_path, str) or not asset_path):
        errors.append("frontend.checks.asset_path must be non-empty string when frontend passes")
    if frontend.get("status") == "PASS":
        expected = {
            "root_status": 200,
            "asset_status": 200,
            "intent_options_status": 204,
            "intent_get_status": 405,
        }
        for key, expected_value in expected.items():
            if checks.get(key) != expected_value:
                errors.append(f"frontend.checks.{key} must be {expected_value} when frontend passes")
    return str(frontend.get("status") or "FAIL")


def _check_login(value: object, errors: list[str]) -> str:
    login = _check_status_block("login", value, errors)
    if not login:
        return "FAIL"
    enabled = login.get("enabled")
    if not isinstance(enabled, bool):
        errors.append("login.enabled must be bool")
    if enabled is False:
        return "PASS"
    if not isinstance(login.get("login"), str) or not login.get("login"):
        errors.append("login.login must be non-empty string when enabled")
    checks = login.get("checks")
    if not isinstance(checks, dict):
        errors.append("login.checks must be object when enabled")
        return str(login.get("status") or "FAIL")
    for key in ("auth_status", "system_init_status"):
        if not isinstance(checks.get(key), int):
            errors.append(f"login.checks.{key} must be int")
    if not isinstance(checks.get("system_init_ok"), bool):
        errors.append("login.checks.system_init_ok must be bool")
    if checks.get("auth_uid") is not None and not isinstance(checks.get("auth_uid"), int):
        errors.append("login.checks.auth_uid must be int when present")
    for key in ("nav_count", "nav_node_count", "nav_action_count", "nav_leaf_count"):
        if checks.get(key) is not None and not isinstance(checks.get(key), int):
            errors.append(f"login.checks.{key} must be int when present")
    if checks.get("role_code") is not None and not isinstance(checks.get("role_code"), str):
        errors.append("login.checks.role_code must be string when present")
    expected_role = checks.get("role_code_expected")
    if expected_role is not None:
        if not isinstance(expected_role, str) or not expected_role:
            errors.append("login.checks.role_code_expected must be a non-empty string when present")
        elif checks.get("role_code") != expected_role:
            errors.append("login.checks.role_code must equal the declared principal role_code_expected")
    for key in ("nav_forbidden_label_hits", "nav_required_path_misses"):
        if checks.get(key) is not None and not _string_list(checks.get(key)):
            errors.append(f"login.checks.{key} must be string list when present")
    if checks.get("nav_required_action_mismatches") is not None and not _nav_action_mismatch_list(
        checks.get("nav_required_action_mismatches")
    ):
        errors.append("login.checks.nav_required_action_mismatches must be action mismatch list when present")
    if checks.get("nav_paths_sample") is not None and not _string_list(checks.get("nav_paths_sample")):
        errors.append("login.checks.nav_paths_sample must be string list when present")
    if login.get("status") == "PASS":
        if checks.get("auth_status") != 200:
            errors.append("login.checks.auth_status must be 200 when login passes")
        if checks.get("system_init_status") != 200:
            errors.append("login.checks.system_init_status must be 200 when login passes")
        if checks.get("system_init_ok") is not True:
            errors.append("login.checks.system_init_ok must be true when login passes")
        if not checks.get("role_code"):
            errors.append("login.checks.role_code must be non-empty when login passes")
        if not isinstance(checks.get("nav_node_count"), int) or checks.get("nav_node_count") <= 0:
            errors.append("login.checks.nav_node_count must be positive when login passes")
        if not isinstance(checks.get("nav_action_count"), int) or checks.get("nav_action_count") <= 0:
            errors.append("login.checks.nav_action_count must be positive when login passes")
        if checks.get("nav_forbidden_label_hits"):
            errors.append("login.checks.nav_forbidden_label_hits must be empty when login passes")
        if checks.get("nav_required_path_misses"):
            errors.append("login.checks.nav_required_path_misses must be empty when login passes")
        if checks.get("nav_required_action_mismatches"):
            errors.append("login.checks.nav_required_action_mismatches must be empty when login passes")
    return str(login.get("status") or "FAIL")


def _check_contract(value: object, errors: list[str]) -> str:
    """Validate the exact-instance receipt and re-derive its approved digest."""
    contract = _check_status_block("contract", value, errors)
    if not contract:
        return "FAIL"
    enabled = contract.get("enabled")
    if not isinstance(enabled, bool):
        errors.append("contract.enabled must be bool")
        return "FAIL"
    if enabled is False:
        return "NOT_RUN"
    status = contract.get("status")
    if status not in {"PASS", "FAIL", "NOT_RUN"}:
        errors.append("contract.status must be PASS, FAIL or NOT_RUN when enabled")
        return "FAIL"
    required = contract.get("required_checks")
    if not isinstance(required, list) or not all(isinstance(item, str) and item for item in required):
        errors.append("contract.required_checks must be a string list when enabled")
        required = []
    checks = contract.get("checks")
    if not isinstance(checks, dict):
        errors.append("contract.checks must be object when enabled")
        checks = {}
    unknown = [name for name in checks if name not in required]
    if unknown:
        errors.append(f"contract.checks must only contain declared required checks {unknown}")
    for name, result in checks.items():
        if not isinstance(result, bool):
            errors.append(f"contract.checks.{name} must be bool")
    # An absent key means "not evaluated"; the claimed executed/not_run lists must
    # agree with the evaluated set instead of pre-filling a default verdict.
    if contract.get("executed_checks") is not None and contract.get("executed_checks") != [name for name in required if name in checks]:
        errors.append("contract.executed_checks must list exactly the evaluated required checks")
    if contract.get("not_run_checks") is not None and contract.get("not_run_checks") != [name for name in required if name not in checks]:
        errors.append("contract.not_run_checks must list exactly the unevaluated required checks")
    if status == "FAIL" and not required and contract.get("reason") == "contract_required_but_undeclared":
        pass
    elif not required:
        errors.append("contract.required_checks must be non-empty when the contract was evaluated")
    executed = [name for name in required if name in checks]
    if status == "PASS":
        if not executed:
            errors.append("contract.status=PASS requires at least one executed required check")
        for name in required:
            if checks.get(name) is not True:
                errors.append(f"contract.checks.{name} must be true when contract passes")
        snapshot = contract.get("snapshot")
        if not isinstance(snapshot, dict) or not snapshot:
            errors.append("contract.snapshot must be non-empty object when contract passes")
        approved = contract.get("approved_semantic_sha256")
        if not _sha256_hex(approved):
            errors.append("contract.approved_semantic_sha256 must be sha256 when contract passes")
        elif isinstance(snapshot, dict) and snapshot:
            if _semantic_sha256(snapshot) != approved:
                errors.append("contract.approved_semantic_sha256 must match the embedded snapshot semantics")
        if contract.get("recomputed_semantic_sha256") != approved:
            errors.append("contract.recomputed_semantic_sha256 must equal approved_semantic_sha256")
        identity = contract.get("identity")
        if not isinstance(identity, dict) or not _sha40_hex(identity.get("served_sha")):
            errors.append("contract.identity.served_sha must be full commit SHA when contract passes")
        elif identity.get("served_sha") != identity.get("expected_sha"):
            errors.append("contract.identity.served_sha must equal expected_sha")
        request = contract.get("request")
        if not isinstance(request, dict) or not isinstance(request.get("params"), dict) or not request.get("params"):
            errors.append("contract.request.params must be non-empty object when contract passes")
        elif not _sha256_hex(request.get("fingerprint_sha256")):
            errors.append("contract.request.fingerprint_sha256 must be sha256 when contract passes")
        # The sealed digest depends on the localized projection, so a passing
        # receipt must record the request context that reproduced it; a missing
        # context would make the recorded request unreplayable.
        request_context = request.get("context") if isinstance(request, dict) else None
        if not isinstance(request_context, dict) or not all(
            isinstance(request_context.get(key), str) and request_context.get(key) for key in ("lang", "tz")
        ):
            errors.append("contract.request.context must record lang and tz when contract passes")
        resolution = contract.get("resolution")
        if not isinstance(resolution, dict) or not isinstance(resolution.get("record_id"), int) or resolution.get("record_id") <= 0:
            errors.append("contract.resolution.record_id must be positive int when contract passes")
        elif not isinstance(resolution.get("stable_identifier"), str) or not resolution.get("stable_identifier"):
            errors.append("contract.resolution.stable_identifier must be governed fixture id")
        custody = contract.get("custody")
        if not isinstance(custody, dict) or not _sha256_hex(custody.get("response_sha256")):
            errors.append("contract.custody.response_sha256 must be sha256 when contract passes")
        else:
            _check_persisted_custody(contract, errors)
        schema = contract.get("schema_asset")
        if not isinstance(schema, dict) or not _sha256_hex(schema.get("sha256")):
            errors.append("contract.schema_asset.sha256 must be sha256 when contract passes")
        elif schema.get("sha256") != schema.get("declared_schema_sha256"):
            errors.append("contract.schema_asset.sha256 must equal declared_schema_sha256")
    return str(status)


def _check_runtime_identity(value: object, errors: list[str]) -> str:
    identity = _check_status_block("runtime_identity", value, errors)
    if not identity:
        return "FAIL"
    expected = identity.get("expected_sha")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{40}", expected):
        errors.append("runtime_identity.expected_sha must be full commit SHA")
    if identity.get("status") == "PASS":
        if identity.get("http_status") != 200:
            errors.append("runtime_identity.http_status must be 200 when identity passes")
        if identity.get("served_sha") != expected:
            errors.append("runtime_identity.served_sha must match expected_sha")
    return str(identity.get("status") or "FAIL")


def main() -> int:
    payload = _load_json(REPORT_JSON)
    errors: list[str] = []
    if not payload:
        errors.append(f"missing or invalid json: {REPORT_JSON.relative_to(ROOT).as_posix()}")
    else:
        if payload.get("mode") != "dev_acceptance_release_probe":
            errors.append("mode must be dev_acceptance_release_probe")
        if payload.get("status") not in {"PASS", "FAIL"}:
            errors.append("status must be PASS or FAIL")
        for key in ("db_name", "base_url", "app_env"):
            if not isinstance(payload.get(key), str) or not payload.get(key):
                errors.append(f"{key} must be non-empty string")
        statuses = [
            _check_backup(payload.get("backup"), errors),
            _check_runtime_identity(payload.get("runtime_identity"), errors),
            _check_frontend(payload.get("frontend"), errors),
            _check_login(payload.get("login"), errors),
        ]
        contract_status = _check_contract(payload.get("contract"), errors) if "contract" in payload else None
        if contract_status is not None and contract_status != "NOT_RUN":
            statuses.append(contract_status)
        expected_status = "PASS" if all(status == "PASS" for status in statuses) else "FAIL"
        if payload.get("status") in {"PASS", "FAIL"} and payload.get("status") != expected_status:
            errors.append("status must match backup/runtime_identity/frontend/login/contract aggregate status")

    if errors:
        print("[dev_acceptance_release_probe_schema_guard] FAIL")
        for error in errors:
            print(error)
        return 2
    print("[dev_acceptance_release_probe_schema_guard] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
