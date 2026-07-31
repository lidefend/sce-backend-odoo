#!/usr/bin/env python3
"""Build an immutable external production release-set lock."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

import production_release_set


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_payload(args: argparse.Namespace) -> dict:
    package = args.customer_package.resolve(strict=True)
    package_manifest_path = args.customer_package_manifest.resolve(strict=True)
    try:
        package_manifest = json.loads(package_manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise production_release_set.ReleaseSetError(
            "PRODUCTION_RELEASE_SET_CUSTOMER_MANIFEST_INVALID"
        ) from exc
    payload_root = args.payload_root.resolve(strict=True)
    if args.output.exists() or args.output.is_symlink():
        raise production_release_set.ReleaseSetError("PRODUCTION_RELEASE_SET_OUTPUT_EXISTS")
    return {
        "schema_version": "sce.production_release_set.v4",
        "release_version": args.release_version,
        "product_sha": args.product_sha,
        "product_tree": args.product_tree,
        "product_image": args.product_image,
        "product_image_digest": args.product_image_digest,
        "customer_sha": args.customer_sha,
        "customer_tree": args.customer_tree,
        "tenant_key": args.tenant_key,
        "customer_package": str(package),
        "customer_package_digest": sha256_file(package),
        "customer_package_manifest": str(package_manifest_path),
        "customer_package_manifest_digest": sha256_file(package_manifest_path),
        "customer_package_schema_version": package_manifest.get("schema_version"),
        "customer_package_build_product_sha": package_manifest.get("product_sha"),
        "customer_package_minimum_product_version": package_manifest.get(
            "minimum_product_version"
        ),
        "customer_package_maximum_product_version_exclusive": package_manifest.get(
            "maximum_product_version_exclusive"
        ),
        "customer_package_product_key": args.customer_package_product_key,
        "customer_package_signature_key_id": args.customer_package_signature_key_id,
        "customer_modules": args.customer_module,
        "payload_root": str(payload_root),
        "payload_version": args.payload_version,
        "payload_digest": sha256_file(payload_root / "checksums.sha256"),
        "payload_schema_version": args.payload_schema_version,
        "target_database": args.target_database,
        "filestore_scope": args.filestore_scope,
        "legacy_attachments_path": str(production_release_set.LEGACY_PATH),
        "allowed_entry_contract": "production_tenant_delivery.v4",
        "operator_contract": {
            "identity_type": args.operator_identity_type,
            "identity_key": args.operator_identity_key,
            "tenant_key": args.tenant_key,
            "direct_grant_targets": args.operator_direct_grant_target,
            "importer_transitive_implied_closure": args.operator_transitive_implied_group,
            "required_existing_operator_groups": args.operator_required_existing_group,
            "expected_direct_grant_additions": args.operator_expected_direct_addition,
            "expected_effective_group_additions": args.operator_expected_effective_addition,
            "expected_undeclared_group_additions": [],
            "expected_company_scope": args.operator_expected_company_scope,
            "grant_scope_version": args.operator_grant_scope_version,
        },
    }


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--output", required=True, type=Path)
    result.add_argument("--release-version", required=True)
    result.add_argument("--product-sha", required=True)
    result.add_argument("--product-tree", required=True)
    result.add_argument("--product-image", required=True)
    result.add_argument("--product-image-digest", required=True)
    result.add_argument("--customer-sha", required=True)
    result.add_argument("--customer-tree", required=True)
    result.add_argument("--tenant-key", required=True)
    result.add_argument("--customer-package", required=True, type=Path)
    result.add_argument("--customer-package-manifest", required=True, type=Path)
    result.add_argument(
        "--customer-package-product-key", default="sce-product", choices=("sce-product",)
    )
    result.add_argument("--customer-package-signature-key-id", required=True)
    result.add_argument("--customer-module", required=True, action="append")
    result.add_argument("--payload-root", required=True, type=Path)
    result.add_argument("--payload-version", required=True)
    result.add_argument("--payload-schema-version", required=True)
    result.add_argument("--target-database", default="sc_production")
    result.add_argument("--filestore-scope", default="sc_production")
    result.add_argument("--operator-identity-type", required=True, choices=("external_xmlid",))
    result.add_argument("--operator-identity-key", required=True)
    result.add_argument("--operator-direct-grant-target", required=True, action="append")
    result.add_argument("--operator-transitive-implied-group", action="append", default=[])
    result.add_argument("--operator-required-existing-group", required=True, action="append")
    result.add_argument("--operator-expected-direct-addition", required=True, action="append")
    result.add_argument("--operator-expected-effective-addition", required=True, action="append")
    result.add_argument("--operator-expected-company-scope", type=int, default=1)
    result.add_argument("--operator-grant-scope-version", type=int, default=3)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        payload = build_payload(args)
        temporary_lock = args.output.parent / f".{args.output.name}.validation"
        temporary_lock.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary_lock.write_text(json.dumps(payload), encoding="utf-8")
        os.chmod(temporary_lock, 0o600)
        try:
            checked = production_release_set.load_lock(temporary_lock)
            production_release_set.verify_bound_files(checked)
        finally:
            temporary_lock.unlink(missing_ok=True)
        atomic_write(args.output, payload)
    except (OSError, json.JSONDecodeError, production_release_set.ReleaseSetError) as exc:
        raise SystemExit(f"[production.release-set.build] BLOCKED: {exc}") from exc
    print(json.dumps({
        "status": "PASS",
        "output": str(args.output.resolve()),
        "lock_sha256": sha256_file(args.output),
        "database_write_count": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
