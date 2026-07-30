#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("field_architecture_purity_audit.py")
SPEC = importlib.util.spec_from_file_location("field_architecture_purity_audit", MODULE_PATH)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class FieldArchitecturePurityAuditTest(unittest.TestCase):
    def test_runtime_snapshot_requires_exact_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fields.psv"
            path.write_text("model|name|label|char|base|f|module|false\n", encoding="utf-8")
            rows = AUDIT.parse_runtime_fields(path)
        self.assertEqual(rows[0]["model"], "model")
        self.assertFalse(rows[0]["store"])
        self.assertFalse(rows[0]["database_column_exists"])

    def test_alias_identity_is_stable(self):
        self.assertEqual(AUDIT.alias_name("金额"), "p1_visible_34943c40c9af")

    def test_all_source_aliases_have_formal_targets(self):
        aliases = AUDIT.source_aliases()
        self.assertGreater(len(aliases), 700)
        unresolved = [identity for identity, row in aliases.items() if not row["formal_sources"]]
        self.assertEqual(unresolved, [])

    def test_isolation_matrix_fails_definition_not_values(self):
        rows = AUDIT.isolation_rows({"database_role": "isolated_uat"})
        results = {row["case"]: row["result"] for row in rows}
        self.assertEqual(results["CROSS_CUSTOMER_FIELD_DEFINITION_ISOLATION"], "PASS")
        self.assertEqual(results["INTRA_TENANT_COMPANY_FIELD_DEFINITION"], "FAIL")
        self.assertEqual(results["VIEW_CONTRACT_ISOLATION"], "FAIL")
        self.assertEqual(results["VALUE_ISOLATION"], "PASS")


if __name__ == "__main__":
    unittest.main()
