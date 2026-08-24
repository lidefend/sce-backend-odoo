import unittest
from pathlib import Path
from scripts.verify.frontend_professional_audit_guard import validate

ROOT = Path(__file__).resolve().parents[2]

class ProfessionalAuditGuardTests(unittest.TestCase):
    def test_current_sources_pass(self): self.assertEqual(validate(), [])
    def test_missing_actor_identity_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace("data-audit-actor", "data-marker-removed")
        self.assertTrue(any("audit event missing" in item for item in validate(read_text)))
    def test_special_case_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return value + "\n// payment.request\n" if path.endswith("professionalAuditModel.ts") else value
        self.assertTrue(any("forbidden product special case" in item for item in validate(read_text)))

if __name__ == "__main__": unittest.main()
