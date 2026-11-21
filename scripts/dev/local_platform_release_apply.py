# -*- coding: utf-8 -*-
"""Apply the approved product policy artifact inside platform control."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


EXPECTED_DATABASE = "sc_platform_control"
EXPECTED_CATALOG_SOURCE_DATABASE = "sc_dev_demo"
PRODUCT_KEY = "construction.standard"
CATALOG_SOURCE_DB_PARAM = "smart_core.release_operator.catalog_source_db"
PLATFORM_RELEASE_DB_PARAM = "smart_core.platform_release_db"
ARTIFACT_SCHEMA = "sce.local_platform_release_source.v1"


def _stable_sha256(value):
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def apply_release(env, *, artifact_path):
    database = str(getattr(getattr(env, "cr", None), "dbname", "") or "").strip()
    if database != EXPECTED_DATABASE:
        raise RuntimeError(
            f"LOCAL_PLATFORM_RELEASE_DATABASE_DENIED:{database}"
        )
    path = Path(artifact_path)
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if artifact.get("schema") != ARTIFACT_SCHEMA:
        raise RuntimeError("LOCAL_PLATFORM_RELEASE_ARTIFACT_SCHEMA_MISMATCH")
    if artifact.get("catalog_source_db") != EXPECTED_CATALOG_SOURCE_DATABASE:
        raise RuntimeError("LOCAL_PLATFORM_RELEASE_CATALOG_SOURCE_MISMATCH")
    if artifact.get("platform_release_db") != EXPECTED_DATABASE:
        raise RuntimeError("LOCAL_PLATFORM_RELEASE_PLATFORM_DATABASE_MISMATCH")
    if artifact.get("product_key") != PRODUCT_KEY:
        raise RuntimeError("LOCAL_PLATFORM_RELEASE_PRODUCT_MISMATCH")
    source_policy = artifact.get("source_policy")
    if not isinstance(source_policy, dict):
        raise RuntimeError("LOCAL_PLATFORM_RELEASE_POLICY_MISSING")
    if _stable_sha256(source_policy) != artifact.get("source_policy_sha256"):
        raise RuntimeError("LOCAL_PLATFORM_RELEASE_POLICY_DIGEST_MISMATCH")
    scenarios = (
        source_policy.get("business_scene_composition") or {}
    ).get("scenarios")
    if not isinstance(scenarios, list) or len(scenarios) != 46:
        raise RuntimeError(
            "LOCAL_PLATFORM_RELEASE_SCENE_COUNT_MISMATCH:"
            f"{len(scenarios) if isinstance(scenarios, list) else 'invalid'}"
        )

    from odoo.addons.smart_core.delivery.edition_release_snapshot_service import (
        EditionReleaseSnapshotService,
    )
    from odoo.addons.smart_core.delivery.effective_delivery_inputs import (
        _load_platform_release_gate,
    )

    params = env["ir.config_parameter"].sudo()
    params.set_param(CATALOG_SOURCE_DB_PARAM, EXPECTED_CATALOG_SOURCE_DATABASE)
    params.set_param(PLATFORM_RELEASE_DB_PARAM, EXPECTED_DATABASE)
    service = EditionReleaseSnapshotService(env)
    draft = service.build_policy_draft_contract(
        product_key=PRODUCT_KEY,
        policy_override=source_policy,
    )
    blocking = [
        row
        for row in (draft.get("preflight_checks") or [])
        if isinstance(row, dict) and row.get("blocking")
    ]
    if blocking:
        raise RuntimeError(
            "LOCAL_PLATFORM_RELEASE_PREFLIGHT_BLOCKED:"
            + json.dumps(
                blocking,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
        )
    result = service.freeze_release_surface(
        product_key=PRODUCT_KEY,
        version=str(artifact["release_version"]),
        note="SCENE-PRODUCT-02 approved cross-database product release",
        replace_active=True,
        policy_override=source_policy,
    )
    snapshot = env["sc.edition.release.snapshot"].sudo().browse(
        int(result.get("id") or 0)
    )
    if not snapshot.exists():
        raise RuntimeError("LOCAL_PLATFORM_RELEASE_SNAPSHOT_NOT_FOUND")
    if snapshot.state != "released" or not snapshot.is_active or not snapshot.active:
        raise RuntimeError("LOCAL_PLATFORM_RELEASE_SNAPSHOT_NOT_EFFECTIVE")
    active_count = (
        env["sc.edition.release.snapshot"]
        .sudo()
        .with_context(active_test=False)
        .search_count([
            ("product_key", "=", PRODUCT_KEY),
            ("state", "=", "released"),
            ("is_active", "=", True),
            ("active", "=", True),
        ])
    )
    if active_count != 1:
        raise RuntimeError(
            f"LOCAL_PLATFORM_RELEASE_ACTIVE_SNAPSHOT_NOT_UNIQUE:{active_count}"
        )
    gate = _load_platform_release_gate(env, product_key=PRODUCT_KEY)
    if not gate.get("applied") or int(gate.get("snapshot_id") or 0) != snapshot.id:
        raise RuntimeError(
            "LOCAL_PLATFORM_RELEASE_GATE_READBACK_MISMATCH:"
            + json.dumps(
                gate,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
        )
    released_composition = (
        snapshot.snapshot_json.get("business_scene_composition") or {}
    )
    released_scenarios = released_composition.get("scenarios") or []
    env.cr.commit()
    return {
        "status": "PASS",
        "database": database,
        "catalog_source_db": str(
            params.get_param(CATALOG_SOURCE_DB_PARAM, "") or ""
        ),
        "platform_release_db": str(
            params.get_param(PLATFORM_RELEASE_DB_PARAM, "") or ""
        ),
        "source_revision": artifact["source_revision"],
        "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "snapshot_id": int(snapshot.id),
        "snapshot_version": str(snapshot.version or ""),
        "snapshot_state": str(snapshot.state or ""),
        "snapshot_is_active": bool(snapshot.is_active),
        "snapshot_active": bool(snapshot.active),
        "active_snapshot_count": active_count,
        "page_count": int(draft.get("page_count") or 0),
        "scenario_count": len(released_scenarios),
        "release_gate": {
            key: gate.get(key)
            for key in (
                "applied",
                "reason",
                "snapshot_id",
                "version",
                "page_count",
                "platform_db",
            )
        },
    }


def main():
    artifact_path = os.environ.get("PRODUCT_RELEASE_ARTIFACT", "").strip()
    if not artifact_path:
        raise RuntimeError("PRODUCT_RELEASE_ARTIFACT_REQUIRED")
    result = apply_release(
        env,  # noqa: F821 - Odoo shell supplies the execution environment.
        artifact_path=artifact_path,
    )
    print(
        "LOCAL_PLATFORM_RELEASE="
        + json.dumps(result, ensure_ascii=False, sort_keys=True, default=str)
    )


if "env" in globals():
    main()
