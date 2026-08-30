import unittest
from pathlib import Path

from scripts.verify.frontend_form_header_action_primitives_guard import validate

ROOT = Path(__file__).resolve().parents[2]


class FormHeaderActionPrimitivesGuardTests(unittest.TestCase):
    def test_current_sources_pass(self):
        self.assertEqual(validate(), [])

    def test_private_action_button_fails(self):
        def read_text(path: str) -> str:
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace("<ScButton v-if=\"showReturn\"", "<button v-if=\"showReturn\"", 1)

        self.assertTrue(any("shared ScButton" in error or "status step" in error for error in validate(read_text)))

    def test_status_step_cannot_regress_to_private_button(self):
        def read_text(path: str) -> str:
            return (ROOT / path).read_text(encoding="utf-8").replace("<ScSteps", "<ol", 1)

        self.assertTrue(any("status step" in error for error in validate(read_text)))

    def test_action_event_authority_fails(self):
        def read_text(path: str) -> str:
            return (ROOT / path).read_text(encoding="utf-8").replace("'save-draft'", "'legacy-save'")

        self.assertTrue(any("event authority" in error for error in validate(read_text)))

    def test_action_evidence_fails(self):
        def read_text(path: str) -> str:
            return (ROOT / path).read_text(encoding="utf-8").replace('data-product-primary-action', 'data-legacy-primary-action')

        self.assertTrue(any("action evidence" in error for error in validate(read_text)))

    def test_destructive_variant_fails(self):
        def read_text(path: str) -> str:
            return (ROOT / path).read_text(encoding="utf-8").replace("action.destructive ? 'danger'", "action.destructive ? 'ghost'")

        self.assertTrue(any("destructive" in error for error in validate(read_text)))


if __name__ == "__main__":
    unittest.main()
