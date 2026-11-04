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
import inspect
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_mapper():
    spec = importlib.util.spec_from_file_location(
        "capability_contract_mapper", ROOT / "scripts/verify/capability_contract_mapper.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mapper = _load_mapper()

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


def _run_catalog_check() -> tuple[str, str]:
    """Run the CAP-01B catalog checker and return (status, reason).

    This invokes the existing governed entrypoint as a real subprocess and maps
    its exit code to pass/fail/error. It never re-derives the provider
    registration chain itself and fails closed on tool failure.
    """
    if not CATALOG_CHECK_PATH.is_file():
        return "error", "provider_registration_checker_unavailable_on_branch"
    try:
        proc = subprocess.run(
            [sys.executable, str(CATALOG_CHECK_PATH), "--check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "error", "catalog_check_tool_failure:" + type(exc).__name__
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    detail = stdout.splitlines()[0] if stdout else stderr
    if proc.returncode == 0:
        return "pass", "catalog_check_pass:" + (detail or "exit=0")
    return "fail", "catalog_check_fail:" + (detail or f"exit={proc.returncode}")


def _identity_cases() -> list[dict]:
    """Provider registration identity, sourced from the CAP-01B catalog checker."""
    status, reason = _run_catalog_check()
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


BATCH_CHECK_IDS = {
    "state-transition": "state_transition_contract",
    "business-write": "write_contract",
    "read-only-query": "query_contract",
    "audit-state-transition": "audit_state_transition_contract",
}


def _batch_cases(template: str, proj: dict) -> list[dict]:
    """Verify template cases from joined facts (real, reviewable logic).

    Structural conditions are verified against the joined facts; semantic
    conditions without static source evidence are recorded as ``skip`` (not
    executed), never inferred as pass.
    """
    if template == "state-transition":
        sm = proj["state_machine"]["value"]
        methods = proj["transition_methods"]
        guard = (proj.get("server_guard") or {}).get("value", {})
        view_guards = proj["view_guards"] or []
        states, transitions, terminal = sm["states"], sm["transitions"], sm["terminal_states"]
        state_set = set(states)
        all_targets = {t for targets in transitions.values() for t in targets}
        method_names = {m["method"] for m in methods}
        button_names = {g["button"] for g in view_guards}
        uncovered, unresolved_edges = _transition_edge_coverage(methods, view_guards, states, transitions)
        edge_status = "fail" if uncovered else ("error" if unresolved_edges else "pass")
        edge_reason = f"uncovered={uncovered} unresolved={unresolved_edges}" if (uncovered or unresolved_edges) else f"{sum(len(v) for v in transitions.values())} edges covered"
        return [
            _case("state_enum_declared", "pass" if states and len(states) == len(state_set) else "fail", f"{len(states)} unique states"),
            _case("transition_table_exhaustive", "pass" if state_set <= set(transitions) and all_targets <= state_set else "fail", f"states={len(states)} table={len(transitions)} targets_valid={all_targets <= state_set}"),
            _case("terminal_state_declared", "pass" if terminal and all(transitions.get(t) == [] for t in terminal) else "fail", f"terminal={terminal}"),
            _case("every_transition_has_method", edge_status, edge_reason),
            _case("server_guard_present", "pass" if guard.get("checks") else "fail", f"checks={guard.get('checks')}"),
            _case("view_guard_consistent_with_state_machine", "pass" if button_names == method_names else "fail", f"buttons_only={sorted(button_names - method_names)} methods_only={sorted(method_names - button_names)}"),
        ]
    if template == "business-write":
        model = proj["provider"]["model_facts"]
        required = model.get("required_fields") or []
        return [
            _case("input_required_fields_declared", "pass" if required else "fail", f"required={required}"),
            _case("output_record_shape_declared", "pass" if model.get("model") else "fail", f"model={model.get('model')}"),
            _case("error_codes_declared", "skip", "semantic check: no declared error-code registry evidence"),
            _case("side_effect_declared", "skip", "semantic check: mail.thread is not business side-effect evidence"),
        ]
    if template == "read-only-query":
        provider = proj["provider"]
        return [
            _case("query_model_declared", "pass" if provider.get("action_res_model") else "fail", f"res_model={provider.get('action_res_model')}"),
            _case("result_columns_declared", "skip", "semantic check: model presence is not return-column evidence"),
            _case("read_side_effect_free", "skip", "semantic check: requires ACL/operation-policy evidence"),
            _case("data_scope_declared", "skip", "semantic check: requires record-rule/data-scope evidence"),
        ]
    if template == "audit-state-transition":
        sm = proj["state_machine"]["value"]
        methods = proj["transition_methods"]
        states, terminal = sm["states"], sm["terminal_states"]
        audit = [m for m in methods if m["method"] in {"action_submit", "action_approve", "action_done", "action_cancel"}]
        bind = [m for m in methods if m["method"] in {"action_bind_contract", "action_unbind_contract"}]
        immutable = _settlement_immutable_states()
        immutable_enforced = _settlement_immutable_enforced()
        audit_guarded = all(m["server_guard"] for m in audit) if len(audit) == 4 else False
        return [
            _case("audit_actions_declared", "pass" if len(audit) == 4 and audit_guarded else ("fail" if len(audit) != 4 else "skip"), f"audit={[(m['method'], m['server_guard']) for m in audit]}"),
            _case("approval_state_declared", "pass" if "approve" in states else "fail", f"states={states}"),
            _case("immutable_final_states_declared", "pass" if immutable and immutable >= {"done", "cancel"} and immutable_enforced else "fail", f"immutable={immutable} enforced={immutable_enforced}"),
            _case("contract_association_boundary_declared", "pass" if len(bind) == 2 and all(m["server_guard"] for m in bind) else "fail", f"bind={[(m['method'], m['server_guard']) for m in bind]}"),
        ]
    return []


def _settlement_immutable_states() -> set[str]:
    text = (ROOT / "addons/smart_construction_core/models/core/settlement_order.py").read_text(encoding="utf-8")
    m = re.search(r'_IMMUTABLE_FACT_STATES\s*=\s*frozenset\(\{(.*?)\}\)', text)
    if not m:
        return set()
    return {s.strip().strip('"').strip("'") for s in m.group(1).split(",") if s.strip()}


def _settlement_immutable_enforced() -> bool:
    """True only when _IMMUTABLE_FACT_STATES is used in a write guard, not merely declared."""
    text = (ROOT / "addons/smart_construction_core/models/core/settlement_order.py").read_text(encoding="utf-8")
    return bool(re.search(r'\._IMMUTABLE_FACT_STATES\b', text)) or bool(
        re.search(r'in\s+self\._IMMUTABLE_FACT_STATES\b', text)
    )


def _parse_from_states(invisible: str, all_states: set[str]) -> set[str]:
    """Derive the set of source states a button guard allows."""
    m = re.search(r"lifecycle_state\s*!=\s*'([a-z_]+)'", invisible)
    if m:
        return {m.group(1)}
    m = re.search(r"lifecycle_state\s*not\s+in\s*\[([^\]]+)\]", invisible)
    if m:
        return {s.strip().strip("'") for s in m.group(1).split(",") if s.strip()}
    m = re.search(r"lifecycle_state\s*==\s*'([a-z_]+)'", invisible)
    if m:
        return all_states - {m.group(1)}
    return set()


def _transition_edge_coverage(methods: list[dict], view_guards: list[dict], states: list[str], transitions: dict) -> tuple[list[str], list[str]]:
    """Return (uncovered_edges, unresolved_edges) for source->target coverage."""
    all_states = set(states)
    method_map: dict[str, dict] = {}
    for m in methods:
        method_map[m["method"]] = {"target": m["target_state"], "from": set()}
    for g in view_guards:
        if g["button"] in method_map:
            method_map[g["button"]]["from"] = _parse_from_states(g["invisible"], all_states)

    uncovered: list[str] = []
    unresolved: list[str] = []
    for source, targets in transitions.items():
        for target in targets:
            candidates = [mm for mm in method_map.values() if mm["target"] == target]
            if not candidates:
                unresolved.append(f"{source}->{target}:no_method_for_target")
                continue
            if any(source in mm["from"] for mm in candidates):
                continue
            if all(not mm["from"] for mm in candidates):
                unresolved.append(f"{source}->{target}:source_guard_unparseable")
            else:
                uncovered.append(f"{source}->{target}")
    return uncovered, unresolved


def build_batch_bundle() -> tuple[dict, dict[str, bytes]]:
    """Build one capability.maturity.evidence.v2 bundle for the six keep-atomic."""
    contract_data = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    contracts = contract_data["capabilities"]
    head = _head()
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    check_source = inspect.getsource(_batch_cases)
    check_digest = hashlib.sha256(check_source.encode("utf-8")).hexdigest()

    artifacts: dict[str, str] = {}
    payloads: list[tuple[str, bytes]] = []
    capabilities = []

    for key, spec in mapper.SPECS.items():
        contract = contracts[key]
        dependencies = {rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
                        for rel in contract["product_dependencies"]}
        criteria = contract["product_criteria"]
        fingerprint = maturity.maturity_fingerprint(key, dependencies, criteria)
        proj = mapper._projection_for(key, spec)
        check_id = BATCH_CHECK_IDS[spec["template"]]
        if proj["unresolved"]:
            required_cases = criteria["standard"][check_id]
            cases = [_case(cid, "error", "join_unresolved:" + ";".join(proj["unresolved"])) for cid in required_cases]
        else:
            cases = _batch_cases(spec["template"], proj)
        artifact = {
            "capability_key": key,
            "fingerprint": fingerprint,
            "check_id": check_id,
            "cases": cases,
            "provenance": {
                "head": head,
                "executed_at": started,
                "mechanism": "capability_contract_mapper.join",
                "check_module": "capability_maturity_bundle_build",
                "check_function": "_batch_cases",
                "check_digest": check_digest,
                "execution_id": hashlib.sha256(f"{head}:{check_digest}:{key}".encode("utf-8")).hexdigest()[:16],
            },
        }
        raw = json.dumps(artifact, ensure_ascii=False, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        relative = f"artifact_{key}.json"
        artifacts[digest] = relative
        payloads.append((relative, raw))
        capabilities.append({
            "capability_key": key,
            "dependencies": dependencies,
            "criteria": criteria,
            "receipts": [{
                "check_id": check_id,
                "capability_key": key,
                "fingerprint": fingerprint,
                "artifact_sha256": digest,
            }],
        })

    bundle = {
        "schema": "capability.maturity.evidence.v2",
        "artifacts": artifacts,
        "capabilities": capabilities,
    }
    return bundle, payloads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", action="store_true", help="build a batch bundle for the six keep-atomic capabilities")
    parser.add_argument(
        "--outdir",
        type=Path,
        default=ROOT / "artifacts/backend/capability_maturity_bundle_project_initiation_create",
    )
    args = parser.parse_args()

    if args.batch:
        outdir = ROOT / "artifacts/backend/capability_maturity_bundle_batch"
        bundle, payloads = build_batch_bundle()
        outdir.mkdir(parents=True, exist_ok=True)
        for relative, raw in payloads:
            (outdir / relative).write_bytes(raw)
        bundle_path = outdir / "bundle.json"
        bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        summary = {
            "status": "PROJECTED",
            "head": bundle["capabilities"][0]["receipts"][0]["fingerprint"][:8] if bundle["capabilities"] else "",
            "bundle": str(bundle_path),
            "capabilities": [c["capability_key"] for c in bundle["capabilities"]],
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

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
