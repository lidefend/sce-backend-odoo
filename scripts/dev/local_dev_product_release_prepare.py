# -*- coding: utf-8 -*-
"""Prepare the published product surface required by local.dev acceptance.

Execute only through ``make local.dev.product_release.prepare`` in the
registered ``sc-local-dev / sc_dev_demo`` profile. The command uses the
existing Odoo product release services; it does not insert snapshot rows or
define product policy itself.
"""
from __future__ import annotations

import json
import os
import re


EXPECTED_DATABASE = "sc_dev_demo"
EXPECTED_ENVIRONMENT = "dev"
PRODUCT_KEY = "construction.standard"
CATALOG_SOURCE_DB_PARAM = "smart_core.release_operator.catalog_source_db"
PLATFORM_RELEASE_DB_PARAM = "smart_core.platform_release_db"


def validate_identity(*, database, environment, source_revision):
    database = str(database or "").strip()
    environment = str(environment or "").strip()
    source_revision = str(source_revision or "").strip().lower()
    if database != EXPECTED_DATABASE:
        raise RuntimeError(f"LOCAL_DEV_PRODUCT_RELEASE_DATABASE_DENIED:{database}")
    if environment != EXPECTED_ENVIRONMENT:
        raise RuntimeError(
            f"LOCAL_DEV_PRODUCT_RELEASE_ENVIRONMENT_DENIED:{environment}"
        )
    if not re.fullmatch(r"[0-9a-f]{40}", source_revision):
        raise RuntimeError("LOCAL_DEV_PRODUCT_RELEASE_SOURCE_REVISION_REQUIRED")
    return {
        "database": database,
        "environment": environment,
        "source_revision": source_revision,
    }


def release_version(source_revision):
    revision = str(source_revision or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise RuntimeError("LOCAL_DEV_PRODUCT_RELEASE_SOURCE_REVISION_REQUIRED")
    return f"local-dev-{revision[:12]}"


def prepare_product_release(env, *, source_revision, environment):
    database = str(getattr(getattr(env, "cr", None), "dbname", "") or "").strip()
    identity = validate_identity(
        database=database,
        environment=environment,
        source_revision=source_revision,
    )
    from odoo.addons.smart_core.delivery.edition_release_snapshot_service import (
        EditionReleaseSnapshotService,
    )
    from odoo.addons.smart_core.delivery.effective_delivery_inputs import (
        _load_platform_release_gate,
    )

    params = env["ir.config_parameter"].sudo()
    before = {
        "catalog_source_db": str(params.get_param(CATALOG_SOURCE_DB_PARAM, "") or ""),
        "platform_release_db": str(params.get_param(PLATFORM_RELEASE_DB_PARAM, "") or ""),
        "snapshot_count": env["sc.edition.release.snapshot"]
        .sudo()
        .with_context(active_test=False)
        .search_count([("product_key", "=", PRODUCT_KEY)]),
    }
    params.set_param(CATALOG_SOURCE_DB_PARAM, database)
    params.set_param(PLATFORM_RELEASE_DB_PARAM, database)

    service = EditionReleaseSnapshotService(env)
    draft = service.build_policy_draft_contract(product_key=PRODUCT_KEY)
    blocking = [
        row
        for row in (draft.get("preflight_checks") or [])
        if isinstance(row, dict) and row.get("blocking")
    ]
    if blocking:
        raise RuntimeError(
            "LOCAL_DEV_PRODUCT_RELEASE_PREFLIGHT_BLOCKED:"
            + json.dumps(blocking, ensure_ascii=False, sort_keys=True, default=str)
        )

    version = release_version(identity["source_revision"])
    result = service.freeze_release_surface(
        product_key=PRODUCT_KEY,
        version=version,
        note="SCENE-PRODUCT-02 governed local.dev acceptance precondition",
        replace_active=True,
    )
    snapshot = env["sc.edition.release.snapshot"].sudo().browse(
        int(result.get("id") or 0)
    )
    if not snapshot.exists():
        raise RuntimeError("LOCAL_DEV_PRODUCT_RELEASE_SNAPSHOT_NOT_FOUND")
    if snapshot.state != "released" or not snapshot.is_active or not snapshot.active:
        raise RuntimeError("LOCAL_DEV_PRODUCT_RELEASE_SNAPSHOT_NOT_EFFECTIVE")

    active_count = (
        env["sc.edition.release.snapshot"]
        .sudo()
        .with_context(active_test=False)
        .search_count(
            [
                ("product_key", "=", PRODUCT_KEY),
                ("state", "=", "released"),
                ("is_active", "=", True),
                ("active", "=", True),
            ]
        )
    )
    if active_count != 1:
        raise RuntimeError(
            f"LOCAL_DEV_PRODUCT_RELEASE_ACTIVE_SNAPSHOT_NOT_UNIQUE:{active_count}"
        )

    gate = _load_platform_release_gate(env, product_key=PRODUCT_KEY)
    if not gate.get("applied") or int(gate.get("snapshot_id") or 0) != snapshot.id:
        raise RuntimeError(
            "LOCAL_DEV_PRODUCT_RELEASE_GATE_READBACK_MISMATCH:"
            + json.dumps(gate, ensure_ascii=False, sort_keys=True, default=str)
        )
    return {
        "status": "PASS",
        "identity": identity,
        "before": before,
        "after": {
            "catalog_source_db": str(
                params.get_param(CATALOG_SOURCE_DB_PARAM, "") or ""
            ),
            "platform_release_db": str(
                params.get_param(PLATFORM_RELEASE_DB_PARAM, "") or ""
            ),
            "snapshot_id": int(snapshot.id),
            "snapshot_version": str(snapshot.version or ""),
            "snapshot_state": str(snapshot.state or ""),
            "snapshot_is_active": bool(snapshot.is_active),
            "snapshot_active": bool(snapshot.active),
            "active_snapshot_count": active_count,
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
        },
        "fingerprint": str(draft.get("fingerprint") or ""),
        "policy_sha256": str(draft.get("policy_sha256") or ""),
    }


def main():
    try:
        result = prepare_product_release(
            env,  # noqa: F821 - Odoo shell supplies the execution environment.
            source_revision=os.environ.get(
                "PRODUCT_RELEASE_SOURCE_REVISION", ""
            ),
            environment=os.environ.get("SC_ENVIRONMENT", ""),
        )
        env.cr.commit()  # noqa: F821 - explicit persistent acceptance setup.
    except Exception:
        env.cr.rollback()  # noqa: F821 - leave no partial release configuration.
        raise
    print(
        "LOCAL_DEV_PRODUCT_RELEASE="
        + json.dumps(result, ensure_ascii=False, sort_keys=True, default=str)
    )


if "env" in globals():
    main()
