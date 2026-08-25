#!/usr/bin/env python3
"""Audit the formal collaboration frontend rollout from runtime authority."""

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

DOMAIN_KEY = "collaboration"
ROOT_MENU_XMLIDS = (
    "smart_construction_core.menu_sc_product_message_notification_v1",
)
OWNER_MODULE = "smart_construction_core"
OUTPUT_PATH = Path(
    os.getenv(
        "FRONTEND_COLLABORATION_DOMAIN_ROLLOUT_PATH",
        "/tmp/frontend_collaboration_domain_rollout_v1.json",
    )
)
EXPECTED_ANCHORS = {
    "smart_construction_core.action_sc_product_message_notification_v1",
}


def _find_key(value, key):
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            found = _find_key(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_key(child, key)
            if found is not None:
                return found
    return None


def collect_form_contract_runtime(env) -> dict[str, object]:
    """Prove the exact form binding through the production ORM and V2 handler."""
    from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler

    user = env.ref("smart_construction_demo.sc_demo_user_test_admin")
    action = env.ref(
        "smart_construction_core.action_sc_product_message_notification_v1"
    )
    menu = env.ref("smart_construction_core.menu_sc_product_message_notification_v1")
    view = env.ref("smart_construction_core.view_sc_product_mail_notification_form")
    expected = env.ref(
        "smart_construction_core.business_config_contract_mail_notification_form_v1"
    )
    user_env = env(user=user.id, context={
        **env.context,
        "allowed_company_ids": user.company_ids.ids,
    })
    selected = user_env[
        "ui.business.config.contract"
    ]._effective_view_orchestration_contracts(
        "mail.notification",
        view_type="form",
        action_id=action.id,
        view_id=view.id,
    )
    selected_ids = [int(row.id) for row in selected]
    if expected.id not in selected_ids:
        raise RuntimeError(
            "collaboration form selector missed exact contract: selected=%s expected=%s"
            % (selected_ids, expected.id)
        )
    payload = {
        "op": "action_open",
        "action_id": int(action.id),
        "menu_id": int(menu.id),
        "model": "mail.notification",
        "view_type": "form",
        "view_id": int(view.id),
        "render_profile": "readonly",
        "client_type": "web_pc",
        "delivery_profile": "full",
    }
    result = UiContractV2Handler(user_env, payload=payload).run(payload=payload)
    contract = result.data if getattr(result, "ok", False) else {}
    if not isinstance(contract, dict) or not contract:
        raise RuntimeError("collaboration readonly form Contract V2 projection failed")
    structure = _find_key(contract, "formStructureContract")
    if not isinstance(structure, dict):
        raise RuntimeError("collaboration form structure contract is missing")
    business_contracts = _find_key(structure, "businessConfigContracts")
    projected_ids = {
        int(row.get("id") or 0)
        for row in business_contracts if isinstance(row, dict)
    } if isinstance(business_contracts, list) else set()
    if expected.id not in projected_ids:
        raise RuntimeError(
            "Contract V2 trace missed exact collaboration contract: projected=%s"
            % sorted(projected_ids)
        )
    if structure.get("presentationMode") != "task":
        raise RuntimeError("collaboration form did not resolve task presentation")
    effective_profile = _find_key(contract, "effectiveRenderProfile")
    if effective_profile != "readonly":
        raise RuntimeError(
            "collaboration form did not preserve readonly authority: %r"
            % effective_profile
        )
    resolved_form_view = next(
        (
            binding.view_id
            for binding in action.view_ids.sorted(lambda row: (row.sequence, row.id))
            if binding.view_mode == "form" and binding.view_id
        ),
        env["ir.ui.view"],
    )
    if resolved_form_view != view:
        raise RuntimeError("collaboration action resolved an unexpected form view")
    return {
        "action_xmlid": action.get_external_id().get(action.id, ""),
        "view_xmlid": view.get_external_id().get(view.id, ""),
        "selected_contract_xmlid": expected.get_external_id().get(expected.id, ""),
        "presentation_mode": structure.get("presentationMode"),
        "effective_render_profile": effective_profile,
        "form_structure_authority": _find_key(structure, "formStructureAuthority"),
    }


def collect(env) -> dict[str, object]:
    payload = collect_domain(
        env,
        domain_key=DOMAIN_KEY,
        root_menu_xmlids=ROOT_MENU_XMLIDS,
        owner_module=OWNER_MODULE,
        expected_anchors=EXPECTED_ANCHORS,
    )
    payload["form_contract_runtime"] = collect_form_contract_runtime(env)
    return payload


if "env" in globals():  # pragma: no branch - Odoo shell execution contract
    payload = collect(env)  # type: ignore[name-defined]  # noqa: F821
    write_report(payload, OUTPUT_PATH)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "summary": payload["summary"],
                "actions": [row["action_xmlid"] for row in payload["actions"]],
                "output": str(OUTPUT_PATH),
            },
            ensure_ascii=False,
        )
    )
    if payload["status"] != "PASS":
        raise RuntimeError(json.dumps(payload["gaps"], ensure_ascii=False))
