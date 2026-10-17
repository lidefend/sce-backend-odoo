"""Read-only preference-record inventory for the contract-snapshot profile (R5, P4 diagnostic).

The tracked snapshot
``docs/contract/snapshots/user_view_preference_set_intent_admin.json`` used to
carry ``ui_contract_raw.id = 1`` written under the legacy ``model:unknown``
sentinel scope.  That number is a database-assigned row handle from the
environment that produced the snapshot; it is *not* proof that the same row
still exists and it must never be used as a deletion handle.

This probe reads the *registered* contract-snapshot database
(``sc-contract-snapshot-v1`` / ``sc_contract_snapshot``) through the governed
``make ... local.contract-snapshot.odoo-shell`` carrier.  Read-only:
``env.cr.commit`` is refused, the carrier rolls back, no product code, schema,
fixture or ACL change, and no row is ever written or deleted.
"""
import json

SNAPSHOT_CLAIMED_ID = 1
SNAPSHOT_SCOPE_KEY = "ui:list_columns:list:model:res.partner"
SENTINEL_MARKER = "model:unknown"

env.cr.rollback()
_ORIGINAL_COMMIT = env.cr.commit


def _refuse_commit(*_args, **_kwargs):
    raise RuntimeError("contract-snapshot preference record probe forbids commit")


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
        "is_snapshot_claimed_id": int(record.id) == SNAPSHOT_CLAIMED_ID,
    }


REPORT = {
    "schema": "contract-snapshot-preference-record-probe/v1",
    "database": str(env.cr.dbname),
    "shell_uid": int(env.uid),
    "snapshot_claimed_id": SNAPSHOT_CLAIMED_ID,
    "snapshot_scope_key": SNAPSHOT_SCOPE_KEY,
    "sentinel_marker": SENTINEL_MARKER,
    "commit_refused": True,
    "handling_rule": (
        "any handling must resolve a row by (user_id, scope_key) through a governed entry; "
        "the snapshot id is environment-assigned and is never a deletion handle"
    ),
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
    claimed = Preference.search([("id", "=", SNAPSHOT_CLAIMED_ID)], limit=1)
    REPORT["snapshot_claimed_id_resolution"] = {
        "exists": bool(claimed),
        "resolved_by": "id lookup only to describe the historical pointer, never to delete",
        "row": _describe(claimed) if claimed else None,
    }
    scoped = Preference.search([("scope_key", "=", SNAPSHOT_SCOPE_KEY)], order="id")
    REPORT["declared_scope_resolution"] = {
        "matches": len(scoped),
        "resolved_by": "scope_key only, never by the snapshot id",
        "rows": [_describe(record) for record in scoped],
    }
    REPORT["sentinel_boundary"] = {
        "model_unknown_scope_keys": int(
            Preference.search_count([("scope_key", "like", SENTINEL_MARKER)])
        ),
    }

env.cr.rollback()
env.cr.commit = _ORIGINAL_COMMIT
print(
    "CONTRACT_SNAPSHOT_PREFERENCE_RECORD_PROBE_REPORT "
    + json.dumps(REPORT, ensure_ascii=False, sort_keys=True)
)
