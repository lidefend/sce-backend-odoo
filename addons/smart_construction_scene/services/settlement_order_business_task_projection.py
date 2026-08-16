# -*- coding: utf-8 -*-
"""Project canonical settlement facts into a sealed terminal task."""

from __future__ import annotations

from copy import deepcopy

try:
    from odoo.addons.smart_scene.core.scene_engine import build_scene_contract_from_specs
except ModuleNotFoundError as exc:  # pure contract-test runtime
    if exc.name != "odoo":
        raise
    from addons.smart_scene.core.scene_engine import build_scene_contract_from_specs

from ..profiles.settlement_order_business_task_profile import settlement_order_task_profile_v1
from .canonical_business_task_projection import (
    as_dict,
    as_list,
    canonical_action_capabilities,
    canonical_input,
    display,
    text,
)


_CAPABILITY_METHODS = {
    "settlement_order.submit": {"action_submit"},
    "settlement_order.approve": {"validate_tier", "action_approve", "action_on_tier_approved"},
    "settlement_order.reject": {"reject_tier", "action_on_tier_rejected"},
    "settlement_order.complete": {"action_done"},
    "settlement_order.cancel": {"action_cancel"},
}

_FACT_FIELDS = {
    "settlement_identity": "name",
    "lifecycle_state": "state",
    "project": "project_id",
    "contract": "contract_id",
    "counterparty": "partner_id",
    "submitted_amount": "submitted_amount",
    "approved_amount": "approved_amount",
    "payable_balance": "amount_payable",
    "payment_progress": "amount_paid",
    "legal_next_step": "legal_next_action_display",
}

_INPUT_FIELDS = {
    "settlement_date": "date_settlement",
    "submitted_amount_input": "submitted_amount",
    "approved_amount_input": "approved_amount",
    "settlement_note": "settlement_description",
}


def _page_can_edit(contract: dict) -> bool:
    global_status = as_dict(as_dict(contract.get("statusContract")).get("globalStatus"))
    return text(global_status.get("pageAuth")).lower() in {"edit", "admin"}


def _repair_capability(*, active: bool, authorized: bool) -> dict:
    enabled = bool(active and authorized)
    return {
        "visible": bool(active),
        "business_available": bool(active),
        "authorization_allowed": bool(authorized),
        "enabled": enabled,
        "reason_code": "" if enabled else "STATE_NOT_APPLICABLE" if not active else "ROLE_HANDOFF_REQUIRED",
        "reason": "" if enabled else "当前记录不可编辑，请移交有权经办人。" if active else "",
        "source_authority": "canonical_page_and_widget_status",
    }


def _blockers(record: dict) -> tuple[dict, bool, bool]:
    scope_missing = bool(
        not record.get("project_id")
        or not record.get("partner_id")
        or not as_list(record.get("line_ids"))
        or text(record.get("compliance_state")) == "block"
    )
    state = text(record.get("state"))
    amount_value = record.get("amount_total")
    amount_missing = bool(
        not isinstance(amount_value, (int, float))
        or amount_value <= 0
    )
    return ({
        "contract_scope_consistency": {
            "active": scope_missing,
            "reason_code": "SETTLEMENT_SCOPE_INCOMPLETE" if scope_missing else "",
            "message": "请补齐项目、往来单位、结算明细并处理合同一致性问题。" if scope_missing else "",
            "missing_items": [
                label
                for key, label in (
                    ("project_id", "项目"),
                    ("partner_id", "往来单位"),
                    ("line_ids", "结算明细"),
                )
                if not record.get(key)
            ],
            "source_authority": "normalized_settlement_contract.domain_precheck",
        },
        "amount_readiness": {
            "active": amount_missing,
            "reason_code": "SETTLEMENT_AMOUNT_INCOMPLETE" if amount_missing else "",
            "message": "结算金额必须大于零。" if amount_missing else "",
            "missing_items": [
                "结算金额"
                for value in (amount_value,)
                if not isinstance(value, (int, float)) or value <= 0
            ],
            "source_authority": "normalized_settlement_contract.domain_precheck",
        },
    }, scope_missing, amount_missing)


def _current_capability(
    *,
    state: str,
    validation_status: str,
    capabilities: dict[str, dict],
    scope_missing: bool,
    amount_missing: bool,
) -> str:
    if scope_missing:
        return "settlement_order.repair_scope"
    if amount_missing:
        return "settlement_order.complete_amounts"
    if validation_status in {"waiting", "pending"}:
        candidates = ("settlement_order.approve", "settlement_order.reject")
    elif state == "draft":
        candidates = ("settlement_order.submit",)
    elif state == "submit" and validation_status == "validated":
        candidates = ("settlement_order.approve",)
    elif state == "approve":
        candidates = ("settlement_order.complete",)
    else:
        candidates = ()
    for key in candidates:
        row = capabilities[key]
        if row.get("enabled") or (row.get("visible") and row.get("business_available")):
            return key
    return ""


def _apply_blocker_verdicts(
    capabilities: dict[str, dict],
    *,
    scope_missing: bool,
    amount_missing: bool,
) -> None:
    if not scope_missing and not amount_missing:
        return
    reason_code = "SETTLEMENT_SCOPE_INCOMPLETE" if scope_missing else "SETTLEMENT_AMOUNT_INCOMPLETE"
    reason = "结算事实尚未满足当前办理条件，请先完成阻断项。"
    for key in (
        "settlement_order.submit",
        "settlement_order.approve",
        "settlement_order.complete",
    ):
        row = capabilities[key]
        if not (row.get("visible") or row.get("business_available")):
            continue
        row.update(
            {
                "business_available": False,
                "enabled": False,
                "reason_code": reason_code,
                "reason": reason,
                "source_authority": "canonical_action_and_normalized_settlement_precheck",
            }
        )


def project_settlement_order_business_task_scene(contract: dict, *, render_profile: str = "") -> dict | None:
    page_info = as_dict(contract.get("pageInfo"))
    if text(page_info.get("model")) != "sc.settlement.order" or text(page_info.get("viewType")) != "form":
        return None
    record = as_dict(as_dict(contract.get("dataContract")).get("mainData"))
    if not record:
        return None

    source = "normalized_settlement_contract"
    state = text(record.get("state"))
    validation_status = text(record.get("validation_status"))
    complete = state in {"done", "cancel"}
    blockers, scope_missing, amount_missing = _blockers(record)
    capabilities = canonical_action_capabilities(contract, _CAPABILITY_METHODS)
    editable = _page_can_edit(contract)
    _apply_blocker_verdicts(
        capabilities,
        scope_missing=scope_missing,
        amount_missing=amount_missing,
    )
    capabilities["settlement_order.repair_scope"] = _repair_capability(active=scope_missing, authorized=editable)
    capabilities["settlement_order.complete_amounts"] = _repair_capability(active=amount_missing, authorized=editable)
    next_key = "" if complete else _current_capability(
        state=state,
        validation_status=validation_status,
        capabilities=capabilities,
        scope_missing=scope_missing,
        amount_missing=amount_missing,
    )
    if not complete and not next_key:
        return None

    facts = {
        key: {
            "value": display(record.get(field)),
            "value_state": "known" if field in record else "unavailable",
            "source_authority": source,
            "applicability": "always",
        }
        for key, field in _FACT_FIELDS.items()
    }
    inputs = {
        key: canonical_input(
            contract,
            field=field,
            value=record.get(field),
            source_authority=f"{source}.status_contract",
        )
        for key, field in _INPUT_FIELDS.items()
    }
    supply = {
        "task": {
            "mode": text(render_profile or page_info.get("renderProfile")) or "readonly",
            "stage": "complete" if complete else "approval" if validation_status in {"waiting", "pending", "validated"} else "settlement",
            "state": state or "unknown",
        },
        "facts": facts,
        "inputs": inputs,
        "blockers": blockers,
        "capabilities": capabilities,
        "evidence": {
            "settlement_documents": {"state": "ready", "count": len(as_list(record.get("attachment_ids"))), "required": False, "source_authority": source},
            "approval_audit": {"state": "available", "count": len(as_list(record.get("review_ids"))), "required": validation_status not in {"", "no"}, "source_authority": source},
        },
        "relations": {
            "project_anchor": {"state": "linked" if record.get("project_id") else "empty", "count": 1 if record.get("project_id") else 0, "summary": display(record.get("project_id")), "source_authority": source},
            "contract_anchor": {"state": "linked" if record.get("contract_id") else "empty", "count": 1 if record.get("contract_id") else 0, "summary": display(record.get("contract_id")), "source_authority": source},
            "counterparty_anchor": {"state": "linked" if record.get("partner_id") else "empty", "count": 1 if record.get("partner_id") else 0, "summary": display(record.get("partner_id")), "source_authority": source},
            "payment_requests": {"state": "linked" if as_list(record.get("payment_request_ids")) else "empty", "count": len(as_list(record.get("payment_request_ids"))), "summary": "", "source_authority": source},
        },
        "completion": {
            "complete": complete,
            "next_capability_key": next_key,
            "outcome_code": "SETTLEMENT_COMPLETED" if state == "done" else "SETTLEMENT_CANCELLED" if state == "cancel" else "NEXT_CAPABILITY_REQUIRED",
        },
    }
    return build_scene_contract_from_specs(
        scene_hint={"key": "contract.settlement_order.task", "scene_type": "business_task"},
        page_hint={"key": "contract.settlement_order.task", "title": "合同结算办理"},
        zone_specs=[],
        built_zones={},
        record={},
        diagnostics={"source": "settlement_order_business_task_projection"},
        business_task_profile=settlement_order_task_profile_v1(),
        business_task_semantic_supply=supply,
    )


def attach_settlement_order_business_task_scene(contract: dict, *, render_profile: str = "") -> dict | None:
    scene = project_settlement_order_business_task_scene(contract, render_profile=render_profile)
    if not scene:
        return None
    out = deepcopy(contract)
    runtime = as_dict(out.get("runtimeContract"))
    runtime["businessTaskSceneContract"] = deepcopy(scene.get("scene_contract_v1") or {})
    runtime["businessTaskContract"] = deepcopy(scene.get("business_task") or {})
    out["runtimeContract"] = runtime
    return out
