# -*- coding: utf-8 -*-
"""Project canonical payment-execution facts into a sealed terminal task."""

from __future__ import annotations

from copy import deepcopy

try:
    from odoo.addons.smart_scene.core.scene_engine import build_scene_contract_from_specs
except ModuleNotFoundError as exc:  # pure contract-test runtime
    if exc.name != "odoo":
        raise
    from addons.smart_scene.core.scene_engine import build_scene_contract_from_specs

from ..profiles.payment_execution_business_task_profile import payment_execution_task_profile_v1
from .canonical_business_task_projection import (
    as_dict,
    as_list,
    canonical_action_capabilities,
    canonical_input,
    display,
    text,
)


_CAPABILITY_METHODS = {
    "payment_execution.submit": {"action_confirm"},
    "payment_execution.approve": {"validate_tier", "action_on_tier_approved"},
    "payment_execution.reject": {"reject_tier", "action_on_tier_rejected"},
    "payment_execution.mark_paid": {"action_paid"},
    "payment_execution.cancel": {"action_cancel"},
    "payment_execution.reverse": {"action_reverse_payment"},
}

_FACT_FIELDS = {
    "execution_identity": "name",
    "handling_subject": "execution_flow_label",
    "lifecycle_state": "state",
    "approval_state": "validation_status",
    "source_request": "payment_request_id",
    "project": "project_id",
    "payee": "partner_id",
    "contract": "contract_id",
    "planned_amount": "planned_amount",
    "paid_amount": "paid_amount",
    "payment_method": "payment_method",
    "receipt_account_name": "receipt_account_name",
    "receipt_bank_name": "receipt_bank_name",
    "receipt_account_no": "receipt_account_no",
    "payment_account_name": "payment_account_name",
    "payment_bank_name": "payment_bank_name",
    "payment_account_no": "payment_account_no",
    "responsibility_state": "company_contractor_responsibility_state",
    "cancellation_kind": "cancellation_kind",
}

_INPUT_FIELDS = {
    "payment_date": "date_payment",
    "actual_amount": "paid_amount",
    "payment_method_input": "payment_method",
    "payment_account_name_input": "payment_account_name",
    "payment_bank_name_input": "payment_bank_name",
    "payment_account_no_input": "payment_account_no",
    "note": "note",
    "reversal_reason": "reversal_reason",
}

def _stage(state: str, validation_status: str) -> str:
    if state in {"paid", "cancel", "legacy_confirmed"}:
        return "complete"
    if validation_status in {"waiting", "pending"}:
        return "approval"
    if state == "confirmed":
        return "payment"
    return "preparation"


def _blockers(contract: dict) -> tuple[dict, bool, set[str]] | None:
    semantics = as_dict(as_dict(contract.get("runtimeContract")).get("businessTaskSemantics"))
    if text(semantics.get("version")) != "v1" or not text(semantics.get("source_authority")):
        return None
    row = as_dict(as_dict(semantics.get("blockers")).get("payment_fact_readiness"))
    active = row.get("active")
    missing_items = row.get("missing_items")
    repair_fields = row.get("repair_field_names")
    if not isinstance(active, bool) or not isinstance(missing_items, list) or not isinstance(repair_fields, list):
        return None
    normalized_repair_fields = {text(item) for item in repair_fields if text(item)}
    if normalized_repair_fields - set(_INPUT_FIELDS.values()):
        return None
    reason_code = text(row.get("reason_code"))
    message = text(row.get("message"))
    source_authority = text(row.get("source_authority"))
    if not source_authority or (active and (not reason_code or not message)):
        return None
    blocker = {
        "active": active,
        "reason_code": reason_code,
        "message": message,
        "missing_items": [text(item) for item in missing_items if text(item)],
        "source_authority": source_authority,
    }
    return {"payment_fact_readiness": blocker}, active, normalized_repair_fields


def _payment_facts_can_edit(contract: dict, repair_fields: set[str]) -> bool:
    if not repair_fields:
        return False
    for row in as_list(as_dict(contract.get("statusContract")).get("widgetStatus")):
        if not isinstance(row, dict):
            continue
        widget_id = text(row.get("widgetId"))
        if not widget_id.startswith("field.") or widget_id[6:] not in repair_fields:
            continue
        if row.get("visible") is True and row.get("readonly") is False and row.get("disabled") is False:
            return True
    return False


def _repair_capability(*, active: bool, authorized: bool) -> dict:
    enabled = bool(active and authorized)
    return {
        "visible": bool(active),
        "business_available": bool(active),
        "authorization_allowed": bool(authorized),
        "enabled": enabled,
        "reason_code": "" if enabled else "STATE_NOT_APPLICABLE" if not active else "ROLE_HANDOFF_REQUIRED",
        "reason": "" if enabled else "当前付款事实不可编辑，请移交有权经办人。" if active else "",
        "source_authority": "canonical_payment_execution_widget_status",
    }


def _apply_payment_fact_blocker(capabilities: dict[str, dict], *, blocker: dict) -> None:
    if not blocker.get("active"):
        return
    for key in ("payment_execution.submit", "payment_execution.mark_paid"):
        row = capabilities[key]
        if not (row.get("visible") or row.get("business_available")):
            continue
        row.update({
            "business_available": False,
            "enabled": False,
            "reason_code": text(blocker.get("reason_code")) or "PAYMENT_EXECUTION_FACTS_INCOMPLETE",
            "reason": text(blocker.get("message")) or "付款事实尚未满足当前办理条件，请先完成阻断项。",
            "source_authority": "canonical_action_and_payment_execution_model_prechecks",
        })


def _current_capability(state: str, validation_status: str, capabilities: dict[str, dict]) -> str:
    candidates = []
    if validation_status in {"waiting", "pending"}:
        candidates.extend(("payment_execution.approve", "payment_execution.reject"))
    elif state == "draft":
        candidates.append("payment_execution.submit")
    elif state == "confirmed":
        candidates.append("payment_execution.mark_paid")
    for key in candidates:
        row = capabilities[key]
        if row.get("enabled") or (row.get("visible") and row.get("business_available")):
            return key
    return ""


def project_payment_execution_business_task_scene(contract: dict, *, render_profile: str = "") -> dict | None:
    page_info = as_dict(contract.get("pageInfo"))
    if text(page_info.get("model")) != "sc.payment.execution" or text(page_info.get("viewType")) != "form":
        return None
    record = as_dict(as_dict(contract.get("dataContract")).get("mainData"))
    if not record:
        return None

    source = "normalized_payment_execution_contract"
    blocker_projection = _blockers(contract)
    if blocker_projection is None:
        return None
    blockers, payment_facts_blocked, repair_fields = blocker_projection
    capabilities = canonical_action_capabilities(contract, _CAPABILITY_METHODS)
    _apply_payment_fact_blocker(
        capabilities,
        blocker=blockers["payment_fact_readiness"],
    )
    capabilities["payment_execution.complete_facts"] = _repair_capability(
        active=payment_facts_blocked,
        authorized=_payment_facts_can_edit(contract, repair_fields),
    )
    state = text(record.get("state"))
    validation_status = text(record.get("validation_status"))
    complete = state in {"paid", "cancel", "legacy_confirmed"}
    next_key = "" if complete else (
        "payment_execution.complete_facts"
        if payment_facts_blocked
        else _current_capability(state, validation_status, capabilities)
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
            "stage": _stage(state, validation_status),
            "state": state or "unknown",
        },
        "facts": facts,
        "inputs": inputs,
        "blockers": blockers,
        "capabilities": capabilities,
        "evidence": {
            "attachments": {"state": "ready", "count": len(as_list(record.get("attachment_ids"))), "required": False, "source_authority": source},
            "approval_audit": {"state": "available", "count": len(as_list(record.get("review_ids"))), "required": validation_status not in {"", "no"}, "source_authority": source},
        },
        "relations": {
            "request_anchor": {"state": "linked" if record.get("payment_request_id") else "empty", "count": 1 if record.get("payment_request_id") else 0, "summary": display(record.get("payment_request_id")), "source_authority": source},
            "project_anchor": {"state": "linked" if record.get("project_id") else "empty", "count": 1 if record.get("project_id") else 0, "summary": display(record.get("project_id")), "source_authority": source},
            "payee_anchor": {"state": "linked" if record.get("partner_id") else "empty", "count": 1 if record.get("partner_id") else 0, "summary": display(record.get("partner_id")), "source_authority": source},
            "contract_anchor": {"state": "linked" if record.get("contract_id") else "empty", "count": 1 if record.get("contract_id") else 0, "summary": display(record.get("contract_id")), "source_authority": source},
        },
        "completion": {
            "complete": complete,
            "next_capability_key": next_key,
            "outcome_code": "PAYMENT_POSTED" if state == "paid" else "PAYMENT_REVERSED_OR_CANCELLED" if state == "cancel" else "LEGACY_PAYMENT_RECORDED" if state == "legacy_confirmed" else "NEXT_CAPABILITY_REQUIRED",
        },
    }
    return build_scene_contract_from_specs(
        scene_hint={"key": "finance.payment_execution.task", "scene_type": "business_task"},
        page_hint={"key": "finance.payment_execution.task", "title": "付款登记办理"},
        zone_specs=[],
        built_zones={},
        record={},
        diagnostics={"source": "payment_execution_business_task_projection"},
        business_task_profile=payment_execution_task_profile_v1(),
        business_task_semantic_supply=supply,
    )


def attach_payment_execution_business_task_scene(contract: dict, *, render_profile: str = "") -> dict | None:
    scene = project_payment_execution_business_task_scene(contract, render_profile=render_profile)
    if not scene:
        return None
    out = deepcopy(contract)
    runtime = as_dict(out.get("runtimeContract"))
    runtime["businessTaskSceneContract"] = deepcopy(scene.get("scene_contract_v1") or {})
    runtime["businessTaskContract"] = deepcopy(scene.get("business_task") or {})
    out["runtimeContract"] = runtime
    return out
