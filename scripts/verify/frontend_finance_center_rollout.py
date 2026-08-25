#!/usr/bin/env python3
"""Audit the formal finance-center frontend rollout from runtime authority."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path


def _load_shared_runtime():
    try:
        from scripts.verify import frontend_project_domain_rollout as shared
        return shared
    except ModuleNotFoundError:
        mounted = Path("/mnt/scripts/verify/frontend_project_domain_rollout.py")
        spec = importlib.util.spec_from_file_location("frontend_project_domain_rollout_shared", mounted)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"shared domain rollout runtime is unavailable: {mounted}")
        shared = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(shared)
        return shared


_SHARED = _load_shared_runtime()
collect_domain = _SHARED.collect_domain
write_report = _SHARED.write_report

DOMAIN_KEY = "finance_center"
ROOT_MENU_XMLIDS = ("smart_construction_core.menu_sc_finance_center",)
OWNER_MODULE = "smart_construction_core"
OUTPUT_PATH = Path(os.getenv(
    "FRONTEND_FINANCE_CENTER_ROLLOUT_PATH",
    "/tmp/frontend_finance_center_rollout_v1.json",
))
EXPECTED_ANCHORS = {
    "smart_construction_core.action_sc_receipt_income",
    "smart_construction_core.action_payment_request_user_payment_apply",
    "smart_construction_core.action_sc_payment_execution_actual_outflow",
    "smart_construction_core.action_sc_expense_claim_reimbursement_request",
    "smart_construction_core.action_sc_product_current_account_v1",
    "smart_construction_core.action_sc_receipt_income_user_income",
    "smart_construction_core.action_sc_payment_execution_company_finance_expense",
    "smart_construction_core.action_sc_expense_claim_deduction_bill",
    "smart_construction_core.action_sc_product_company_project_refund_v1",
    "smart_construction_core.action_sc_expense_claim_advance_fund",
    "smart_construction_core.action_project_funding_baseline_summary",
}


def collect(env) -> dict[str, object]:
    return collect_domain(
        env,
        domain_key=DOMAIN_KEY,
        root_menu_xmlids=ROOT_MENU_XMLIDS,
        owner_module=OWNER_MODULE,
        expected_anchors=EXPECTED_ANCHORS,
    )


if "env" in globals():  # pragma: no branch
    payload = collect(env)  # type: ignore[name-defined]  # noqa: F821
    write_report(payload, OUTPUT_PATH)
    print(json.dumps({
        "status": payload["status"], "summary": payload["summary"],
        "actions": [row["action_xmlid"] for row in payload["actions"]],
        "output": str(OUTPUT_PATH),
    }, ensure_ascii=False))
    if payload["status"] != "PASS":
        raise RuntimeError(json.dumps(payload["gaps"], ensure_ascii=False))
