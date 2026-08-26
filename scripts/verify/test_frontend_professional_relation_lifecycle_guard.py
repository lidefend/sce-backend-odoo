import unittest
from pathlib import Path
from scripts.verify.frontend_professional_relation_lifecycle_guard import validate

ROOT = Path(__file__).resolve().parents[2]

class ProfessionalRelationLifecycleGuardTests(unittest.TestCase):
    def test_current_sources_pass(self): self.assertEqual(validate(), [])
    def test_producer_bypass_fails(self):
        def read_text(path): return (ROOT / path).read_text(encoding="utf-8").replace("buildProfessionalRelationCreatedMessage", "legacyCreatedMessage") if path.endswith("useCreatedRecordNavigationRuntime.ts") else (ROOT / path).read_text(encoding="utf-8")
        self.assertTrue(any("producer bypasses" in item for item in validate(read_text)))
    def test_missing_exact_once_settlement_fails(self):
        def read_text(path): return (ROOT / path).read_text(encoding="utf-8").replace("settleProfessionalRelationLifecycle", "legacySettlement") if path.endswith("relationCreateDialogRuntime.ts") else (ROOT / path).read_text(encoding="utf-8")
        self.assertTrue(any("consumer bypasses" in item for item in validate(read_text)))
    def test_legacy_search_control_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace('<ScInput', '<input class="input"') if path.endswith("RelationSearchDialog.vue") else value
        self.assertTrue(any("relation search presentation" in item for item in validate(read_text)))
    def test_missing_result_semantics_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace('role="listbox"', 'role="group"') if path.endswith("RelationSearchDialog.vue") else value
        self.assertTrue(any("role=\"listbox\"" in item for item in validate(read_text)))
    def test_direct_primitive_token_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return value + "\n.fixture{gap:var(--sc-space-xs)}\n" if path.endswith("RelationSearchDialog.css") else value
        self.assertTrue(any("directly consumes primitive" in item for item in validate(read_text)))

if __name__ == "__main__": unittest.main()
