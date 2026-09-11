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

        self.assertTrue(any("shared ScButton" in error or "selection status" in error for error in validate(read_text)))

    def test_status_select_cannot_regress_to_private_control(self):
        def read_text(path: str) -> str:
            return (ROOT / path).read_text(encoding="utf-8").replace("<ScSelect", "<select", 1)

        self.assertTrue(any("selection status" in error for error in validate(read_text)))

    def test_selection_status_cannot_regress_to_steps(self):
        def read_text(path: str) -> str:
            return (ROOT / path).read_text(encoding="utf-8") + "\n<ScSteps />\n"

        self.assertTrue(any("ordered workflow" in error for error in validate(read_text)))

    def test_steps_cannot_patch_vendor_internal_dom(self):
        def read_text(path: str) -> str:
            value = (ROOT / path).read_text(encoding="utf-8")
            return value + "\n<style scoped>:deep(.t-steps-item__title) { white-space: nowrap; }</style>\n" if path.endswith("ScSteps.vue") else value

        self.assertTrue(any("internal DOM" in error for error in validate(read_text)))

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
