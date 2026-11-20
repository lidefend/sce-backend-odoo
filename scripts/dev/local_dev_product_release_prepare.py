# -*- coding: utf-8 -*-
"""Export the approved product policy from the local demo database."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path


EXPECTED_DATABASE = "sc_dev_demo"
EXPECTED_PLATFORM_CONTROL_DATABASE = "sc_platform_control"
EXPECTED_ENVIRONMENT = "dev"
PRODUCT_KEY = "construction.standard"
ARTIFACT_SCHEMA = "sce.local_platform_release_source.v1"


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


def validate_release_databases(*, catalog_source_db, platform_release_db):
    catalog_source_db = str(catalog_source_db or "").strip()
    platform_release_db = str(platform_release_db or "").strip()
    if catalog_source_db != EXPECTED_DATABASE:
        raise RuntimeError(
            f"LOCAL_DEV_PRODUCT_RELEASE_CATALOG_SOURCE_DENIED:{catalog_source_db}"
        )
    if platform_release_db != EXPECTED_PLATFORM_CONTROL_DATABASE:
        raise RuntimeError(
            f"LOCAL_DEV_PRODUCT_RELEASE_PLATFORM_DATABASE_DENIED:{platform_release_db}"
        )
    if catalog_source_db == platform_release_db:
        raise RuntimeError("LOCAL_DEV_PRODUCT_RELEASE_DATABASE_SEPARATION_REQUIRED")
    return {
        "catalog_source_db": catalog_source_db,
        "platform_release_db": platform_release_db,
    }


def _stable_sha256(value):
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def prepare_product_release(env, *, source_revision, environment, artifact_path):
    database = str(getattr(getattr(env, "cr", None), "dbname", "") or "").strip()
    identity = validate_identity(
        database=database,
        environment=environment,
        source_revision=source_revision,
    )
    release_databases = validate_release_databases(
        catalog_source_db=database,
        platform_release_db=EXPECTED_PLATFORM_CONTROL_DATABASE,
    )
    from odoo import api
    from odoo.addons.smart_core.delivery.edition_release_snapshot_service import (
        EditionReleaseSnapshotService,
    )
    from odoo.addons.smart_core.delivery.product_policy_service import (
        ProductPolicyService,
    )
    from odoo.addons.smart_core.delivery.product_scene_composition import (
        compose_product_policy,
    )

    source_policy = ProductPolicyService(env).get_policy(
        product_key=PRODUCT_KEY,
        enforce_release=True,
        enforce_access=True,
        use_published_policy=False,
    )
    source_policy = compose_product_policy(env, source_policy)
    composition = source_policy.get("business_scene_composition")
    if not isinstance(composition, dict):
        raise RuntimeError("LOCAL_DEV_PRODUCT_RELEASE_SCENE_COMPOSITION_MISSING")
    scenarios = composition.get("scenarios")
    if not isinstance(scenarios, list) or len(scenarios) != 46:
        raise RuntimeError(
            "LOCAL_DEV_PRODUCT_RELEASE_SCENE_COUNT_MISMATCH:"
            f"{len(scenarios) if isinstance(scenarios, list) else 'invalid'}"
        )
    source_env = api.Environment(
        env.cr,
        env.uid,
        {
            **env.context,
            "sc_release_catalog_source_db": database,
        },
    )
    draft = EditionReleaseSnapshotService(source_env).build_policy_draft_contract(
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
            "LOCAL_DEV_PRODUCT_RELEASE_PREFLIGHT_BLOCKED:"
            + json.dumps(
                blocking,
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
        )
    if int(draft.get("page_count") or 0) != 132:
        raise RuntimeError(
            f"LOCAL_DEV_PRODUCT_RELEASE_PAGE_COUNT_MISMATCH:{draft.get('page_count')}"
        )
    artifact = {
        "schema": ARTIFACT_SCHEMA,
        "source_revision": identity["source_revision"],
        "catalog_source_db": release_databases["catalog_source_db"],
        "platform_release_db": release_databases["platform_release_db"],
        "product_key": PRODUCT_KEY,
        "release_version": release_version(identity["source_revision"]),
        "source_policy": source_policy,
        "source_policy_sha256": _stable_sha256(source_policy),
        "source_draft": {
            "fingerprint": str(draft.get("fingerprint") or ""),
            "policy_sha256": str(draft.get("policy_sha256") or ""),
            "page_count": int(draft.get("page_count") or 0),
            "total_page_count": int(draft.get("total_page_count") or 0),
            "scenario_count": len(scenarios),
        },
    }
    path = Path(artifact_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return {
        "status": "PASS",
        "identity": identity,
        "release_databases": release_databases,
        "artifact": str(path),
        "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_policy_sha256": artifact["source_policy_sha256"],
        "source_draft": artifact["source_draft"],
    }


def main():
    artifact_path = os.environ.get("PRODUCT_RELEASE_ARTIFACT", "").strip()
    if not artifact_path:
        raise RuntimeError("PRODUCT_RELEASE_ARTIFACT_REQUIRED")
    result = prepare_product_release(
        env,  # noqa: F821 - Odoo shell supplies the execution environment.
        source_revision=os.environ.get(
            "PRODUCT_RELEASE_SOURCE_REVISION", ""
        ),
        environment=os.environ.get("SC_ENVIRONMENT", ""),
        artifact_path=artifact_path,
    )
    print(
        "LOCAL_DEV_PRODUCT_RELEASE="
        + json.dumps(result, ensure_ascii=False, sort_keys=True, default=str)
    )


if "env" in globals():
    main()
