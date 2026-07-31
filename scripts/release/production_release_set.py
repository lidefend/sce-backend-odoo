#!/usr/bin/env python3
"""Validate the external immutable release-set lock used by production tools."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
CHECKSUM = re.compile(r"^[0-9a-f]{64}$")
LEGACY_PATH = Path("/data/odoo/legacy_attachments")
TENANT = re.compile(r"^[a-z][a-z0-9_]{2,62}$")
MODULE = re.compile(r"^[a-z][a-z0-9_]{1,62}$")
XMLID = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
OPERATOR_FIELDS = {
    "identity_type",
    "identity_key",
    "tenant_key",
    "target_group_xmlid",
    "expected_membership_before",
    "expected_membership_after",
    "expected_company_scope",
    "grant_scope_version",
}


class ReleaseSetError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_lock(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_LOCK_INVALID")
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version", "release_version", "product_sha", "product_tree",
        "product_image", "product_image_digest", "customer_sha", "customer_tree",
        "tenant_key", "customer_package", "customer_package_digest", "customer_package_signature_key_id",
        "customer_modules", "payload_root", "payload_version", "payload_digest",
        "payload_schema_version", "target_database", "filestore_scope",
        "legacy_attachments_path", "allowed_entry_contract",
        "operator_contract",
    }
    if not isinstance(payload, dict):
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_SCHEMA_INVALID")
    if "operator_contract" not in payload:
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_OPERATOR_SCHEMA_INVALID")
    if set(payload) != required:
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_SCHEMA_INVALID")
    if payload["schema_version"] != "sce.production_release_set.v2":
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_SCHEMA_INVALID")
    expected_version = (Path(__file__).resolve().parents[2] / "VERSION").read_text().strip()
    if payload["release_version"] != expected_version:
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_VERSION_MISMATCH")
    for name in ("product_sha", "product_tree", "customer_sha", "customer_tree"):
        if not SHA.fullmatch(str(payload[name])):
            raise ReleaseSetError(f"PRODUCTION_RELEASE_SET_{name.upper()}_INVALID")
    if payload["product_image_digest"] != str(payload["product_image"]).partition("@")[2]:
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_IMAGE_REFERENCE_MISMATCH")
    if not DIGEST.fullmatch(str(payload["product_image_digest"])):
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_IMAGE_DIGEST_INVALID")
    for name in ("customer_package_digest", "payload_digest"):
        if not CHECKSUM.fullmatch(str(payload[name])):
            raise ReleaseSetError(f"PRODUCTION_RELEASE_SET_{name.upper()}_INVALID")
    modules = payload["customer_modules"]
    if (
        not TENANT.fullmatch(str(payload["tenant_key"]))
        or not isinstance(modules, list)
        or not modules
        or len(modules) != len(set(modules))
        or any(not MODULE.fullmatch(str(name)) or str(name).endswith("_legacy") for name in modules)
    ):
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_CUSTOMER_MODULES_INVALID")
    if payload["target_database"] != "sc_production" or payload["filestore_scope"] != "sc_production":
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_DATABASE_FILESTORE_MISMATCH")
    if Path(payload["legacy_attachments_path"]) != LEGACY_PATH:
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_LEGACY_PATH_MISMATCH")
    if payload["allowed_entry_contract"] != "production_tenant_delivery.v2":
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_ENTRY_CONTRACT_MISMATCH")
    operator = payload["operator_contract"]
    if not isinstance(operator, dict) or set(operator) != OPERATOR_FIELDS:
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_OPERATOR_SCHEMA_INVALID")
    if (
        operator["identity_type"] != "external_xmlid"
        or not XMLID.fullmatch(str(operator["identity_key"]))
        or not XMLID.fullmatch(str(operator["target_group_xmlid"]))
        or operator["tenant_key"] != payload["tenant_key"]
        or operator["expected_membership_before"] != 0
        or operator["expected_membership_after"] != 1
        or operator["expected_company_scope"] != 1
        or operator["grant_scope_version"] != 1
    ):
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_OPERATOR_CONTRACT_INVALID")
    return payload


def verify_bound_files(payload: dict) -> None:
    package = Path(payload["customer_package"]).resolve()
    payload_root = Path(payload["payload_root"]).resolve()
    legacy = LEGACY_PATH.resolve(strict=False)
    for target in (package, payload_root):
        if target == legacy or legacy in target.parents or target in legacy.parents:
            raise ReleaseSetError("PRODUCTION_RELEASE_SET_LEGACY_PATH_OVERLAP")
    if not package.is_file() or package.is_symlink():
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_CUSTOMER_PACKAGE_MISSING")
    if sha256_file(package) != payload["customer_package_digest"]:
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_CUSTOMER_PACKAGE_DIGEST_MISMATCH")
    checksum = payload_root / "checksums.sha256"
    manifest = payload_root / "manifest.json"
    if not payload_root.is_dir() or payload_root.is_symlink() or not checksum.is_file() or not manifest.is_file():
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_PAYLOAD_MISSING")
    if sha256_file(checksum) != payload["payload_digest"]:
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_PAYLOAD_DIGEST_MISMATCH")
    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    if (
        manifest_payload.get("payload_id") != payload["payload_version"]
        or manifest_payload.get("schema_version") != payload["payload_schema_version"]
        or manifest_payload.get("customer_module") not in payload["customer_modules"]
        or manifest_payload.get("tenant_key") != payload["tenant_key"]
    ):
        raise ReleaseSetError("PRODUCTION_RELEASE_SET_PAYLOAD_IDENTITY_MISMATCH")


def validate_environment(payload: dict) -> None:
    expected = {
        "ENV": "prod",
        "PRODUCTION_COMPOSE_PROJECT": "sc_production",
        "TARGET_DB": "sc_production",
        "EXPECTED_RELEASE_SHA": payload["product_sha"],
        "EXPECTED_IMAGE_DIGEST": payload["product_image_digest"],
        "ODOO_IMAGE_REF": payload["product_image"],
        "NGINX_IMAGE_REF": payload["product_image"],
    }
    for name, value in expected.items():
        if os.environ.get(name) != value:
            raise ReleaseSetError(f"PRODUCTION_RELEASE_SET_ENVIRONMENT_MISMATCH:{name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("validate", "print", "tenant", "modules", "module", "operator-field"),
    )
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--module")
    parser.add_argument("--field", choices=sorted(OPERATOR_FIELDS))
    args = parser.parse_args()
    try:
        payload = load_lock(args.lock.resolve())
        verify_bound_files(payload)
        validate_environment(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, ReleaseSetError) as exc:
        raise SystemExit(f"[production.release-set] BLOCKED: {exc}") from exc
    if args.action == "tenant":
        print(payload["tenant_key"])
    elif args.action == "modules":
        print(",".join(payload["customer_modules"]))
    elif args.action == "module":
        if args.module not in payload["customer_modules"]:
            raise SystemExit("[production.release-set] BLOCKED: module is outside the signed allowlist")
        print(args.module)
    elif args.action == "operator-field":
        if not args.field:
            raise SystemExit("[production.release-set] BLOCKED: --field is required")
        value = payload["operator_contract"][args.field]
        if isinstance(value, bool):
            value = int(value)
        print(value)
    elif args.action == "print":
        print(json.dumps({
            "status": "PASS",
            "release_version": payload["release_version"],
            "product_sha": payload["product_sha"],
            "product_image_digest": payload["product_image_digest"],
            "customer_package_digest": payload["customer_package_digest"],
            "payload_digest": payload["payload_digest"],
            "tenant_key": payload["tenant_key"],
            "customer_modules": payload["customer_modules"],
            "database_write_count": 0,
        }, sort_keys=True))
    else:
        print("[production.release-set] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
