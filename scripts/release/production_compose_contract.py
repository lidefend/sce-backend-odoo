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
    nginx_image_ref: str,
    expected_digest: str,
    manifest: dict,
) -> dict[str, str]:
    if project != PRODUCTION_PROJECT:
        raise ComposeContractError(
            f"production Compose project must be {PRODUCTION_PROJECT}; legacy sc_prod is forbidden"
        )
    if database != PRODUCTION_DATABASE:
        raise ComposeContractError(
            f"production database must be {PRODUCTION_DATABASE}; legacy sc_prod is forbidden"
        )
    if not DIGEST.fullmatch(expected_digest):
        raise ComposeContractError("expected image digest is required")
    references = {"odoo": odoo_image_ref, "nginx": nginx_image_ref}
    for service, reference in references.items():
        match = IMAGE_REF.fullmatch(reference)
        if not match:
            raise ComposeContractError(f"{service} image must use image@sha256:<digest>")
        if match.group("digest") != expected_digest:
            raise ComposeContractError(f"{service} image digest does not match expected digest")
    if odoo_image_ref != nginx_image_ref:
        raise ComposeContractError("Odoo and Nginx must use the same manifest image revision")
    if manifest.get("image_digest") != expected_digest:
        raise ComposeContractError("release manifest and Compose digest differ")
    if manifest.get("repository") != "lidefend/sce-backend-odoo":
        raise ComposeContractError("release manifest repository is not approved")
    if manifest.get("branch") != "main":
        raise ComposeContractError("release manifest branch must be main")
    if manifest.get("oci_revision") != manifest.get("container_source_revision"):
        raise ComposeContractError("Odoo/Nginx release revision set is inconsistent")
    return {
        "project": project,
        "database": database,
        "image_reference": odoo_image_ref,
        "image_digest": expected_digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--odoo-image-ref", required=True)
    parser.add_argument("--nginx-image-ref", required=True)
    parser.add_argument("--expected-digest", required=True)
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
            nginx_image_ref=args.nginx_image_ref,
            expected_digest=args.expected_digest,
            manifest=manifest,
        )
    except (OSError, json.JSONDecodeError, ComposeContractError) as exc:
        raise SystemExit(f"[production.compose.contract] BLOCKED: {exc}") from exc
    print("[production.compose.contract] PASS " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
