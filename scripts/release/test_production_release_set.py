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


class ReleaseSetTest(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, dict]:
        package = root / "customer.tar.gz"
        package.write_bytes(b"customer")
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
            "schema_version": "sce.production_release_set.v2",
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
            "customer_package_signature_key_id": "release-key",
            "customer_modules": ["sce_customer_sample"],
            "payload_root": str(payload_root),
            "payload_version": "sample-locked-v4",
            "payload_digest": hashlib.sha256((payload_root / "checksums.sha256").read_bytes()).hexdigest(),
            "payload_schema_version": "tenant_payload_v1",
            "target_database": "sc_production",
            "filestore_scope": "sc_production",
            "legacy_attachments_path": "/data/odoo/legacy_attachments",
            "allowed_entry_contract": "production_tenant_delivery.v2",
            "operator_contract": {
                "identity_type": "external_xmlid",
                "identity_key": "base.user_admin",
                "tenant_key": "sample_tenant",
                "target_group_xmlid": "smart_core.group_smart_core_tenant_payload_importer",
                "expected_membership_before": 0,
                "expected_membership_after": 1,
                "expected_company_scope": 1,
                "grant_scope_version": 1,
            },
        }
        lock = root / "lock.json"
        lock.write_text(json.dumps(data))
        return lock, data

    def test_valid_lock_and_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock, _ = self.fixture(Path(temporary))
            payload = target.load_lock(lock)
            target.verify_bound_files(payload)

    def test_legacy_module_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            lock, data = self.fixture(Path(temporary))
            data["customer_modules"].append("sce_customer_sample_legacy")
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
                "customer_package_signature_key_id": data["customer_package_signature_key_id"],
                "customer_module": data["customer_modules"],
                "payload_root": Path(data["payload_root"]),
                "payload_version": data["payload_version"],
                "payload_schema_version": data["payload_schema_version"],
                "target_database": data["target_database"],
                "filestore_scope": data["filestore_scope"],
                "operator_identity_type": data["operator_contract"]["identity_type"],
                "operator_identity_key": data["operator_contract"]["identity_key"],
                "operator_target_group_xmlid": data["operator_contract"]["target_group_xmlid"],
                "operator_expected_membership_before": 0,
                "operator_expected_membership_after": 1,
                "operator_expected_company_scope": 1,
                "operator_grant_scope_version": 1,
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
            data["operator_contract"]["expected_membership_after"] = 2
            lock.write_text(json.dumps(data))
            with self.assertRaisesRegex(target.ReleaseSetError, "OPERATOR_CONTRACT"):
                target.load_lock(lock)

    def test_customer_archive_rejects_legacy_module(self):
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
            with self.assertRaises(ValueError):
                customer_package.inspect_archive(archive, expected)


if __name__ == "__main__":
    unittest.main()
