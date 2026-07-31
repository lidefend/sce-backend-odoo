#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
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


class NarrowImporterGroupTest(unittest.TestCase):
    def test_importer_has_no_implied_data_operator(self):
        expression = guard.importer_implied_expression()
        self.assertEqual(expression.replace(" ", ""), "[(5,0,0)]")
        self.assertNotIn("group_smart_core_data_operator", expression)

    def test_importer_acl_set_is_exact(self):
        self.assertEqual(guard.importer_acls(), guard.ALLOWED_ACLS)

    def test_signed_entry_requires_unforgeable_maintenance_capability(self):
        source = (
            ROOT
            / "addons/smart_core/models/tenant_payload_import_batch.py"
        ).read_text(encoding="utf-8")
        self.assertIn("TPV1_SIGNED_IMPORT_CONTEXT_REQUIRED", source)
        self.assertIn(
            "TPV1_SIGNED_MAINTENANCE_CAPABILITY_REQUIRED", source
        )
        self.assertIn("hashlib.compare_digest", source)

    def test_operator_contract_rejects_data_operator(self):
        source = (
            ROOT / "scripts/tenant_payload/provision_operator.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            'DATA_OPERATOR_XMLID = "smart_core.group_smart_core_data_operator"',
            source,
        )
        self.assertIn(
            "TPV1_IMPORT_OPERATOR_DATA_OPERATOR_FORBIDDEN", source
        )
        self.assertIn(
            "TPV1_IMPORT_OPERATOR_REQUIRED_EXISTING_GROUP_MISSING", source
        )


if __name__ == "__main__":
    unittest.main()
