# -*- coding: utf-8 -*-
"""Write/read authority for backed product system parameters.

The controlled parameter catalog declares which parameter is backed by which
authority. ``cost_ledger_source`` and ``default_payment_terms`` are backed by
company fields; ``approval_mode`` is backed by the ``payment.request`` approval
policy (the tier.review runtime authority). Publish writes the owning authority
and returns the previous value; rollback restores it. Nothing here exposes raw
``ir.config_parameter`` or credential material.
"""

from __future__ import annotations

from typing import Any


COST_LEDGER_SOURCE_FIELD_MAP = {
    "account_move": "sc_cost_from_account_move",
    "purchase_order": "sc_cost_from_purchase",
    "stock_move": "sc_cost_from_stock",
}

COMPANY_SELECTION_FIELD_MAP = {
    "default_payment_terms": "sc_default_payment_terms",
}

APPROVAL_MODE_TO_POLICY = {
    "disabled": {"approval_required": False, "mode": "none"},
    "single": {"approval_required": True, "mode": "single"},
    "multi": {"approval_required": True, "mode": "linear"},
}
POLICY_MODE_TO_APPROVAL = {
    "none": "disabled",
    "single": "single",
    "linear": "multi",
}


def _payment_approval_policy(env: Any):
    """Active payment.request approval policy, the tier.review runtime owner."""
    if "sc.approval.policy" not in env:
        return False
    try:
        return env["sc.approval.policy"].sudo().get_active_policy(
            "payment.request", company=env.company
        )
    except Exception:
        return False


def _approval_mode_from_policy(env: Any) -> str:
    policy = _payment_approval_policy(env)
    if not policy or not policy.approval_required or policy.mode == "none":
        return "disabled"
    return POLICY_MODE_TO_APPROVAL.get(policy.mode, "disabled")


def read_parameter_value(env: Any, parameter_key: str):
    """Return the current value of a backed parameter, or None if not backed."""
    key = str(parameter_key or "").strip()
    company = env.company
    if key == "cost_ledger_source":
        enabled = {
            source: bool(getattr(company, field, False))
            for source, field in COST_LEDGER_SOURCE_FIELD_MAP.items()
        }
        selected = [source for source, value in enabled.items() if value]
        return selected[0] if len(selected) == 1 else "disabled"
    if key == "approval_mode":
        return _approval_mode_from_policy(env)
    field = COMPANY_SELECTION_FIELD_MAP.get(key)
    if field and hasattr(company, field):
        return getattr(company, field)
    return None


def apply_parameter_value(env: Any, parameter_key: str, value: Any):
    """Apply a backed parameter value and return the previous value.

    ``env`` must expose the Odoo environment so policy-backed parameters can
    write the tier.review authority.
    """
    key = str(parameter_key or "").strip()
    company = env.company
    previous = read_parameter_value(env, key)
    if key == "cost_ledger_source":
        writable = company.sudo() if callable(getattr(company, "sudo", None)) else company
        writable.write(
            {
                field: value == source
                for source, field in COST_LEDGER_SOURCE_FIELD_MAP.items()
            }
        )
        return previous
    if key == "approval_mode":
        policy_vals = APPROVAL_MODE_TO_POLICY.get(value)
        if policy_vals is None:
            raise ValueError("approval_mode value %r is not declared" % value)
        Policy = env["sc.approval.policy"].sudo()
        policy = _payment_approval_policy(env)
        local_policy = Policy.with_context(active_test=False).search(
            [("target_model", "=", "payment.request"), ("company_id", "=", company.id)],
            limit=1,
        )
        if local_policy:
            # The unique model/company policy may be archived. Reuse its identity
            # rather than creating a duplicate or writing a shared fallback.
            local_policy.write({"active": True, **policy_vals})
        elif policy:
            # A company parameter must never mutate a policy inherited by other
            # companies. One2many steps are explicitly copied, not reparented.
            steps = []
            for step in policy.with_context(active_test=False).step_ids:
                step_vals = step.copy_data()[0]
                step_vals.pop("policy_id", None)
                # Required computed/inverse fields are excluded by copy_data().
                step_vals["approval_scope_key"] = step.approval_scope_key
                steps.append((0, 0, step_vals))
            policy.copy({
                "company_id": company.id,
                "code": "product_parameter_payment_request_approval_%s" % company.id,
                "step_ids": steps,
                **policy_vals,
            })
        elif policy_vals["approval_required"]:
            Policy.create(
                {
                    "name": "付款/收款申请审批规则",
                    "code": "product_parameter_payment_request_approval_%s" % company.id,
                    "target_model": "payment.request",
                    "company_id": company.id,
                    "trigger": "submit",
                    "runtime_state": "policy_only",
                    "sequence": 50,
                    **policy_vals,
                }
            )
        return previous
    field = COMPANY_SELECTION_FIELD_MAP.get(key)
    if field and hasattr(company, field):
        writable = company.sudo() if callable(getattr(company, "sudo", None)) else company
        writable.write({field: value})
        return previous
    raise ValueError("parameter %s has no company authority backing" % key)
