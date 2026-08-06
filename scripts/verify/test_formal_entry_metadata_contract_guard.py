#!/usr/bin/env python3
from pathlib import Path
import shutil
import tempfile
import unittest

from formal_entry_metadata_contract_guard import scan


ROOT = Path(__file__).resolve().parents[2]
FILES = (
    "addons/smart_construction_core/__manifest__.py",
    "addons/smart_construction_core/models/support/formal_entry_metadata_extensions.py",
    "addons/smart_construction_core/migrations/17.0.0.82/post-migration.py",
    "addons/smart_construction_core/views/core/project_list_views.xml",
    "addons/smart_construction_core/views/core/project_views.xml",
    "addons/smart_construction_core/views/core/funding_actual_event_allocation_views.xml",
    "addons/smart_construction_core/views/core/historical_payment_fact_views.xml",
    "addons/smart_construction_core/views/core/tax_certificate_registration_views.xml",
    "addons/smart_construction_core/views/support/tender_views.xml",
    "scripts/verify/formal_entry_metadata_audit.py",
)


class FormalEntryMetadataContractGuardTest(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        for relative in FILES:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        self.addCleanup(temporary.cleanup)
        return root

    def test_current_contract_passes(self):
        self.assertEqual(scan(self.fixture()), [])

    def test_missing_model_extension_fails(self):
        root = self.fixture()
        path = root / "addons/smart_construction_core/models/support/formal_entry_metadata_extensions.py"
        path.write_text(path.read_text(encoding="utf-8").replace('    "project.project",\n', ""), encoding="utf-8")
        self.assertIn("missing_formal_entry_metadata_extension", {row["reason"] for row in scan(root)})

    def test_missing_visible_pair_fails(self):
        root = self.fixture()
        path = root / "addons/smart_construction_core/views/core/project_list_views.xml"
        path.write_text(path.read_text(encoding="utf-8").replace("source_created_at", "source_time_removed"), encoding="utf-8")
        self.assertIn("missing_visible_entry_metadata_field", {row["reason"] for row in scan(root)})

    def test_destructive_fact_cleanup_fails(self):
        root = self.fixture()
        path = root / "addons/smart_construction_core/migrations/17.0.0.82/post-migration.py"
        path.write_text(path.read_text(encoding="utf-8") + "\n# DROP TABLE sc_legacy_invoice_analysis_report_fact\n", encoding="utf-8")
        self.assertIn("business_data_destructive_cleanup", {row["reason"] for row in scan(root)})

    def test_missing_active_orphan_guard_fails(self):
        root = self.fixture()
        path = root / "scripts/verify/formal_entry_metadata_audit.py"
        path.write_text(path.read_text(encoding="utf-8").replace("active_unresolved_model_errors(env", "removed_guard(env"), encoding="utf-8")
        self.assertIn("missing_active_orphan_fail_closed_guard", {row["reason"] for row in scan(root)})


if __name__ == "__main__":
    unittest.main()
