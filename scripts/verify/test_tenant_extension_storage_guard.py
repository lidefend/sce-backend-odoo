#!/usr/bin/env python3

import tempfile
import unittest
from pathlib import Path

from tenant_extension_storage_guard import scan


class TestTenantExtensionStorageGuard(unittest.TestCase):
    def _root(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "addons/smart_core/model").mkdir(parents=True)
        (root / "addons/smart_core/core").mkdir(parents=True)
        (root / "scripts/tenant_payload").mkdir(parents=True)
        (root / "addons/smart_core/model/ui_tenant_extension_field.py").write_text(
            """
_name = "ui.tenant.extension.field"
_name = "ui.tenant.extension.value"
company_id database_scope boolean_is_set integer_value monetary_value date_value relation_record_id
@tools.ormcache("company_id", "user_id", "schema_version")
""",
            encoding="utf-8",
        )
        (root / "addons/smart_core/core/view_orchestrator.py").write_text(
            'out["tenant_extension_fields"] = rows\n',
            encoding="utf-8",
        )
        (root / "scripts/tenant_payload/tenant_extension_migration_plan.py").write_text(
            'parser.add_argument("--mode", default="dry-run")\n',
            encoding="utf-8",
        )
        return temp, root

    def test_clean_carrier_passes(self):
        temp, root = self._root()
        self.addCleanup(temp.cleanup)
        self.assertEqual(scan(root)["result"], "PASS")

    def test_public_column_declaration_fails(self):
        temp, root = self._root()
        self.addCleanup(temp.cleanup)
        path = root / "addons/smart_core/model/customer.py"
        path.write_text("x_custom_field = fields.Char()\n", encoding="utf-8")
        report = scan(root)
        self.assertEqual(report["result"], "FAIL")
        self.assertEqual(report["public_custom_physical_column_declarations"], 1)

    def test_dynamic_global_field_registration_fails(self):
        temp, root = self._root()
        self.addCleanup(temp.cleanup)
        path = root / "addons/smart_core/model/customer.py"
        path.write_text('env["ir.model.fields"].create(values)\n', encoding="utf-8")
        report = scan(root)
        self.assertEqual(report["result"], "FAIL")
        self.assertEqual(report["dynamic_global_custom_fields"], 1)


if __name__ == "__main__":
    unittest.main()
