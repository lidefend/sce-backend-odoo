"""Create an active release snapshot from the maintained database product policy.

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
    try:
        with env.cr.savepoint():  # noqa: F821
            sync = env["sc.product.policy"].sudo().synchronize_locked_formal_menu_policy(  # noqa: F821
                product_key,
            )
            policy = sync["policy"]
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
            if (existing and _text(existing_draft.get("fingerprint")) == fingerprint
                    and draft.get("policy_sha256")
                    and existing_draft.get("policy_sha256") == draft["policy_sha256"]
                    and isinstance(existing.snapshot_json, dict)
                    and existing.snapshot_json.get("policy_snapshot_schema") == "maintained_product_policy.v1"):
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

            snapshot = env["sc.edition.release.snapshot"].sudo().browse(int(result.get("id") or 0))  # noqa: F821
            if not snapshot.exists() or int(snapshot.source_policy_id.id or 0) != int(policy.id):
                raise RuntimeError("LOCKED_MENU_SNAPSHOT_SOURCE_POLICY_MISMATCH")
            snapshot_meta = snapshot.meta_json if isinstance(snapshot.meta_json, dict) else {}
            snapshot_draft = snapshot_meta.get("release_draft") if isinstance(snapshot_meta.get("release_draft"), dict) else {}
            if (_text(snapshot_draft.get("fingerprint")) != fingerprint
                    or not draft.get("policy_sha256")
                    or snapshot_draft.get("policy_sha256") != draft["policy_sha256"]):
                raise RuntimeError("RELEASE_SNAPSHOT_DRAFT_MISMATCH")
            post_snapshot_match = service.assert_frozen_release_integrity(snapshot)

    except Exception:
        env.cr.rollback()  # noqa: F821
        raise
    env.cr.commit()  # noqa: F821
    print(json.dumps({
        "status": "PASS",
        "database": current_db,
        "product_key": product_key,
        "version": version,
        "snapshot_id": int(result.get("id") or 0),
        "fingerprint": fingerprint,
        "changed": changed,
        "policy_changed": bool(sync.get("changed")),
        "policy_authority": "sc.product.policy",
        "policy_menu_count": int(post_snapshot_match.get("released_count") or 0),
        "snapshot_menu_count": int(post_snapshot_match.get("released_count") or 0),
        "snapshot_preview_page_count": int(post_snapshot_match.get("preview_count") or 0),
        "snapshot_effective_page_count": int(post_snapshot_match.get("effective_count") or 0),
        "policy_normalized_sha256": fingerprint,
        "snapshot_normalized_sha256": _text(post_snapshot_match.get("fingerprint")),
        "idempotent": True,
    }, sort_keys=True))


main()
