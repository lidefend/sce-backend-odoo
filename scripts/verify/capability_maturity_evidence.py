#!/usr/bin/env python3
"""Verify a controlled evidence bundle; never publish or grant permissions.

The bundle must come from the governed verification runner/review channel.
Content hashes detect substitution, not malicious claims by a trusted author.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACCEPTANCE_CONTRACTS = Path("addons/smart_construction_core/data/capability_acceptance_contracts_v1.json")
_spec = importlib.util.spec_from_file_location("maturity", ROOT / "addons/smart_core/core/capability_maturity.py")
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


def verify_bundle(path, *, edition, repository=ROOT):
    if edition not in {"standard", "preview"}:
        raise ValueError("INVALID_REQUESTED_EDITION")
    path = Path(path).resolve()
    repository = Path(repository).resolve()
    authority_path = (repository / ACCEPTANCE_CONTRACTS).resolve()
    if not authority_path.is_relative_to(repository):
        raise ValueError("ACCEPTANCE_AUTHORITY_OUTSIDE_REPOSITORY")
    authority_bytes = authority_path.read_bytes()
    authority = json.loads(authority_bytes)
    if (not isinstance(authority, dict) or authority.get("schema") != "capability.acceptance.contracts.v1"
            or not isinstance(authority.get("capabilities"), dict) or not authority["capabilities"]):
        raise ValueError("INVALID_ACCEPTANCE_AUTHORITY")
    bundle = json.loads(path.read_text())
    if not isinstance(bundle, dict) or bundle.get("schema") != "capability.maturity.evidence.v2":
        raise ValueError("INVALID_EVIDENCE_BUNDLE")
    artifacts = {}
    files = bundle.get("artifacts")
    if not isinstance(files, dict):
        raise ValueError("ARTIFACT_MANIFEST_REQUIRED")
    for digest, relative in files.items():
        if not isinstance(relative, str) or Path(relative).is_absolute():
            raise ValueError("ARTIFACT_MUST_BE_BUNDLE_RELATIVE")
        artifact = (path.parent / relative).resolve()
        if not artifact.is_relative_to(path.parent):
            raise ValueError("ARTIFACT_OUTSIDE_BUNDLE")
        artifacts[digest] = artifact.read_bytes()
    capabilities = bundle.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        raise ValueError("ZERO_CAPABILITIES_IS_NOT_A_PASS")
    seen = set()
    rows = []

    def verify_dependencies(dependencies):
        if not isinstance(dependencies, dict) or not dependencies:
            raise ValueError("DEPENDENCY_FILES_REQUIRED")
        for relative, digest in dependencies.items():
            if not isinstance(relative, str) or Path(relative).is_absolute():
                raise ValueError("DEPENDENCY_MUST_BE_REPOSITORY_RELATIVE")
            dependency = (repository / relative).resolve()
            if not dependency.is_relative_to(repository):
                raise ValueError("DEPENDENCY_OUTSIDE_REPOSITORY")
            if hashlib.sha256(dependency.read_bytes()).hexdigest() != digest:
                raise ValueError("CANDIDATE_DEPENDENCY_CHANGED:" + relative)

    for capability in capabilities:
        if not isinstance(capability, dict):
            raise ValueError("INVALID_CAPABILITY_ASSESSMENT")
        key = capability.get("capability_key")
        if not isinstance(key, str) or key in seen:
            raise ValueError("INVALID_OR_DUPLICATE_CAPABILITY")
        seen.add(key)
        contract = authority["capabilities"].get(key)
        if not isinstance(contract, dict):
            raise ValueError("CAPABILITY_ACCEPTANCE_NOT_DECLARED:" + key)
        expected_dependencies = contract.get("product_dependencies")
        if (not isinstance(expected_dependencies, list) or not expected_dependencies
                or any(not isinstance(item, str) or not item for item in expected_dependencies)
                or len(expected_dependencies) != len(set(expected_dependencies))):
            raise ValueError("INVALID_PRODUCT_DEPENDENCY_DECLARATION")
        dependencies = capability.get("dependencies")
        if not isinstance(dependencies, dict) or set(dependencies) != set(expected_dependencies):
            raise ValueError("PRODUCT_DEPENDENCY_SCOPE_MISMATCH:" + key)
        if capability.get("criteria") != contract.get("product_criteria"):
            raise ValueError("PRODUCT_ACCEPTANCE_CRITERIA_MISMATCH:" + key)
        verify_dependencies(dependencies)
        result = gate.evaluate_maturity(
            capability_key=key, dependencies=dependencies,
            criteria=capability.get("criteria"), receipts=capability.get("receipts"), artifacts=artifacts)
        result["requested_edition"] = edition
        result["product_eligible"] = result["editions"][edition]["eligible"]
        handling = capability.get("role_business_handling")
        if handling is None:
            result["role_business_handling"] = {"verified": False, "reason_code": "BUSINESS_HANDLING_EVIDENCE_MISSING"}
        else:
            try:
                if not isinstance(handling, dict):
                    raise ValueError("INVALID_BUSINESS_HANDLING_ASSESSMENT")
                expected_authorization = contract.get("authorization_dependencies")
                if (not isinstance(expected_authorization, list) or not expected_authorization
                        or any(not isinstance(item, str) or not item for item in expected_authorization)
                        or len(expected_authorization) != len(set(expected_authorization))):
                    raise ValueError("INVALID_AUTHORIZATION_DEPENDENCY_DECLARATION")
                if (not isinstance(handling.get("authorization_dependencies"), dict)
                        or set(handling["authorization_dependencies"]) != set(expected_authorization)):
                    raise ValueError("AUTHORIZATION_DEPENDENCY_SCOPE_MISMATCH")
                declared_scenarios = contract.get("business_scenarios")
                scenarios = handling.get("scenarios")
                if (not isinstance(declared_scenarios, dict) or not declared_scenarios
                        or not isinstance(scenarios, dict) or set(scenarios) != set(declared_scenarios)):
                    raise ValueError("BUSINESS_SCENARIO_SCOPE_MISMATCH")
                for scenario_key, scenario in scenarios.items():
                    if (not isinstance(scenario, dict)
                            or {k: v for k, v in scenario.items() if k != "principal_fingerprint"} != declared_scenarios[scenario_key]):
                        raise ValueError("BUSINESS_SCENARIO_CONTRACT_MISMATCH:" + scenario_key)
                verify_dependencies(handling.get("authorization_dependencies"))
                result["role_business_handling"] = gate.evaluate_business_handling(
                    capability_key=key, product_dependencies=dependencies,
                    authorization_dependencies=handling.get("authorization_dependencies"),
                    scenarios=handling.get("scenarios"), receipts=handling.get("receipts"), artifacts=artifacts)
            except (ValueError, OSError, TypeError) as exc:
                result["role_business_handling"] = {"verified": False, "reason_code": "BUSINESS_HANDLING_EVIDENCE_INVALID",
                                                   "error": str(exc)}
        result["scoped_correctness_verified"] = result["product_eligible"] and result["role_business_handling"]["verified"]
        rows.append(result)
    return {"schema": "capability.maturity.report.v2", "requested_edition": edition,
            "acceptance_authority": {"path": str(ACCEPTANCE_CONTRACTS),
                                     "sha256": hashlib.sha256(authority_bytes).hexdigest()},
            "status": "pass" if all(row["product_eligible"] for row in rows) else "blocked",
            "status_scope": "requested_edition_product_qualification",
            "scoped_correctness_verified": all(row["scoped_correctness_verified"] for row in rows),
            "verification_scope": "declared_capabilities_and_business_scenarios_only",
            "capabilities": rows, "publication_performed": False, "authorization_performed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--edition", required=True, choices=("standard", "preview"))
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    try:
        report = verify_bundle(args.bundle, edition=args.edition)
    except (ValueError, OSError, TypeError) as exc:
        report = {"schema": "capability.maturity.report.v2", "status": "blocked",
                  "error": str(exc), "publication_performed": False}
    output = Path(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("[capability.maturity] " + report["status"] + " report=" + str(output))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
