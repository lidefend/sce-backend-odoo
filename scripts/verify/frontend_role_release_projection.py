"""Read-only per-role published projection collector (acceptance carrier).

Executed only through the governed frontend acceptance operation entry against
``sc_frontend_acceptance`` after the acceptance fixture and release snapshot are
ready. This collector only gathers identities; it never reads the navigation
manifest to filter the actual set, and it never prints PASS. The release audit
aggregator recomputes the comparison against the declared leaf identities.

Read-only: the transaction is rolled back and any commit attempt is refused.
"""
from __future__ import annotations

import json

from odoo import api
from odoo.addons.smart_core.delivery.runtime_route_authority import (
    ROUTE_AUTHORITY_BUCKETS,
    published_route_authority as p1_authority,
)


DATABASE = "sc_frontend_acceptance"
PRIMARY_HOME_BUCKETS = ("primary_actions", "role_home_actions")
ACTION_MODELS = (
    "ir.actions.act_window",
    "ir.actions.act_url",
    "ir.actions.server",
    "ir.actions.client",
    "ir.actions.report",
)
# manifest role -> (backend role_code, acceptance fixture login)
ROLES = (
    ("finance", "finance", "fixture_role_finance"),
    ("project_a_member", "project_member", "fixture_role_project_a_member"),
    ("pm", "pm", "fixture_role_pm"),
    ("owner", "owner", "fixture_role_owner"),
)


assert env.cr.dbname == DATABASE, "requires %s, got %s" % (DATABASE, env.cr.dbname)
env.cr.rollback()
_original_commit = env.cr.commit


def _refuse_commit(*_args, **_kwargs):
    raise RuntimeError("read-only projection collector: commit forbidden")


env.cr.commit = _refuse_commit


def _xmlid(record, record_id):
    try:
        return str(record.get_external_id().get(record_id) or "").strip()
    except Exception:
        return ""


def _action_info(action_id):
    for model_name in ACTION_MODELS:
        if model_name not in env:
            continue
        record = env[model_name].sudo().browse(action_id).exists()
        if record:
            return _xmlid(record, action_id), (
                record.res_model if "res_model" in record._fields else ""
            )
    return "", ""


def _menu_xmlid(menu_id):
    if not menu_id:
        return ""
    menu = env["ir.ui.menu"].sudo().browse(menu_id).exists()
    return _xmlid(menu, menu_id) if menu else ""


def _identities(authority, buckets):
    identities = []
    if not isinstance(authority, dict):
        return identities
    for bucket in buckets:
        for row in authority.get(bucket) or []:
            if not isinstance(row, dict):
                continue
            menu_id = int(row.get("menu_id") or 0)
            action_id = int(row.get("action_id") or 0)
            menu = str(row.get("menu_xmlid") or "").strip() or _menu_xmlid(menu_id)
            action, model = _action_info(action_id) if action_id else ("", "")
            identities.append("%s|%s|%s" % (menu, action, model))
    # Preserve raw rows (including intra-bucket duplicates). The aggregator's
    # comparator is the only place that reports duplicates; de-duplicating here
    # would silently hide a repeated published identity.
    return identities


def _bucket_counts(authority):
    if not isinstance(authority, dict):
        return {bucket: 0 for bucket in ROUTE_AUTHORITY_BUCKETS}
    return {
        bucket: len([row for row in authority.get(bucket) or [] if isinstance(row, dict)])
        for bucket in ROUTE_AUTHORITY_BUCKETS
    }


def _denied_rows(authority):
    rows = []
    if not isinstance(authority, dict):
        return rows
    for row in authority.get("denied_actions") or []:
        if not isinstance(row, dict):
            continue
        rows.append({
            "menu_xmlid": str(row.get("menu_xmlid") or "").strip(),
            "menu_id": int(row.get("menu_id") or 0),
            "action_id": int(row.get("action_id") or 0),
            "scene_key": str(row.get("scene_key") or "").strip(),
            "reason_code": str(row.get("reason_code") or "").strip(),
            "source": str(row.get("source") or "").strip(),
        })
    return rows


roles: dict = {}
for manifest_role, _role_code, login in ROLES:
    users = env["res.users"].sudo().search([("login", "=", login), ("active", "=", True)])
    entry = {"login": login, "found_users": len(users)}
    if len(users) != 1:
        entry["error"] = "missing_or_ambiguous"
        roles[manifest_role] = entry
        continue

    user = users[0]
    actor = api.Environment(
        env.cr, user.id, {"allowed_company_ids": [user.company_id.id], "lang": "zh_CN"}
    )
    assert not actor.su, "actor must not be elevated"

    p0 = p1 = None
    p0_error = p1_error = None
    try:
        p0 = actor["sc.product.policy"].published_route_authority()
    except Exception as exc:  # keep the raw fact; never substitute a demo actor
        p0_error = "%s: %s" % (type(exc).__name__, exc)
    try:
        p1 = p1_authority(actor)
    except Exception as exc:
        p1_error = "%s: %s" % (type(exc).__name__, exc)

    roles[manifest_role] = {
        "login": login,
        "uid": user.id,
        "company_id": user.company_id.id,
        "company": user.company_id.name,
        "role_code": (p0 or {}).get("principal_scope", {}).get("role_code")
        if isinstance(p0, dict)
        else None,
        "p0": {
            "primary_home_identities": _identities(p0, PRIMARY_HOME_BUCKETS),
            "bucket_counts": _bucket_counts(p0),
            "error": p0_error,
        },
        "p1": {
            "primary_home_identities": _identities(p1, PRIMARY_HOME_BUCKETS),
            "bucket_counts": _bucket_counts(p1),
            "denied_rows": _denied_rows(p1),
            "error": p1_error,
        },
    }


print(
    "ROLE_RELEASE_PROJECTION="
    + json.dumps({"db": DATABASE, "roles": roles}, ensure_ascii=False, default=str),
    flush=True,
)
env.cr.rollback()
env.cr.commit = _original_commit
