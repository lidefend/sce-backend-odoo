"""Create an active release snapshot from version-controlled product policy.

Run only through the governed Make target against an isolated clone first.
The service owns snapshot creation and promotion; this script never inserts
snapshot rows directly and never reads an independent platform database.
"""

from __future__ import annotations

import json
import os

from odoo.addons.smart_core.delivery.edition_release_snapshot_service import EditionReleaseSnapshotService


ACK = "I_ACKNOWLEDGE_COLOCATED_PLATFORM_SNAPSHOT_INITIALIZATION"
PARAM = "smart_core.platform_release_db"


def _text(value):
    return str(value or "").strip()


def main():
    current_db = _text(env.cr.dbname)  # noqa: F821
    expected_db = _text(os.environ.get("PLATFORM_RELEASE_DB"))
    product_key = _text(os.environ.get("PLATFORM_RELEASE_PRODUCT_KEY"))
    version = _text(os.environ.get("PLATFORM_RELEASE_VERSION"))
    if os.environ.get("SC_COLOCATED_PLATFORM_SNAPSHOT_APPLY") != ACK:
        raise RuntimeError("COLOCATED_PLATFORM_SNAPSHOT_APPLY_ACK_REQUIRED")
    if not current_db or expected_db != current_db:
        raise RuntimeError("PLATFORM_RELEASE_DB_MUST_MATCH_CURRENT")
    configured = _text(env["ir.config_parameter"].sudo().get_param(PARAM, ""))  # noqa: F821
    if configured != current_db:
        raise RuntimeError("PLATFORM_RELEASE_DB_PARAMETER_MUST_MATCH_CURRENT")
    if not product_key or not version:
        raise RuntimeError("PLATFORM_RELEASE_PRODUCT_KEY_AND_VERSION_REQUIRED")
    policy = env["sc.product.policy"].sudo().search([  # noqa: F821
        ("product_key", "=", product_key),
        ("active", "=", True),
    ], limit=1)
    if not policy:
        raise RuntimeError("ACTIVE_PRODUCT_POLICY_NOT_FOUND")

    service = EditionReleaseSnapshotService(env)  # noqa: F821
    draft = service.build_policy_draft_contract(product_key=product_key)
    if int(draft.get("blocking_issue_count") or 0):
        raise RuntimeError("RELEASE_PREFLIGHT_BLOCKED")
    fingerprint = _text(draft.get("fingerprint"))
    existing = env["sc.edition.release.snapshot"].sudo().search([  # noqa: F821
        ("product_key", "=", product_key),
        ("version", "=", version),
        ("state", "=", "released"),
        ("is_active", "=", True),
        ("active", "=", True),
    ], limit=1)
    existing_meta = existing.meta_json if existing and isinstance(existing.meta_json, dict) else {}
    existing_draft = existing_meta.get("release_draft") if isinstance(existing_meta.get("release_draft"), dict) else {}
    if existing and _text(existing_draft.get("fingerprint")) == fingerprint:
        result = existing.to_runtime_dict()
        changed = False
    else:
        result = service.freeze_release_surface(
            product_key=product_key,
            version=version,
            note="deterministic colocated production release initialization",
            replace_active=True,
        )
        changed = True
    env.cr.commit()  # noqa: F821
    print(json.dumps({
        "status": "PASS",
        "database": current_db,
        "product_key": product_key,
        "version": version,
        "snapshot_id": int(result.get("id") or 0),
        "fingerprint": fingerprint,
        "changed": changed,
        "idempotent": True,
    }, sort_keys=True))


main()
