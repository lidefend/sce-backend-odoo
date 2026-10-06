# -*- coding: utf-8 -*-
"""Unified project-ledger field-overlay repair.

项目台账 (action ``smart_construction_core.action_sc_project_list``) is the
single project-center record entry.  The duplicate 项目信息编辑 surface was
retired, and its complete composition must be carried by 项目台账.

When the two surfaces were split, the ledger was a secondary dashboard and a
user-level legacy ``ui.form.field.policy`` overlay suppressed fields that its
own authoritative native form declares (for example ``project_code``).  A
legacy compatibility overlay is a projection-only carrier: it may annotate a
surface, but it must not silently strip the fields the unified surface's
authoritative native form declares.  That overlay was never retired together
with the duplicate entry, so the runtime contract lost ``project_code`` even
though the ledger form declares it.

This repair derives the required set from declarations (the ledger's
authoritative native form plus the retired form that must be carried) and
retires only the ledger-action overlay rows that suppress those fields.  It is
idempotent, scoped to one action/model, and never touches ACL, record rules or
field permissions.
"""

from __future__ import annotations

from lxml import etree

LEDGER_ACTION_XMLID = "smart_construction_core.action_sc_project_list"
LEDGER_FORM_VIEW_XMLID = "smart_construction_core.view_project_overview_form"
RETIRED_FORM_VIEW_XMLID = (
    "smart_construction_core.view_sc_product_project_information_edit_form_v1"
)
LEDGER_MODEL = "project.project"
POLICY_MODEL = "ui.form.field.policy"


def _arch_field_names(view) -> set[str]:
    if not view:
        return set()
    try:
        arch = view._get_combined_arch()
    except Exception:
        return set()
    if isinstance(arch, (str, bytes)):
        try:
            arch = etree.fromstring(arch)
        except Exception:
            return set()
    return {name for name in arch.xpath("//field/@name") if name}


def ledger_required_field_names(env) -> set[str]:
    """Fields the unified ledger must render, derived from declarations."""

    required = _arch_field_names(env.ref(LEDGER_FORM_VIEW_XMLID, raise_if_not_found=False))
    required |= _arch_field_names(env.ref(RETIRED_FORM_VIEW_XMLID, raise_if_not_found=False))
    return required


def retire_stale_ledger_field_overlay(env, *, dry_run: bool = True) -> dict:
    """Retire ledger-action overlays that suppress the declared composition."""

    action = env.ref(LEDGER_ACTION_XMLID, raise_if_not_found=False)
    report = {
        "action_xmlid": LEDGER_ACTION_XMLID,
        "action_id": int(action.id) if action else 0,
        "model": LEDGER_MODEL,
        "dry_run": bool(dry_run),
        "status": "skipped",
        "required_fields": [],
        "retired": [],
        "reason": "",
    }
    required = ledger_required_field_names(env)
    report["required_fields"] = sorted(required)
    if not action or not required:
        report["reason"] = "ledger action or declared composition unavailable"
        return report

    rows = env[POLICY_MODEL].sudo().search(
        [
            ("model", "=", LEDGER_MODEL),
            ("action_id", "=", action.id),
            ("visible", "=", False),
            ("active", "=", True),
            ("field_name", "in", sorted(required)),
        ],
        order="id",
    ) if POLICY_MODEL in env else None
    if rows is None:
        report["reason"] = "field-policy carrier unavailable"
        return report
    if not rows:
        report["status"] = "noop"
        report["reason"] = "no suppressing overlay rows"
        return report

    report["retired"] = [
        {"id": int(row.id), "field_name": row.field_name} for row in rows
    ]
    if dry_run:
        report["status"] = "dry_run"
        return report

    rows.write({"active": False})
    env.flush_all()
    report["status"] = "applied"
    return report
