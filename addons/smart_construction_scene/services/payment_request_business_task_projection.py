# -*- coding: utf-8 -*-
"""Project a normalized payment form into a terminal business-task scene.

This adapter is pure.  It consumes only materialized record facts and the final
canonical action/status authority; it never queries ORM or infers permissions.
"""

from __future__ import annotations

from copy import deepcopy
try:
    from odoo.addons.smart_scene.core.scene_engine import build_scene_contract_from_specs
except ModuleNotFoundError as exc:  # pure contract-test runtime
    if exc.name != "odoo":
        raise
    from addons.smart_scene.core.scene_engine import build_scene_contract_from_specs

from ..profiles.payment_request_business_task_profile import payment_request_task_profile_v1
from .canonical_business_task_projection import (
    as_dict as _dict,
    as_list as _list,
    canonical_action_capabilities,
    display as _display,
    inactive_capability as _inactive_capability,
    text as _text,
)


_CAPABILITY_METHODS = {
    "payment_request.submit": {"action_submit"},
    "payment_request.approve": {"action_approve", "action_set_approved", "validate_tier", "action_approval_decision"},
    "payment_request.reject": {"reject_tier", "action_on_tier_rejected"},
    "payment_execution.create": {"action_create_payment_execution"},
    "payment_execution.open": {"action_view_payment_execution"},
    "payment_request.cancel": {"action_cancel"},
}

_FACT_FIELDS = {
    "request_identity": "name",
    "handling_subject": "payment_flow_label",
    "lifecycle_state": "state",
    "project": "project_id",
    "payee": "partner_id",
    "payment_basis": "payment_basis_type",
    "requested_amount": "amount",
    "payable_balance": "unpaid_amount",
    "account_readiness": "payee_account_completeness",
    "account_source": "payee_account_source_display",
    "execution_status": "payment_execution_status_display",
    "blocking_summary": "payment_blocking_reason_display",
    "legal_next_step": "legal_next_action_display",
}


def _action_capabilities(contract: dict) -> dict[str, dict]:
    out = canonical_action_capabilities(contract, _CAPABILITY_METHODS)
    for key in (
        "counterparty.resolve_eligibility",
        "payment_request.complete_basis",
        "counterparty.maintain_settlement_account",
    ):
        out[key] = _inactive_capability()
    return out


def _stage(state: str, capabilities: dict[str, dict]) -> str:
    if state in {"done", "cancel"}:
        return "complete"
    if capabilities["payment_execution.open"]["enabled"]:
        return "payment_execution"
    if capabilities["payment_execution.create"]["enabled"]:
        return "payment_ready"
    if state in {"submit", "approve"}:
        return "approval"
    return "preparation"


def project_payment_request_business_task_scene(contract: dict, *, render_profile: str = "") -> dict | None:
    """Return one sealed terminal scene or ``None`` outside payment forms."""

    page_info = _dict(contract.get("pageInfo"))
    if _text(page_info.get("model")) != "payment.request" or _text(page_info.get("viewType")) != "form":
        return None
    record = _dict(_dict(contract.get("dataContract")).get("mainData"))
    if not record:
        return None
    capabilities = _action_capabilities(contract)
    state = _text(record.get("state"))
    profile = _text(render_profile or page_info.get("renderProfile")) or "readonly"
    source = "normalized_payment_request_contract"
    facts = {
        key: {
            "value": _display(record.get(field)),
            "value_state": "known" if field in record else "unavailable",
            "source_authority": source,
            "applicability": "always",
        }
        for key, field in _FACT_FIELDS.items()
    }
    account_missing = _text(record.get("payee_account_completeness")) == "incomplete"
    basis_missing = not any(record.get(key) for key in ("contract_id", "settlement_id", "material_settlement_id"))
    eligibility = _text(record.get("partner_transaction_eligibility"))
    eligibility_blocked = bool(eligibility and eligibility not in {"eligible", "review"})
    blockers = {
        "counterparty_eligibility": {
            "active": eligibility_blocked,
            "reason_code": "COUNTERPARTY_NOT_ELIGIBLE" if eligibility_blocked else "",
            "message": _text(record.get("partner_transaction_eligibility_reason")) if eligibility_blocked else "",
            "missing_items": ["counterparty_eligibility"] if eligibility_blocked else [],
            "source_authority": source,
        },
        "payment_basis_readiness": {
            "active": basis_missing,
            "reason_code": "PAYMENT_BASIS_REQUIRED" if basis_missing else "",
            "message": "请补充付款依据" if basis_missing else "",
            "missing_items": ["payment_basis"] if basis_missing else [],
            "source_authority": source,
        },
        "payee_account_readiness": {
            "active": account_missing,
            "reason_code": "PAYEE_ACCOUNT_INCOMPLETE" if account_missing else "",
            "message": _text(record.get("payment_blocking_reason_display")) if account_missing else "",
            "missing_items": ["account_name", "bank_name", "account_number"] if account_missing else [],
            "source_authority": source,
        },
    }
    repair_by_blocker = {
        "counterparty_eligibility": "counterparty.resolve_eligibility",
        "payment_basis_readiness": "payment_request.complete_basis",
        "payee_account_readiness": "counterparty.maintain_settlement_account",
    }
    for blocker_key, capability_key in repair_by_blocker.items():
        if blockers[blocker_key]["active"]:
            capabilities[capability_key].update({
                "visible": True,
                "business_available": True,
                "reason_code": "ACTION_PERMISSION_UNRESOLVED",
            })
    next_key = next(
        (key for key, row in capabilities.items() if row.get("enabled") and key != "payment_request.cancel"),
        "",
    )
    complete = state in {"done", "cancel"}
    if not complete and not next_key:
        next_key = next(
            (
                key
                for key, row in capabilities.items()
                if key != "payment_request.cancel"
                and row.get("visible")
                and row.get("business_available")
            ),
            "",
        )
    if not complete and not next_key:
        next_key = next(
            (repair_by_blocker[key] for key, row in blockers.items() if row.get("active")),
            "",
        )
    if not complete and not next_key and capabilities["payment_request.cancel"].get("enabled"):
        next_key = "payment_request.cancel"
    if not complete and not next_key:
        return None
    supply = {
        "task": {"mode": profile, "stage": _stage(state, capabilities), "state": state or "unknown"},
        "facts": facts,
        "inputs": {
            "application_note": {
                "value": record.get("note") or "",
                "visible": "note" in record,
                "readonly": profile == "readonly",
                "required": False,
                "source_authority": source,
                "applicability": "always",
            }
        },
        "blockers": blockers,
        "capabilities": capabilities,
        "evidence": {
            "attachments": {
                "state": "ready",
                "count": len(_list(record.get("attachment_ids"))),
                "required": False,
                "source_authority": source,
            },
            "approval_audit": {
                "state": "available",
                "count": len(_list(record.get("review_ids"))),
                "required": state in {"submit", "approved", "done"},
                "source_authority": source,
            },
        },
        "relations": {
            "project_anchor": {"state": "linked" if record.get("project_id") else "empty", "count": 1 if record.get("project_id") else 0, "summary": _display(record.get("project_id")), "source_authority": source},
            "payee_anchor": {"state": "linked" if record.get("partner_id") else "empty", "count": 1 if record.get("partner_id") else 0, "summary": _display(record.get("partner_id")), "source_authority": source},
            "contract_anchor": {"state": "linked" if record.get("contract_id") else "empty", "count": 1 if record.get("contract_id") else 0, "summary": _display(record.get("contract_id")), "source_authority": source},
            "settlement_anchor": {"state": "linked" if record.get("settlement_id") else "empty", "count": 1 if record.get("settlement_id") else 0, "summary": _display(record.get("settlement_id")), "source_authority": source},
            "payment_execution_relation": {"state": "linked" if record.get("has_active_payment_execution") else "empty", "count": 1 if record.get("has_active_payment_execution") else 0, "summary": _text(record.get("payment_execution_status_display")), "source_authority": source},
        },
        "completion": {
            "complete": complete,
            "next_capability_key": "" if complete else next_key,
            "outcome_code": "PAYMENT_REQUEST_COMPLETED" if state == "done" else "PAYMENT_REQUEST_CANCELLED" if state == "cancel" else "NEXT_CAPABILITY_REQUIRED",
        },
    }
    return build_scene_contract_from_specs(
        scene_hint={"key": "finance.payment_request.task", "scene_type": "business_task"},
        page_hint={"key": "finance.payment_request.task", "title": "付款申请办理"},
        zone_specs=[],
        built_zones={},
        record={},
        diagnostics={"source": "payment_request_business_task_projection"},
        business_task_profile=payment_request_task_profile_v1(),
        business_task_semantic_supply=supply,
    )


def attach_payment_request_business_task_scene(contract: dict, *, render_profile: str = "") -> dict | None:
    scene = project_payment_request_business_task_scene(contract, render_profile=render_profile)
    if not scene:
        return None
    out = deepcopy(contract)
    runtime = _dict(out.get("runtimeContract"))
    runtime["businessTaskSceneContract"] = deepcopy(scene.get("scene_contract_v1") or {})
    runtime["businessTaskContract"] = deepcopy(scene.get("business_task") or {})
    out["runtimeContract"] = runtime
    return out
