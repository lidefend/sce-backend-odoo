"""Evidence-bound capability publication eligibility, independent of principals.

The caller supplies product-owned criteria and evidence bytes obtained through
its trusted verification channel. A digest proves content identity, not who ran
the checks; this evaluator must not be exposed as a self-certification API.
"""
from __future__ import annotations

import hashlib
import json
import re


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _digest(value):
    return isinstance(value, str) and bool(_SHA256.fullmatch(value))


def candidate_fingerprint(capability_key, dependencies):
    """Bind all declared capability inputs; roles and users are not inputs."""
    if not isinstance(capability_key, str) or not capability_key.strip():
        raise ValueError("CAPABILITY_KEY_REQUIRED")
    if not isinstance(dependencies, dict) or not dependencies:
        raise ValueError("CAPABILITY_DEPENDENCIES_REQUIRED")
    if any(not isinstance(key, str) or not key.strip() or not _digest(value)
           for key, value in dependencies.items()):
        raise ValueError("INVALID_CAPABILITY_DEPENDENCY")
    payload = {"capability_key": capability_key, "dependencies": dependencies}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def maturity_fingerprint(capability_key, dependencies, criteria):
    """Criteria changes invalidate evidence even when implementation is unchanged."""
    identity = {"candidate": candidate_fingerprint(capability_key, dependencies), "criteria": criteria}
    return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def evaluate_maturity(*, capability_key, dependencies, criteria, receipts, artifacts):
    """Return standard/preview eligibility without changing any publication.

    Criteria maps edition names to nonempty {check_id: [required_case_ids]}.
    Standard must include every preview check/case. Each receipt binds the
    capability and dependency fingerprint to one JSON artifact. The artifact
    carries executed cases with explicit pass/fail/error/skip statuses.
    Missing, stale, failed or skipped required cases never count as a pass.
    """
    candidate_fingerprint(capability_key, dependencies)
    if not isinstance(criteria, dict) or set(criteria) != {"preview", "standard"}:
        raise ValueError("INVALID_MATURITY_CRITERIA")
    for checks in criteria.values():
        if not isinstance(checks, dict) or not checks:
            raise ValueError("EMPTY_MATURITY_CRITERIA")
        for check, cases in checks.items():
            if (not isinstance(check, str) or not check.strip()
                    or not isinstance(cases, list) or not cases
                    or any(not isinstance(case, str) or not case.strip() for case in cases)
                    or len(cases) != len(set(cases))):
                raise ValueError("INVALID_MATURITY_CASES")
    for check, cases in criteria["preview"].items():
        if not set(cases) <= set(criteria["standard"].get(check, [])):
            raise ValueError("STANDARD_MUST_INCLUDE_PREVIEW_CRITERIA")
    fingerprint = maturity_fingerprint(capability_key, dependencies, criteria)
    if not isinstance(receipts, list) or not isinstance(artifacts, dict):
        raise ValueError("INVALID_MATURITY_EVIDENCE")
    by_check = {}
    duplicates = set()
    for receipt in receipts:
        if not isinstance(receipt, dict) or not isinstance(receipt.get("check_id"), str):
            raise ValueError("INVALID_MATURITY_RECEIPT")
        check = receipt["check_id"]
        if check in by_check:
            duplicates.add(check)
        by_check[check] = receipt

    def assess(check, required):
        if check in duplicates:
            return "DUPLICATE_RECEIPT"
        receipt = by_check.get(check)
        if not receipt:
            return "EVIDENCE_MISSING"
        if receipt.get("capability_key") != capability_key:
            return "CAPABILITY_MISMATCH"
        if receipt.get("fingerprint") != fingerprint:
            return "EVIDENCE_STALE"
        digest = receipt.get("artifact_sha256")
        raw = artifacts.get(digest) if isinstance(digest, str) else None
        if not _digest(digest) or not isinstance(raw, bytes):
            return "ARTIFACT_MISSING"
        if hashlib.sha256(raw).hexdigest() != digest:
            return "ARTIFACT_DIGEST_MISMATCH"
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeError):
            return "ARTIFACT_INVALID"
        if not isinstance(payload, dict):
            return "ARTIFACT_INVALID"
        if (payload.get("capability_key") != capability_key
                or payload.get("fingerprint") != fingerprint
                or payload.get("check_id") != check):
            return "ARTIFACT_SCOPE_MISMATCH"
        cases = payload.get("cases")
        if not isinstance(cases, list) or not cases:
            return "ZERO_EXECUTED_CASES"
        observed = {}
        for case in cases:
            if (not isinstance(case, dict) or not isinstance(case.get("id"), str)
                    or not case["id"].strip() or case["id"] in observed
                    or case.get("status") not in {"pass", "fail", "error", "skip"}):
                return "INVALID_CASE_RESULT"
            observed[case["id"]] = case["status"]
        if any(status in {"fail", "error"} for status in observed.values()):
            return "CHECK_FAILED"
        if not set(required) <= set(observed):
            return "REQUIRED_CASE_MISSING"
        if any(observed[case] != "pass" for case in required):
            return "REQUIRED_CASE_NOT_PASSED"
        return "PASS"

    editions = {}
    for edition in ("preview", "standard"):
        checks = {check: assess(check, cases) for check, cases in criteria[edition].items()}
        editions[edition] = {"eligible": all(value == "PASS" for value in checks.values()), "checks": checks}
    eligible = "standard" if editions["standard"]["eligible"] else "preview" if editions["preview"]["eligible"] else None
    return {"capability_key": capability_key, "fingerprint": fingerprint,
            "proof_domain": "product_capability",
            "eligible_edition": eligible, "editions": editions}


def business_handling_identity(capability_key, product_dependencies, authorization_dependencies, scenarios):
    """An acceptance scope, never a role-to-permission mapping or authorizer."""
    candidate_fingerprint(capability_key, product_dependencies)
    candidate_fingerprint(capability_key, authorization_dependencies)
    if not isinstance(scenarios, dict) or not scenarios:
        raise ValueError("BUSINESS_HANDLING_SCENARIOS_REQUIRED")
    context_fields = {"role_code", "principal_fingerprint", "operation", "company_scope", "data_scope", "record_state"}
    for key, scenario in scenarios.items():
        if not isinstance(key, str) or not key.strip() or not isinstance(scenario, dict):
            raise ValueError("INVALID_BUSINESS_HANDLING_SCENARIO")
        if set(scenario) != context_fields | {"expected"}:
            raise ValueError("BUSINESS_HANDLING_CONTEXT_REQUIRED")
        if any(not isinstance(scenario[field], str) or not scenario[field].strip() for field in context_fields):
            raise ValueError("BUSINESS_HANDLING_CONTEXT_REQUIRED")
        if not _digest(scenario["principal_fingerprint"]):
            raise ValueError("PRINCIPAL_FINGERPRINT_REQUIRED")
        expected = scenario["expected"]
        if (not isinstance(expected, dict) or set(expected) != {"decision", "business_effect", "reason_code"}
                or expected["decision"] not in {"allow", "deny"}
                or not isinstance(expected["business_effect"], dict) or not expected["business_effect"]
                or not isinstance(expected["reason_code"], str)
                or (expected["decision"] == "deny" and not expected["reason_code"].strip())):
            raise ValueError("BUSINESS_HANDLING_EXPECTED_OUTCOME_REQUIRED")
    # Domain separation prevents a product-level pass from serving as a role test.
    evidence_key = "role_business_handling:" + capability_key
    dependencies = {"product_candidate": candidate_fingerprint(capability_key, product_dependencies),
                    "authorization_candidate": candidate_fingerprint(capability_key, authorization_dependencies),
                    "scenarios": hashlib.sha256(json.dumps(scenarios, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
    checks = {"business_handling": sorted(scenarios)}
    criteria = {"preview": checks, "standard": checks}
    return {"capability_key": evidence_key, "dependencies": dependencies, "criteria": criteria}


def evaluate_business_handling(*, capability_key, product_dependencies, authorization_dependencies,
                               scenarios, receipts, artifacts):
    identity = business_handling_identity(capability_key, product_dependencies, authorization_dependencies, scenarios)
    result = evaluate_maturity(**identity, receipts=receipts, artifacts=artifacts)
    checks = dict(result["editions"]["standard"]["checks"])
    verified = result["editions"]["standard"]["eligible"]
    outcomes = {}
    if verified:
        receipt = next(row for row in receipts if row["check_id"] == "business_handling")
        payload = json.loads(artifacts[receipt["artifact_sha256"]])
        cases = {row["id"]: row for row in payload["cases"]}
        for key, scenario in scenarios.items():
            context = {field: value for field, value in scenario.items() if field != "expected"}
            case = cases[key]
            if case.get("observed_context") != context:
                outcomes[key] = "BUSINESS_CONTEXT_MISMATCH"
            elif case.get("observed") != scenario["expected"]:
                outcomes[key] = "BUSINESS_OUTCOME_MISMATCH"
            else:
                outcomes[key] = "PASS"
        verified = all(value == "PASS" for value in outcomes.values())
    return {"proof_domain": "role_business_handling", "capability_key": capability_key,
            "product_fingerprint": candidate_fingerprint(capability_key, product_dependencies),
            "fingerprint": result["fingerprint"], "verified": verified,
            "checks": checks, "scenarios": scenarios, "outcomes": outcomes,
            "authorization_performed": False}
