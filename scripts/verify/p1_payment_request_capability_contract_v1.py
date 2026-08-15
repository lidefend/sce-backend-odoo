#!/usr/bin/env python3
"""Fail closed when the P1 payment-request capability boundary drifts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config/p1_payment_request_capability_contract_v1.json"


def main() -> int:
    contract = json.loads(PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    if contract.get("schema_version") != "p1_payment_request_capability_contract.v1":
        errors.append("unexpected schema version")
    if contract.get("product_stage") != "P1_construction_industry_standard_product":
        errors.append("payment-request work left P1 standard product")
    if contract.get("specific_customer_or_tenant_scope") != "forbidden":
        errors.append("specific customer or tenant scope is not forbidden")
    capabilities = contract.get("capabilities", [])
    if len(capabilities) != 14 or len({row.get("key") for row in capabilities}) != 14:
        errors.append("capability set must contain fourteen unique keys")
    for row in capabilities:
        if not row.get("evidence"):
            errors.append(f"{row.get('key')} has no evidence")
        if row.get("status") != "implemented" and not row.get("gap"):
            errors.append(f"{row.get('key')} has an unexplained gap")
    if contract.get("implementation_sequence", [])[-1].get("status") != "blocked_until_business_acceptance":
        errors.append("component evaluation is no longer acceptance gated")
    boundary = contract.get("change_boundary", {})
    forbidden_surfaces = tuple(boundary.get("forbidden_surfaces", []))
    baseline_sha = str(boundary.get("baseline_sha") or "").strip()
    if len(baseline_sha) != 40:
        errors.append("scope baseline_sha must be an exact commit SHA")
    elif subprocess.run(
        ["git", "merge-base", "--is-ancestor", baseline_sha, "HEAD"],
        cwd=ROOT,
        capture_output=True,
    ).returncode != 0:
        errors.append("scope baseline_sha is not an ancestor of HEAD")
    tracked = subprocess.run(
        ["git", "diff", "--name-only", baseline_sha or "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    changed_paths = sorted(set(tracked + untracked))
    for changed_path in changed_paths:
        if changed_path == "docker-compose.yml" or changed_path.startswith(forbidden_surfaces):
            errors.append(f"candidate crossed P1 payment boundary: {changed_path}")
    scope_manifest = contract.get("scope_manifest") or {}
    declared_paths = [path for paths in scope_manifest.values() for path in paths]
    if len(declared_paths) != len(set(declared_paths)):
        errors.append("scope manifest contains duplicate paths")
    undeclared = sorted(set(changed_paths) - set(declared_paths))
    stale = sorted(set(declared_paths) - set(changed_paths))
    if undeclared:
        errors.append(f"candidate contains undeclared paths: {undeclared}")
    if stale:
        errors.append(f"scope manifest contains unchanged paths: {stale}")
    corpus = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "addons/smart_construction_core/models/core/payment_request.py",
            "addons/smart_construction_core/models/core/payment_execution.py",
            "addons/smart_construction_core/models/core/payment_ledger.py",
            "addons/smart_construction_core/views/core/payment_request_views.xml",
            "addons/smart_construction_core/views/support/user_confirmed_formal_list_views.xml",
            "addons/smart_construction_core/data/payment_request_form_productization_contract.xml",
        )
    )
    for anchor in (
        "_check_contract_business_identity",
        "_sc_assert_transaction_eligible",
        "payee_account_completeness",
        "_business_fact_fields",
        "合同本身是预付款",
        "_assert_payment_relation_anchors_immutable",
        "history_surface_sync",
        "self.env.su",
        "legal_next_action_display",
        "payment_execution_from_request_productized_form_v1",
        "sc_payment_execution_one_active_per_request_idx",
        "payment_ledger_one_posted_per_execution_idx",
        "账户完整度",
        "下一步",
    ):
        if anchor not in corpus:
            errors.append(f"missing payment capability anchor: {anchor}")
    if errors:
        for error in errors:
            print(f"[p1-payment-request-capability] FAIL {error}", file=sys.stderr)
        return 1
    gaps = sum(row.get("status") != "implemented" for row in capabilities)
    print(
        f"[p1-payment-request-capability] PASS capabilities={len(capabilities)} "
        f"open_gaps={gaps} component=blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
