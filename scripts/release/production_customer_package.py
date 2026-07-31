#!/usr/bin/env python3
"""Fail-closed preparation of one signed customer add-on package."""

from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

import customer_package_preflight as admission
import production_release_set as release_set

CONFIRMATION = "YES_PREPARE_SIGNED_CUSTOMER_PACKAGE"


def validate_package_target_contract(
    lock: dict, manifest: dict, manifest_path: Path, release_config: dict
) -> None:
    if (
        manifest_path.resolve() != Path(lock["customer_package_manifest"]).resolve()
        or admission.sha256_file(manifest_path.resolve())
        != lock["customer_package_manifest_digest"]
        or manifest["schema_version"] != lock["customer_package_schema_version"]
        or manifest["product_sha"] != lock["customer_package_build_product_sha"]
        or manifest["customer_sha"] != lock["customer_sha"]
        or manifest["minimum_product_version"]
        != lock["customer_package_minimum_product_version"]
        or manifest["maximum_product_version_exclusive"]
        != lock["customer_package_maximum_product_version_exclusive"]
        or (manifest.get("signature") or {}).get("key_id")
        != lock["customer_package_signature_key_id"]
    ):
        raise ValueError("CUSTOMER_PACKAGE_BUILD_PROVENANCE_MISMATCH")
    if release_config["product"] != lock["customer_package_product_key"]:
        raise ValueError("CUSTOMER_PACKAGE_TARGET_PRODUCT_IDENTITY_MISMATCH")


def validate_destination(destination: Path) -> Path:
    resolved = destination.resolve()
    legacy = release_set.LEGACY_PATH.resolve(strict=False)
    repository = Path(__file__).resolve().parents[2]
    if (
        resolved == legacy
        or legacy in resolved.parents
        or resolved in legacy.parents
        or resolved == repository
        or repository in resolved.parents
    ):
        raise ValueError("CUSTOMER_PACKAGE_DESTINATION_FORBIDDEN")
    return resolved


def inspect_archive(archive: Path, expected_files: list[dict]) -> None:
    with tarfile.open(archive, "r:gz") as handle:
        members = handle.getmembers()
        if not members:
            raise ValueError("CUSTOMER_PACKAGE_EMPTY")
        for member in members:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or member.issym() or member.islnk() or member.isdev():
                raise ValueError("CUSTOMER_PACKAGE_UNSAFE_MEMBER")
        manifests = [m for m in members if "/addons/" in m.name and m.name.endswith("/__manifest__.py")]
        legacy = [m for m in members if "_legacy" in m.name]
        if not manifests or legacy:
            raise ValueError("CUSTOMER_PACKAGE_MODULE_SET_INVALID")
        observed = []
        for member in members:
            if not member.isfile():
                continue
            extracted = handle.extractfile(member)
            assert extracted is not None
            content = extracted.read()
            observed.append({
                "path": member.name,
                "sha256": admission.hashlib.sha256(content).hexdigest(),
                "size": len(content),
            })
        if observed != expected_files:
            raise ValueError("CUSTOMER_PACKAGE_FILE_MANIFEST_MISMATCH")


def inspect_runtime_contract(
    archive: Path, modules: list[str], tenant_key: str
) -> dict[str, dict]:
    validator = admission.load_module(
        "sce_production_customer_module_contract",
        "addons/smart_core/utils/tenant_delivery_manifest.py",
    )
    contracts: dict[str, dict] = {}
    with tarfile.open(archive, "r:gz") as handle:
        regular = {member.name: member for member in handle.getmembers() if member.isfile()}
        for module in modules:
            suffix = f"/addons/{module}/customer_module_manifest.json"
            matches = [name for name in regular if name.endswith(suffix)]
            manifest_suffix = f"/addons/{module}/__manifest__.py"
            module_manifests = [name for name in regular if name.endswith(manifest_suffix)]
            if len(matches) != 1 or len(module_manifests) != 1:
                raise ValueError("CUSTOMER_PACKAGE_RUNTIME_CONTRACT_MISSING")
            contract_file = handle.extractfile(regular[matches[0]])
            module_file = handle.extractfile(regular[module_manifests[0]])
            if contract_file is None or module_file is None:
                raise ValueError("CUSTOMER_PACKAGE_RUNTIME_CONTRACT_MISSING")
            contract = json.loads(contract_file.read().decode("utf-8"))
            module_manifest = ast.literal_eval(module_file.read().decode("utf-8"))
            validator.validate_customer_module_manifest(contract)
            if (
                contract.get("tenant_key") != tenant_key
                or contract.get("module_name") != module
                or contract.get("module_version")
                != str(module_manifest.get("version") or "")
                or contract.get("product_bundle") != "smart_construction_bundle"
            ):
                raise ValueError("CUSTOMER_PACKAGE_RUNTIME_CONTRACT_MISMATCH")
            contracts[module] = contract
    return contracts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("plan", "apply"))
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--archive-root", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    lock = release_set.load_lock(args.lock.resolve())
    release_set.verify_bound_files(lock)
    release_set.validate_environment(lock)
    archive = admission.archive_from_root(args.archive_root.resolve())
    actual = admission.sha256_file(archive)
    manifest = admission.load_package_manifest(args.manifest.resolve(), actual)
    if manifest["modules"] != lock["customer_modules"] or manifest["tenant_id"] != lock["tenant_key"]:
        raise SystemExit("CUSTOMER_PACKAGE_MODULE_SET_INVALID")
    if actual != lock["customer_package_digest"] or archive.resolve() != Path(lock["customer_package"]).resolve():
        raise SystemExit("CUSTOMER_PACKAGE_RELEASE_SET_MISMATCH")
    if manifest["schema_version"] != admission.PACKAGE_SCHEMA_VERSION_V2:
        raise SystemExit("CUSTOMER_PACKAGE_V2_REQUIRED")
    manifest_path = args.manifest.resolve()
    release_config = admission.load_module(
        "sce_customer_target_release", "scripts/release/product_release.py"
    ).load_release_config()
    try:
        validate_package_target_contract(lock, manifest, manifest_path, release_config)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    inspect_archive(archive, manifest["files"])
    runtime_contracts = inspect_runtime_contract(
        archive, manifest["modules"], manifest["tenant_id"]
    )
    destination = validate_destination(args.destination)
    report = {
        "schema_version": "production_customer_package_plan.v1",
        "status": "PASS",
        "action": args.action,
        "archive_sha256": actual,
        "manifest_sha256": admission.sha256_file(manifest_path),
        "package_build_product_sha": manifest["product_sha"],
        "target_product_sha": lock["product_sha"],
        "target_product_key": lock["customer_package_product_key"],
        "target_product_version": lock["release_version"],
        "target_version_in_compatibility_range": True,
        "runtime_contract_compatible": True,
        "product_bundles": sorted(
            {row["product_bundle"] for row in runtime_contracts.values()}
        ),
        "modules": manifest["modules"],
        "legacy_module_included": False,
        "destination": str(destination),
        "database_write_count": 0,
    }
    if args.action == "apply":
        if os.environ.get("CONFIRM_PRODUCTION_CUSTOMER_PACKAGE") != CONFIRMATION:
            raise SystemExit("CUSTOMER_PACKAGE_APPLY_CONFIRMATION_REQUIRED")
        if destination.exists() or destination.is_symlink():
            raise SystemExit("CUSTOMER_PACKAGE_DESTINATION_MUST_NOT_EXIST")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".customer-package-", dir=destination.parent) as temporary:
            prepared = Path(temporary) / "prepared"
            admission.safe_extract(archive, prepared)
            module_roots = [admission.locate_module_root(prepared, name) for name in lock["customer_modules"]]
            addons_roots = {root.parent for root in module_roots}
            if len(addons_roots) != 1:
                raise SystemExit("CUSTOMER_PACKAGE_EXTRACTED_ADDONS_ROOT_INVALID")
            discovered = {
                path.parent.name
                for path in prepared.rglob("__manifest__.py")
                if path.parent.parent.name == "addons"
            }
            if discovered != set(lock["customer_modules"]):
                raise SystemExit("CUSTOMER_PACKAGE_EXTRACTED_MODULE_SET_INVALID")
            staging = Path(temporary) / "addons"
            shutil.copytree(addons_roots.pop(), staging)
            staging.rename(destination)
        report["prepared_addons_root"] = str(destination)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
