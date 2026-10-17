"""Read-only preference-record inventory for R5 (P4 diagnostic).

The tracked contract snapshot
``docs/contract/snapshots/user_view_preference_set_resolved_intent_admin.json``
carries ``ui_contract_raw.id = 1``.  That number is a database-assigned row
handle from the environment that produced the snapshot; it is *not* proof that
the same row still exists, and it must never be used as a deletion handle.

Run through the governed ``make ... odoo.shell.exec`` carrier.  Read-only:
``env.cr.commit`` is refused, the carrier rolls back, no product code, schema,
fixture or ACL changes, and no row is ever written or deleted.
"""
import json

DATABASE = "sc_dev_demo"
SNAPSHOT_SCOPE_KEY = "ui:list_columns:list:model:res.partner"
SNAPSHOT_CLAIMED_ID = 1

assert env.cr.dbname == DATABASE, "registered local.dev database required"
env.cr.rollback()
_ORIGINAL_COMMIT = env.cr.commit


def _refuse_commit(*_args, **_kwargs):
    raise RuntimeError("preference record probe forbids commit")


env.cr.commit = _refuse_commit


def _xmlid(record):
    try:
        return (record.get_external_id() or {}).get(record.id, "")
    except Exception:
        return ""


def _describe(record):
    user = record.user_id
    return {
        "id": int(record.id),
        "scope_key": str(record.scope_key or ""),
        "preference_key": str(record.preference_key or ""),
        "view_type": str(record.view_type or ""),
        "model_name": str(record.model_name or ""),
        "action_id": int(record.action_id.id or 0),
        "owner_login": str(user.login or "") if user else "",
        "owner_uid": int(user.id or 0) if user else 0,
        "owner_xmlid": _xmlid(user) if user else "",
        "create_date": str(record.create_date or ""),
        "write_date": str(record.write_date or ""),
        "value_json": record.value_json if isinstance(record.value_json, dict) else {},
        "equals_snapshot_claimed_id": int(record.id) == SNAPSHOT_CLAIMED_ID,
    }


REPORT = {
    "schema": "preference-record-probe/v1",
    "database": DATABASE,
    "shell_uid": int(env.uid),
    "snapshot_scope_key": SNAPSHOT_SCOPE_KEY,
    "snapshot_claimed_id": SNAPSHOT_CLAIMED_ID,
    "commit_refused": True,
}

if "sc.user.view.preference" not in env:
    REPORT["status"] = "unavailable"
    REPORT["detail"] = "sc.user.view.preference is not installed in this database"
else:
    Preference = env["sc.user.view.preference"].sudo()
    rows = Preference.search([], order="id")
    REPORT["status"] = "ok"
    REPORT["row_count"] = len(rows)
    REPORT["rows"] = [_describe(record) for record in rows]
    scoped = Preference.search([("scope_key", "=", SNAPSHOT_SCOPE_KEY)], order="id")
    REPORT["snapshot_scope_resolution"] = {
        "matches": len(scoped),
        "resolved_by": "scope_key only, never by the snapshot id",
        "rows": [_describe(record) for record in scoped],
        "snapshot_id_still_points_at_the_same_scope": bool(
            scoped.filtered(lambda record: int(record.id) == SNAPSHOT_CLAIMED_ID)
        ),
    }
    REPORT["registered_non_application_consumers"] = {
        "handlers/business_config_surface.py": "admin audit overview/count of personal preference rows",
        "handlers/form_field_configuration.py": "admin list/search boundary audit of personal preference rows",
    }
    REPORT["sentinel_boundary"] = {
        "model_unknown_scope_keys": int(
            Preference.search_count([("scope_key", "like", "model:unknown")])
        ),
    }
    REPORT["handling_rule"] = (
        "any handling must resolve a row by (user_id, scope_key); the snapshot id is "
        "environment-assigned and is never a deletion handle"
    )

env.cr.rollback()
env.cr.commit = _ORIGINAL_COMMIT
print("PREFERENCE_RECORD_PROBE_REPORT " + json.dumps(REPORT, ensure_ascii=False, sort_keys=True))
