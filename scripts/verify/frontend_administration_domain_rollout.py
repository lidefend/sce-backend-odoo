#!/usr/bin/env python3
"""Audit the formal administration frontend rollout from runtime authority."""

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
        spec = importlib.util.spec_from_file_location(
            "frontend_project_domain_rollout_shared", mounted
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"shared domain rollout runtime is unavailable: {mounted}")
        shared = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(shared)
        return shared


_SHARED = _load_shared_runtime()
collect_domain = _SHARED.collect_domain
write_report = _SHARED.write_report

DOMAIN_KEY = "administration"
ROOT_MENU_XMLIDS = ("smart_construction_core.menu_sc_hr_admin_center",)
OWNER_MODULE = "smart_construction_core"
OUTPUT_PATH = Path(
    os.getenv(
        "FRONTEND_ADMINISTRATION_DOMAIN_ROLLOUT_PATH",
        "/tmp/frontend_administration_domain_rollout_v1.json",
    )
)
EXPECTED_ANCHORS = {
    "smart_construction_core.action_sc_organization_department",
    "smart_construction_core.action_sc_runtime_user_management",
    "smart_construction_core.action_sc_certificate_registration",
    "smart_construction_core.action_sc_payroll_management",
    "smart_construction_core.action_sc_product_job_management_v1",
    "smart_construction_core.action_sc_product_social_fund_v1",
    "smart_construction_core.action_sc_product_office_asset_v1",
    "smart_construction_core.action_sc_product_policy_document_v1",
}


def collect(env) -> dict[str, object]:
    return collect_domain(
        env,
        domain_key=DOMAIN_KEY,
        root_menu_xmlids=ROOT_MENU_XMLIDS,
        owner_module=OWNER_MODULE,
        expected_anchors=EXPECTED_ANCHORS,
    )


if "env" in globals():  # pragma: no branch - Odoo shell execution contract
    payload = collect(env)  # type: ignore[name-defined]  # noqa: F821
    write_report(payload, OUTPUT_PATH)
    print(json.dumps({
        "status": payload["status"],
        "summary": payload["summary"],
        "actions": [row["action_xmlid"] for row in payload["actions"]],
        "output": str(OUTPUT_PATH),
    }, ensure_ascii=False))
    if payload["status"] != "PASS":
        raise RuntimeError(json.dumps(payload["gaps"], ensure_ascii=False))
