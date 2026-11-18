"""Static ownership checks for the local native projection audit tool."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "scripts/verify/local_dev_native_projection_audit.py"


class LocalDevNativeProjectionAuditTest(unittest.TestCase):
    def test_standard_and_preview_compatibility_surfaces_must_be_equal(self):
        source = AUDIT.read_text(encoding="utf-8")
        self.assertIn(
            "edition_entries['construction.preview'] == edition_entries['construction.standard']",
            source,
        )
        self.assertIn("assert not preview_only", source)

    def test_audit_requires_nonempty_declared_navigation(self):
        source = AUDIT.read_text(encoding="utf-8")
        self.assertIn("assert observed & declared_ids", source)
        self.assertIn("'observed_declared_count'", source)


if __name__ == "__main__":
    unittest.main()
