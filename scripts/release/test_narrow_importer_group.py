#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "narrow_importer_group_guard",
    ROOT / "scripts/verify/narrow_importer_group_guard.py",
)
guard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(guard)

CAPABILITY_SPEC = importlib.util.spec_from_file_location(
    "tenant_payload_capability",
    ROOT / "addons/smart_core/utils/tenant_payload_capability.py",
)
capability = importlib.util.module_from_spec(CAPABILITY_SPEC)
assert CAPABILITY_SPEC.loader
CAPABILITY_SPEC.loader.exec_module(capability)


class NarrowImporterGroupTest(unittest.TestCase):
    def test_importer_has_empty_implied_closure(self):
        expression = guard.importer_implied_expression()
        self.assertEqual(expression.replace(" ", ""), "[(5,0,0)]")
        self.assertNotIn("group_smart_core_data_operator", expression)

    def test_importer_acl_set_is_exact(self):
        self.assertEqual(guard.importer_acls(), guard.ALLOWED_ACLS)

    def test_signed_entry_compares_maintenance_capability_behavior(self):
        expected = "a" * 64
        self.assertTrue(
            capability.maintenance_capability_matches(expected, expected)
        )
        self.assertFalse(
            capability.maintenance_capability_matches("b" + expected[1:], expected)
        )
        self.assertFalse(
            capability.maintenance_capability_matches("a" * 63, "a" * 63)
        )

    def test_obsolete_hashlib_compare_digest_is_absent(self):
        source = (
            ROOT / "addons/smart_core/models/tenant_payload_import_batch.py"
        ).read_text(encoding="utf-8")
        self.assertIn("TPV1_SIGNED_IMPORT_CONTEXT_REQUIRED", source)
        self.assertIn("TPV1_SIGNED_MAINTENANCE_CAPABILITY_REQUIRED", source)
        tracked = subprocess.run(
            [
                "git",
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
                "--",
                "*.py",
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout.decode("utf-8").split("\0")
        forbidden = "hashlib" + ".compare_digest"
        offenders = []
        for relative in filter(None, tracked):
            path = ROOT / relative
            if forbidden in path.read_text(
                encoding="utf-8", errors="ignore"
            ):
                offenders.append(relative)
        self.assertEqual(offenders, [])

    def test_operator_contract_is_scope_v3_and_rejects_data_operator(self):
        source = (
            ROOT / "scripts/tenant_payload/provision_operator.py"
        ).read_text(encoding="utf-8")
        self.assertIn("grant_scope_version != 3", source)
        self.assertIn("TPV1_IMPORT_OPERATOR_DATA_OPERATOR_FORBIDDEN", source)
        self.assertIn(
            "TPV1_IMPORT_OPERATOR_REQUIRED_EXISTING_GROUP_MISSING", source
        )

    def test_business_model_import_paths_call_signed_boundary(self):
        for relative in (
            "addons/smart_construction_core/models/core/payment_request.py",
            "addons/smart_construction_core/models/core/payment_ledger.py",
            "addons/smart_construction_core/models/core/historical_payment_fact.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(
                'env["sc.tenant.payload.adapter"].assert_import_operator()',
                source,
            )


if __name__ == "__main__":
    unittest.main()
