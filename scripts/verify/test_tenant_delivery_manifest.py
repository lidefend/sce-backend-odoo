#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "addons/smart_core/utils/tenant_delivery_manifest.py"
SPEC = importlib.util.spec_from_file_location("tenant_delivery_manifest", MODULE_PATH)
manifest = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(manifest)


class TenantDeliveryManifestTest(unittest.TestCase):
    def test_sample_customer_module_manifest(self):
        payload = json.loads(
            (ROOT / "customer_addons/sce_customer_sample/customer_module_manifest.json").read_text()
        )
        manifest.validate_customer_module_manifest(payload)

    def test_customer_module_requires_tenant_payload_v1(self):
        payload = json.loads(
            (ROOT / "customer_addons/sce_customer_sample/customer_module_manifest.json").read_text()
        )
        payload["payload_manifest_version"] = "sce.customer_payload_manifest.v1"
        with self.assertRaisesRegex(manifest.TenantDeliveryManifestError, "payload manifest version"):
            manifest.validate_customer_module_manifest(payload)

    def test_rejected_payload_declaration_is_strict(self):
        payload = json.loads(
            (ROOT / "customer_addons/sce_customer_sample/customer_module_manifest.json").read_text()
        )
        payload["rejected_payloads"] = [
            {
                "payload_id": "sample-rejected-v1",
                "payload_checksum": "a" * 64,
                "reason_code": "SEMANTIC_CONTRACT_INVALID",
            }
        ]
        manifest.validate_customer_module_manifest(payload)
        payload["rejected_payloads"][0]["reason_code"] = "not-a-stable-code"
        with self.assertRaisesRegex(
            manifest.TenantDeliveryManifestError,
            "rejected payload declaration",
        ):
            manifest.validate_customer_module_manifest(payload)


if __name__ == "__main__":
    unittest.main()
