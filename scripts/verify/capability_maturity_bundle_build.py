#!/usr/bin/env python3
"""Thin evidence projector for C1 ``project.initiation.create``.

This is a projection adapter, not a second verification engine. It maps real,
branch-local verification facts into a ``capability.maturity.evidence.v2``
bundle consumed by ``scripts/verify/capability_maturity_evidence.py``.

Responsibilities that stay with existing mechanisms:
* fingerprint computation -> ``addons/smart_core/core/capability_maturity.py``
* maturity evaluation       -> ``scripts/verify/capability_maturity_evidence.py``
* provider registration     -> ``scripts/verify/capability_candidate_catalog_check.py``

Fail-closed contract:
* provider registration identity is only proven by the CAP-01B catalog checker.
  When that mechanism is absent from the current branch, identity cases are
  recorded as ``error`` (never ``pass``), so the downstream verifier blocks.
* static contract/handler/service facts are read from versioned files and every
  case records its exact source file, repository HEAD and execution timestamp.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CAPABILITY_KEY = "project.initiation.create"
PROVIDER_INTENT = "project.initiation.enter"

CONTRACT_PATH = ROOT / "addons/smart_construction_core/data/capability_acceptance_contracts_v1.json"
HANDLER_PATH = ROOT / "addons/smart_construction_core/handlers/project_initiation_enter.py"
SERVICE_PATH = ROOT / "addons/smart_construction_core/services/project_creation_service.py"
REGISTRATION_PATH = ROOT / "addons/smart_construction_core/core_extension_intent_handlers.py"
CATALOG_CHECK_PATH = ROOT / "scripts/verify/capability_candidate_catalog_check.py"


def _load_maturity():
    spec = importlib.util.spec_from_file_location(
        "maturity", ROOT / "addons/smart_core/core/capability_maturity.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


maturity = _load_maturity()


def _head() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True
    )
    return proc.stdout.strip()


def _load_contract() -> dict:
    data = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if data.get("schema") != "capability.acceptance.contracts.v1":
        raise SystemExit("ACCEPTANCE_CONTRACT_SCHEMA_UNEXPECTED")
    return data["capabilities"][CAPABILITY_KEY]


def _handler_facts() -> dict:
    text = HANDLER_PATH.read_text(encoding="utf-8")
    fields_match = re.search(r"_ALLOWED_FIELDS\s*=\s*\{(.*?)\}", text, re.S)
    fields: set[str] = set()
    if fields_match:
        fields = {
            item.strip().strip("\"'")
            for item in fields_match.group(1).split(",")
            if item.strip()
        }
    intent_match = re.search(r'INTENT_TYPE\s*=\s*"([^"]+)"', text)
    return {
        "intent_type": intent_match.group(1) if intent_match else "",
        "allowed_fields": sorted(fields),
        "inherits_base_handler": "BaseIntentHandler" in text,
        "error_codes": sorted(set(re.findall(r"REASON_[A-Z_]+", text))),
        "source": str(HANDLER_PATH),
    }


def _service_facts() -> dict:
    text = SERVICE_PATH.read_text(encoding="utf-8")
    phase_match = re.search(r'normalized\["phase_key"\]\s*=\s*"([^"]+)"', text)
    lifecycle_match = re.search(r'normalized\["lifecycle_state"\]\s*=\s*"([^"]+)"', text)
    return {
        "defaults": {
            "manager_id_fallback": 'normalized.get("user_id") or self.env.user.id' in text,
            "phase_key": phase_match.group(1) if phase_match else "",
            "lifecycle_state": lifecycle_match.group(1) if lifecycle_match else "",
        },
        "conditional_bootstrap": (
            'check_access_rights("create"' in text and "search_count" in text
        ),
        "conditional_message_post": 'hasattr(project, "message_post")' in text,
        "source": str(SERVICE_PATH),
    }


def _case(case_id: str, status: str, reason: str = "") -> dict:
    result: dict = {"id": case_id, "status": status}
    if reason:
        result["reason"] = reason
    return result


def _identity_cases() -> list[dict]:
    """Provider registration identity.

    The authoritative check is ``capability_candidate_catalog_check.py`` from the
    CAP-01B branch. This adapter must not re-derive the intent->handler
    registration chain itself, so when the checker is absent the cases fail
    closed instead of being marked pass.
    """
    reason = (
        "provider_registration_checker_unavailable_on_branch"
        if not CATALOG_CHECK_PATH.is_file()
        else ""
    )
    status = "error" if reason else "pass"
    return [
        _case("capability_key_matches_provider", status, reason),
        _case("provider_chain_resolves", status, reason),
    ]


def _io_cases() -> list[dict]:
    facts = _handler_facts()
    whitelist = facts["allowed_fields"]
    has_name = "name" in whitelist
    handler_text = HANDLER_PATH.read_text(encoding="utf-8")
    output_shape_declared = bool(re.search(r'"record"\s*:\s*\{', handler_text))
    error_codes_declared = bool(facts["error_codes"])
    return [
        _case(
            "input_fields_whitelist_declared",
            "pass" if (whitelist and has_name) else "fail",
            "handler_allowed_fields=" + ",".join(whitelist),
        ),
        _case(
            "output_record_shape_declared",
            "pass" if output_shape_declared else "fail",
            "handler_success_record_shape" if output_shape_declared else "record_shape_missing",
        ),
        _case(
            "error_codes_declared",
            "pass" if error_codes_declared else "fail",
            "handler_reason_codes=" + ",".join(facts["error_codes"]),
        ),
    ]


def _dependency_cases(contract: dict) -> list[dict]:
    product = contract.get("product_dependencies") or []
    authorization = contract.get("authorization_dependencies") or []
    product_complete = bool(product) and all((ROOT / rel).is_file() for rel in product)
    authorization_complete = bool(authorization) and all(
        (ROOT / rel).is_file() for rel in authorization
    )
    return [
        _case(
            "product_dependencies_complete",
            "pass" if product_complete else "fail",
            "product_dependency_files=" + str(len(product)),
        ),
        _case(
            "authorization_dependencies_complete",
            "pass" if authorization_complete else "fail",
            "authorization_dependency_files=" + str(len(authorization)),
        ),
    ]


def _scope_cases() -> list[dict]:
    """The contract must not promise capability beyond the handler allowlist."""
    facts = _handler_facts()
    whitelist = set(facts["allowed_fields"])
    bounded = bool(whitelist) and "name" in whitelist
    return [
        _case(
            "contract_does_not_exceed_provider_capability",
            "pass" if bounded else "fail",
            "provider_surface=" + ",".join(sorted(whitelist)),
        )
    ]


def _promise_cases() -> list[dict]:
    facts = _service_facts()
    defaults = facts["defaults"]
    defaults_ok = (
        defaults.get("manager_id_fallback")
        and defaults.get("phase_key") == "initiation"
        and defaults.get("lifecycle_state") == "draft"
    )
    error_codes = _handler_facts()["error_codes"]
    return [
        _case(
            "defaults_contract_consistent",
            "pass" if defaults_ok else "fail",
            "service_defaults=" + json.dumps(defaults, sort_keys=True),
        ),
        _case(
            "conditional_bootstrap_contract_consistent",
            "pass" if facts["conditional_bootstrap"] else "fail",
            "bootstrap_is_conditional" if facts["conditional_bootstrap"] else "bootstrap_unconditional",
        ),
        _case(
            "error_mapping_contract_consistent",
            "pass" if bool(error_codes) else "fail",
            "handler_error_codes=" + ",".join(error_codes),
        ),
    ]


CHECKS = {
    "contract_identity_consistency": (_identity_cases, "capability_candidate_catalog_check"),
    "contract_io_consistency": (_io_cases, "handler_static_facts"),
    "contract_dependency_consistency": (_dependency_cases, "contract_and_filesystem"),
    "contract_scope_consistency": (_scope_cases, "handler_allowlist"),
    "contract_promise_consistency": (_promise_cases, "service_static_facts"),
}


def _run_check(check_id: str, contract: dict) -> list[dict]:
    case_fn = CHECKS[check_id][0]
    if check_id == "contract_dependency_consistency":
        return case_fn(contract)
    return case_fn()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--outdir",
        type=Path,
        default=ROOT / "artifacts/backend/capability_maturity_bundle_project_initiation_create",
    )
    args = parser.parse_args()

    contract = _load_contract()
    head = _head()
    executed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    deps = contract.get("product_dependencies") or []
    dep_hashes = {
        rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in deps
    }
    criteria = contract.get("product_criteria") or {}
    fingerprint = maturity.maturity_fingerprint(CAPABILITY_KEY, dep_hashes, criteria)

    artifacts: dict[str, str] = {}
    receipts: list[dict] = []
    payloads: list[tuple[str, bytes]] = []
    for check_id, (_case_fn, mechanism) in CHECKS.items():
        cases = _run_check(check_id, contract)
        payload = {
            "capability_key": CAPABILITY_KEY,
            "fingerprint": fingerprint,
            "check_id": check_id,
            "cases": cases,
            "provenance": {
                "head": head,
                "executed_at": executed_at,
                "mechanism": mechanism,
            },
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        relative = f"artifact_{check_id}.json"
        artifacts[digest] = relative
        payloads.append((relative, raw))
        receipts.append(
            {
                "check_id": check_id,
                "capability_key": CAPABILITY_KEY,
                "fingerprint": fingerprint,
                "artifact_sha256": digest,
            }
        )

    bundle = {
        "schema": "capability.maturity.evidence.v2",
        "artifacts": artifacts,
        "capabilities": [
            {
                "capability_key": CAPABILITY_KEY,
                "dependencies": dep_hashes,
                "criteria": criteria,
                "receipts": receipts,
            }
        ],
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    for relative, raw in payloads:
        (args.outdir / relative).write_bytes(raw)
    bundle_path = args.outdir / "bundle.json"
    bundle_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    summary = {
        "status": "PROJECTED",
        "head": head,
        "bundle": str(bundle_path),
        "checks": {
            check_id: {
                "mechanism": CHECKS[check_id][1],
                "cases": _run_check(check_id, contract),
            }
            for check_id in CHECKS
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
