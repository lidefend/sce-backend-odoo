#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import io
import json
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import production_release_set as target
import build_production_release_set as builder
import production_customer_package as customer_package


ROOT = Path(__file__).resolve().parents[2]
SAMPLE_CUSTOMER_MODULE = ROOT / "customer_addons" / "sce_customer_sample"


class ReleaseSetTest(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, dict]:
        package = root / "customer.tar.gz"
        package.write_bytes(b"customer")
        package_manifest = root / "customer-package.json"
        payload_root = root / "payload"
        payload_root.mkdir()
        (payload_root / "checksums.sha256").write_bytes(b"checksums")
        (payload_root / "manifest.json").write_text(json.dumps({
            "payload_id": "sample-locked-v4",
            "schema_version": "tenant_payload_v1",
            "customer_module": "sce_customer_sample",
            "tenant_key": "sample_tenant",
        }))
        data = {
            "schema_version": "sce.production_release_set.v4",
            "release_version": (Path(__file__).resolve().parents[2] / "VERSION").read_text().strip(),
            "product_sha": "a" * 40,
            "product_tree": "b" * 40,
            "product_image": "ghcr.io/lidefend/sce-product@sha256:" + "c" * 64,
            "product_image_digest": "sha256:" + "c" * 64,
            "customer_sha": "d" * 40,
            "customer_tree": "e" * 40,
            "tenant_key": "sample_tenant",
            "customer_package": str(package),
            "customer_package_digest": hashlib.sha256(package.read_bytes()).hexdigest(),
            "customer_package_manifest": str(package_manifest),
            "customer_package_manifest_digest": "",
            "customer_package_schema_version": "sce.tenant_customer_addon_package.v2",
            "customer_package_build_product_sha": "f" * 40,
            "customer_package_minimum_product_version": "1.0.0-rc.6",
            "customer_package_maximum_product_version_exclusive": "2.0.0",
            "customer_package_product_key": "sce-product",
            "customer_package_signature_key_id": "release-key",
            "customer_modules": ["sce_customer_sample"],
            "payload_root": str(payload_root),
            "payload_version": "sample-locked-v4",
            "payload_digest": hashlib.sha256((payload_root / "checksums.sha256").read_bytes()).hexdigest(),
            "payload_schema_version": "tenant_payload_v1",
            "target_database": "sc_production",
            "filestore_scope": "sc_production",
            "legacy_attachments_path": "/data/odoo/legacy_attachments",
            "allowed_entry_contract": "production_tenant_delivery.v4",
            "operator_contract": {
                "identity_type": "external_xmlid",
                "identity_key": "base.user_admin",
                "tenant_key": "sample_tenant",
                "direct_grant_targets": ["smart_core.group_smart_core_tenant_payload_importer"],
                "importer_transitive_implied_closure": [],
                "required_existing_operator_groups": ["base.group_user"],
                "expected_direct_grant_additions": ["smart_core.group_smart_core_tenant_payload_importer"],
                "expected_effective_group_additions": ["smart_core.group_smart_core_tenant_payload_importer"],
                "expected_undeclared_group_additions": [],
                "expected_company_scope": 1,
                "grant_scope_version": 3,
            },
        }
        package_manifest.write_text(json.dumps({
            "schema_version": data["customer_package_schema_version"],
            "product_sha": data["customer_package_build_product_sha"],
            "customer_sha": data["customer_sha"],
            "minimum_product_version": data["customer_package_minimum_product_version"],
            "maximum_product_version_exclusive": data["customer_package_maximum_product_version_exclusive"],
            "archive_sha256": data["customer_package_digest"],
            "tenant_id": data["tenant_key"],
            "modules": data["customer_modules"],
            "signature": {"algorithm": "ed25519", "key_id": data["customer_package_signature_key_id"], "value": "signed"},
        }))
        data["customer_package_manifest_digest"] = hashlib.sha256(
            package_manifest.read_bytes()
        ).hexdigest()
        lock = root / "lock.json"
        lock.write_text(json.dumps(data))
        return lock, data

    def test_valid_lock_and_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock, _ = self.fixture(Path(temporary))
            payload = target.load_lock(lock)
            target.verify_bound_files(payload)

    def test_signed_tenant_history_module_is_allowed(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock, data = self.fixture(Path(temporary))
            data["customer_modules"].append("sce_customer_sample_legacy")
            lock.write_text(json.dumps(data))
            self.assertEqual(
                target.load_lock(lock)["customer_modules"],
                ["sce_customer_sample", "sce_customer_sample_legacy"],
            )

    def test_cross_tenant_customer_extension_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock, data = self.fixture(Path(temporary))
            data["customer_modules"].append("sce_customer_other_legacy")
            lock.write_text(json.dumps(data))
            with self.assertRaises(target.ReleaseSetError):
                target.load_lock(lock)

    def test_payload_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock, data = self.fixture(Path(temporary))
            Path(data["payload_root"], "checksums.sha256").write_bytes(b"changed")
            with self.assertRaises(target.ReleaseSetError):
                target.verify_bound_files(target.load_lock(lock))

    def test_environment_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock, _ = self.fixture(Path(temporary))
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(target.ReleaseSetError):
                    target.validate_environment(target.load_lock(lock))

    def test_wrong_database_and_filestore_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock, data = self.fixture(Path(temporary))
            data["target_database"] = "wrong_database"
            lock.write_text(json.dumps(data))
            with self.assertRaises(target.ReleaseSetError):
                target.load_lock(lock)

    def test_builder_writes_valid_immutable_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock, data = self.fixture(root)
            lock.unlink()
            args = type("Args", (), {
                "output": lock,
                "release_version": data["release_version"],
                "product_sha": data["product_sha"],
                "product_tree": data["product_tree"],
                "product_image": data["product_image"],
                "product_image_digest": data["product_image_digest"],
                "customer_sha": data["customer_sha"],
                "customer_tree": data["customer_tree"],
                "tenant_key": data["tenant_key"],
                "customer_package": Path(data["customer_package"]),
                "customer_package_manifest": Path(data["customer_package_manifest"]),
                "customer_package_product_key": data["customer_package_product_key"],
                "customer_package_signature_key_id": data["customer_package_signature_key_id"],
                "customer_module": data["customer_modules"],
                "payload_root": Path(data["payload_root"]),
                "payload_version": data["payload_version"],
                "payload_schema_version": data["payload_schema_version"],
                "target_database": data["target_database"],
                "filestore_scope": data["filestore_scope"],
                "operator_identity_type": data["operator_contract"]["identity_type"],
                "operator_identity_key": data["operator_contract"]["identity_key"],
                "operator_direct_grant_target": data["operator_contract"]["direct_grant_targets"],
                "operator_transitive_implied_group": data["operator_contract"]["importer_transitive_implied_closure"],
                "operator_required_existing_group": data["operator_contract"]["required_existing_operator_groups"],
                "operator_expected_direct_addition": data["operator_contract"]["expected_direct_grant_additions"],
                "operator_expected_effective_addition": data["operator_contract"]["expected_effective_group_additions"],
                "operator_expected_company_scope": 1,
                "operator_grant_scope_version": 3,
            })()
            payload = builder.build_payload(args)
            builder.atomic_write(lock, payload)
            self.assertEqual(lock.stat().st_mode & 0o777, 0o600)
            target.verify_bound_files(target.load_lock(lock))
            with self.assertRaises(target.ReleaseSetError):
                builder.build_payload(args)

    def test_customer_archive_accepts_exact_files_and_rejects_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "package.tar.gz"
            content = b"{}"
            with tarfile.open(archive, "w:gz") as handle:
                info = tarfile.TarInfo("package/addons/sce_customer_sample/__manifest__.py")
                info.size = len(content)
                handle.addfile(info, io.BytesIO(content))
            expected = [{
                "path": "package/addons/sce_customer_sample/__manifest__.py",
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            }]
            customer_package.inspect_archive(archive, expected)
            with tarfile.open(archive, "w:gz") as handle:
                info = tarfile.TarInfo("../escape")
                info.size = len(content)
                handle.addfile(info, io.BytesIO(content))
            with self.assertRaises(ValueError):
                customer_package.inspect_archive(archive, expected)

    def test_signed_archive_runtime_contract_targets_product_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "customer.tar.gz"
            with tarfile.open(archive, "w:gz") as handle:
                handle.add(
                    SAMPLE_CUSTOMER_MODULE,
                    arcname="package/addons/sce_customer_sample",
                )
            contracts = customer_package.inspect_runtime_contract(
                archive, ["sce_customer_sample"], "sample"
            )
            self.assertEqual(
                "smart_construction_bundle",
                contracts["sce_customer_sample"]["product_bundle"],
            )
            with self.assertRaisesRegex(ValueError, "RUNTIME_CONTRACT_MISMATCH"):
                customer_package.inspect_runtime_contract(
                    archive, ["sce_customer_sample"], "wrong_tenant"
                )

    def test_package_build_sha_is_provenance_not_target_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock_path, data = self.fixture(Path(temporary))
            lock = target.load_lock(lock_path)
            manifest_path = Path(data["customer_package_manifest"])
            manifest = json.loads(manifest_path.read_text())
            self.assertNotEqual(manifest["product_sha"], lock["product_sha"])
            customer_package.validate_package_target_contract(
                lock,
                manifest,
                manifest_path,
                {"product": "sce-product"},
            )

    def test_manifest_digest_and_target_product_mismatch_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock_path, data = self.fixture(Path(temporary))
            lock = target.load_lock(lock_path)
            manifest_path = Path(data["customer_package_manifest"])
            manifest = json.loads(manifest_path.read_text())
            with self.assertRaisesRegex(ValueError, "TARGET_PRODUCT_IDENTITY"):
                customer_package.validate_package_target_contract(
                    lock, manifest, manifest_path, {"product": "different-product"}
                )
            manifest["minimum_product_version"] = "1.0.0-rc.7"
            with self.assertRaisesRegex(ValueError, "BUILD_PROVENANCE"):
                customer_package.validate_package_target_contract(
                    lock, manifest, manifest_path, {"product": "sce-product"}
                )

    def test_manifest_file_tamper_is_rejected_by_release_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock_path, data = self.fixture(Path(temporary))
            manifest_path = Path(data["customer_package_manifest"])
            manifest = json.loads(manifest_path.read_text())
            manifest["maximum_product_version_exclusive"] = "3.0.0"
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(
                target.ReleaseSetError, "CUSTOMER_MANIFEST_DIGEST_MISMATCH"
            ):
                target.verify_bound_files(target.load_lock(lock_path))

    def test_out_of_range_target_version_and_old_lock_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock_path, data = self.fixture(Path(temporary))
            data["customer_package_minimum_product_version"] = "2.0.0"
            data["customer_package_maximum_product_version_exclusive"] = "3.0.0"
            lock_path.write_text(json.dumps(data))
            with self.assertRaisesRegex(target.ReleaseSetError, "TARGET_INCOMPATIBLE"):
                target.load_lock(lock_path)
            data["schema_version"] = "sce.production_release_set.v3"
            lock_path.write_text(json.dumps(data))
            with self.assertRaisesRegex(target.ReleaseSetError, "SCHEMA_INVALID"):
                target.load_lock(lock_path)

    def test_operator_contract_is_required_and_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock, data = self.fixture(Path(temporary))
            del data["operator_contract"]
            lock.write_text(json.dumps(data))
            with self.assertRaisesRegex(target.ReleaseSetError, "OPERATOR_SCHEMA"):
                target.load_lock(lock)

    def test_operator_contract_rejects_ambiguous_or_expanded_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock, data = self.fixture(Path(temporary))
            data["operator_contract"]["identity_key"] = "admin"
            lock.write_text(json.dumps(data))
            with self.assertRaisesRegex(target.ReleaseSetError, "OPERATOR_CONTRACT"):
                target.load_lock(lock)
            data["operator_contract"]["identity_key"] = "base.user_admin"
            data["operator_contract"]["expected_effective_group_additions"] = [
                "smart_core.group_smart_core_tenant_payload_importer",
                "smart_core.group_smart_core_data_operator",
            ]
            lock.write_text(json.dumps(data))
            with self.assertRaisesRegex(target.ReleaseSetError, "OPERATOR_CONTRACT"):
                target.load_lock(lock)

    def test_old_operator_scope_contracts_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock, data = self.fixture(Path(temporary))
            for old_scope in (1, 2):
                data["operator_contract"]["grant_scope_version"] = old_scope
                lock.write_text(json.dumps(data))
                with self.assertRaisesRegex(
                    target.ReleaseSetError, "OPERATOR_CONTRACT"
                ):
                    target.load_lock(lock)

    def test_data_operator_and_undeclared_groups_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock, data = self.fixture(Path(temporary))
            data["operator_contract"]["importer_transitive_implied_closure"] = [
                "smart_core.group_smart_core_data_operator"
            ]
            lock.write_text(json.dumps(data))
            with self.assertRaisesRegex(
                target.ReleaseSetError, "OPERATOR_CONTRACT"
            ):
                target.load_lock(lock)
            data["operator_contract"]["importer_transitive_implied_closure"] = []
            data["operator_contract"]["expected_undeclared_group_additions"] = [
                "base.group_portal"
            ]
            lock.write_text(json.dumps(data))
            with self.assertRaisesRegex(
                target.ReleaseSetError, "OPERATOR_CONTRACT"
            ):
                target.load_lock(lock)

    def test_customer_archive_accepts_signed_history_module(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "package.tar.gz"
            content = b"{}"
            path = "package/addons/sce_customer_sample_legacy/__manifest__.py"
            with tarfile.open(archive, "w:gz") as handle:
                info = tarfile.TarInfo(path)
                info.size = len(content)
                handle.addfile(info, io.BytesIO(content))
            expected = [{
                "path": path,
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            }]
            customer_package.inspect_archive(archive, expected)


if __name__ == "__main__":
    unittest.main()
