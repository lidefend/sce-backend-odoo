#!/usr/bin/env python3
from pathlib import Path
import tempfile
import unittest

from formal_product_field_purity_guard import scan


class FormalProductFieldPurityGuardTest(unittest.TestCase):
    def test_clean_formal_product_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "addons/smart_construction_core/models/formal.py"
            path.parent.mkdir(parents=True)
            path.write_text("amount = fields.Monetary()\\n", encoding="utf-8")
            self.assertEqual(scan(root), [])

    def test_migration_alias_in_product_source_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "addons/smart_construction_core/views/formal.xml"
            path.parent.mkdir(parents=True)
            path.write_text('<field name="p1_visible_forbidden"/>\\n', encoding="utf-8")
            violations = scan(root)
            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0]["reason_code"], "FORMAL_PRODUCT_LEGACY_ALIAS")

    def test_migration_cleanup_is_not_a_published_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "addons/smart_construction_core/migrations/17.0.0.76/pre-migration.py"
            path.parent.mkdir(parents=True)
            path.write_text("prefix = 'p1_visible_'\\n", encoding="utf-8")
            self.assertEqual(scan(root), [])


if __name__ == "__main__":
    unittest.main()
