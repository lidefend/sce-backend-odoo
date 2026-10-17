#!/usr/bin/env python3
"""Fail-closed production target and digest-addressed Compose admission."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PRODUCTION_PROJECT = "sc_production"
PRODUCTION_DATABASE = "sc_production"
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
IMAGE_REF = re.compile(r"^[a-z0-9][a-z0-9._/-]*@(?P<digest>sha256:[0-9a-f]{64})$")


class ComposeContractError(ValueError):
    pass


def validate(
    *,
    project: str,
    database: str,
    odoo_image_ref: str,
    frontend_image_ref: str,
    expected_odoo_digest: str,
    expected_frontend_digest: str,
    manifest: dict,
) -> dict:
    """Admit a two-image production stack.

    The Odoo runtime and the static frontend are separate images: each carries
    its own digest and neither may be inferred from the other. Both must still
    describe the same source revision, so a half-upgraded stack cannot pass.
    """
    if project != PRODUCTION_PROJECT:
        raise ComposeContractError(
            f"production Compose project must be {PRODUCTION_PROJECT}; legacy sc_prod is forbidden"
        )
    if database != PRODUCTION_DATABASE:
        raise ComposeContractError(
            f"production database must be {PRODUCTION_DATABASE}; legacy sc_prod is forbidden"
        )
    identities = {
        "odoo": (odoo_image_ref, expected_odoo_digest),
        "frontend": (frontend_image_ref, expected_frontend_digest),
    }
    for service, (reference, expected_digest) in identities.items():
        if not DIGEST.fullmatch(str(expected_digest)):
            raise ComposeContractError(f"expected {service} image digest is required")
        match = IMAGE_REF.fullmatch(reference)
        if not match:
            raise ComposeContractError(f"{service} image must use image@sha256:<digest>")
        if match.group("digest") != expected_digest:
            raise ComposeContractError(f"{service} image digest does not match expected digest")
    # Digests are independent by contract: the same reference is neither
    # required nor forbidden, but each digest is bound to its own manifest field.
    if manifest.get("image_digest") != expected_odoo_digest:
        raise ComposeContractError("release manifest and Odoo Compose digest differ")
    if manifest.get("frontend_image_digest") != expected_frontend_digest:
        raise ComposeContractError("release manifest and frontend Compose digest differ")
    manifest_odoo_ref = manifest.get("image")
    if manifest_odoo_ref is not None and manifest_odoo_ref != odoo_image_ref:
        raise ComposeContractError("release manifest Odoo image reference differs from Compose")
    manifest_frontend_ref = manifest.get("frontend_image")
    if manifest_frontend_ref is not None and manifest_frontend_ref != frontend_image_ref:
        raise ComposeContractError("release manifest frontend image reference differs from Compose")
    if manifest.get("repository") != "lidefend/sce-backend-odoo":
        raise ComposeContractError("release manifest repository is not approved")
    if manifest.get("branch") != "main":
        raise ComposeContractError("release manifest branch must be main")
    source_revision = str(manifest.get("source_sha") or "")
    if not re.fullmatch(r"[0-9a-f]{40}", source_revision):
        raise ComposeContractError("release manifest source revision is missing or invalid")
    if (
        manifest.get("oci_revision") != source_revision
        or manifest.get("container_source_revision") != source_revision
    ):
        raise ComposeContractError("Odoo/frontend release revision set is inconsistent")
    return {
        "project": project,
        "database": database,
        "odoo": {
            "image_reference": odoo_image_ref,
            "image_digest": expected_odoo_digest,
        },
        "frontend": {
            "image_reference": frontend_image_ref,
            "image_digest": expected_frontend_digest,
        },
        "image_reference": odoo_image_ref,
        "image_digest": expected_odoo_digest,
        "frontend_image_reference": frontend_image_ref,
        "frontend_image_digest": expected_frontend_digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--odoo-image-ref", required=True)
    parser.add_argument("--frontend-image-ref", required=True)
    parser.add_argument("--expected-odoo-digest", required=True)
    parser.add_argument("--expected-frontend-digest", required=True)
    parser.add_argument("--release-manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.release_manifest.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ComposeContractError("release manifest must be an object")
        result = validate(
            project=args.project,
            database=args.database,
            odoo_image_ref=args.odoo_image_ref,
            frontend_image_ref=args.frontend_image_ref,
            expected_odoo_digest=args.expected_odoo_digest,
            expected_frontend_digest=args.expected_frontend_digest,
            manifest=manifest,
        )
    except (OSError, json.JSONDecodeError, ComposeContractError) as exc:
        raise SystemExit(f"[production.compose.contract] BLOCKED: {exc}") from exc
    print("[production.compose.contract] PASS " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
