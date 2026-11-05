"""Build the governed release-navigation snapshot for the acceptance database.

This is test-fixture state only.  It reuses the locked product policy and the
production snapshot service, but is guarded to the dedicated frontend
acceptance database and never promotes a production release candidate.
"""

from __future__ import annotations

import hashlib
import json
import os

from odoo.addons.smart_core.delivery.edition_release_snapshot_service import (
    EditionReleaseSnapshotService,
)



EXPECTED_DATABASE = "sc_frontend_acceptance"
PRODUCT_KEY = "construction.standard"
PLATFORM_RELEASE_DB_PARAM = "smart_core.platform_release_db"
CATALOG_SOURCE_DB_PARAM = "smart_core.release_operator.catalog_source_db"


def _text(value) -> str:
    return str(value or "").strip()


def _guard() -> str:
    database = _text(env.cr.dbname)  # noqa: F821
    if database != EXPECTED_DATABASE:
        raise RuntimeError(
            f"FRONTEND_ACCEPTANCE_SNAPSHOT_DATABASE_DENIED:{database}"
        )
    if _text(os.environ.get("SC_ENVIRONMENT")) != "acceptance":
        raise RuntimeError("FRONTEND_ACCEPTANCE_SNAPSHOT_ENVIRONMENT_DENIED")
    if _text(os.environ.get("SC_ALLOW_DEMO_DATA")) != "1":
        raise RuntimeError("FRONTEND_ACCEPTANCE_SNAPSHOT_FIXTURE_FLAG_REQUIRED")
    return database


def main() -> None:
    database = _guard()
    source_revision = _text(os.environ.get("SC_ACCEPTANCE_SOURCE_REVISION"))
    if len(source_revision) != 40:
        raise RuntimeError("FRONTEND_ACCEPTANCE_SNAPSHOT_SOURCE_REVISION_REQUIRED")
    version = f"frontend-audit-{source_revision[:12]}"

    params = env["ir.config_parameter"].sudo()  # noqa: F821
    params.set_param(PLATFORM_RELEASE_DB_PARAM, database)
    params.set_param(CATALOG_SOURCE_DB_PARAM, database)

    sync = env["sc.product.policy"].sudo().synchronize_locked_formal_menu_policy(  # noqa: F821
        PRODUCT_KEY
    )
    policy = sync["policy"]
    service = EditionReleaseSnapshotService(env)  # noqa: F821
    draft = service.build_policy_draft_contract(product_key=PRODUCT_KEY)
    if int(draft.get("blocking_issue_count") or 0):
        blocking_checks = [
            row
            for row in draft.get("preflight_checks") or []
            if isinstance(row, dict) and row.get("blocking")
        ]
        raise RuntimeError(
            "FRONTEND_ACCEPTANCE_RELEASE_PREFLIGHT_BLOCKED:"
            + json.dumps(blocking_checks, sort_keys=True)
        )
    fingerprint = _text(draft.get("fingerprint"))
    snapshot = env["sc.edition.release.snapshot"].sudo().search(  # noqa: F821
        [
            ("product_key", "=", PRODUCT_KEY),
            ("version", "=", version),
            ("state", "=", "released"),
            ("is_active", "=", True),
            ("active", "=", True),
        ],
        limit=1,
    )
    existing_meta = snapshot.meta_json if snapshot and isinstance(snapshot.meta_json, dict) else {}
    existing_draft = (
        existing_meta.get("release_draft")
        if isinstance(existing_meta.get("release_draft"), dict)
        else {}
    )
    if (snapshot and _text(existing_draft.get("fingerprint")) == fingerprint
            and isinstance(snapshot.snapshot_json, dict)
            and snapshot.snapshot_json.get("policy_snapshot_schema") == "maintained_product_policy.v1"):
        changed = False
    else:
        result = service.freeze_release_surface(
            product_key=PRODUCT_KEY,
            version=version,
            note="isolated frontend acceptance release audit",
            replace_active=True,
        )
        snapshot = env["sc.edition.release.snapshot"].sudo().browse(  # noqa: F821
            int(result.get("id") or 0)
        )
        changed = True

    if not snapshot.exists() or int(snapshot.source_policy_id.id or 0) != int(policy.id):
        raise RuntimeError("FRONTEND_ACCEPTANCE_SNAPSHOT_POLICY_MISMATCH")
    snapshot_meta = snapshot.meta_json if isinstance(snapshot.meta_json, dict) else {}
    snapshot_draft = (
        snapshot_meta.get("release_draft")
        if isinstance(snapshot_meta.get("release_draft"), dict)
        else {}
    )
    if _text(snapshot_draft.get("fingerprint")) != fingerprint:
        raise RuntimeError("FRONTEND_ACCEPTANCE_SNAPSHOT_DRAFT_MISMATCH")
    snapshot_match = service.assert_frozen_release_integrity(snapshot)
    evidence = {
        "schema": "frontend_acceptance_release_snapshot.v1",
        "database": database,
        "product_key": PRODUCT_KEY,
        "version": version,
        "source_revision": source_revision,
        "snapshot_id": snapshot.id,
        "fingerprint": fingerprint,
        "changed": changed,
        "policy_changed": bool(sync.get("changed")),
        "policy_menu_count": int(snapshot_match.get("effective_count") or 0),
        "snapshot_menu_count": int(snapshot_match.get("effective_count") or 0),
        "policy_authority": "sc.product.policy",
        "evidence_sha256": hashlib.sha256(
            json.dumps(
                {
                    "source_revision": source_revision,
                    "fingerprint": fingerprint,
                    "snapshot_id": snapshot.id,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest(),
    }
    env.cr.commit()  # noqa: F821
    print("[acceptance.frontend.release_snapshot] PASS")
    print(json.dumps(evidence, sort_keys=True))


main()
