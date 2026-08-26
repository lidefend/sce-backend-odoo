import unittest
from pathlib import Path

from scripts.verify.frontend_contract_prompt_action_presentation_guard import validate

ROOT = Path(__file__).resolve().parents[2]


class ContractPromptActionPresentationGuardTests(unittest.TestCase):
    def test_current_sources_pass(self):
        self.assertEqual(validate(), [])

    def test_private_native_control_fails(self):
        def read_text(path: str) -> str:
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace("<ScInput", "<input") if path.endswith(".vue") else value

        self.assertTrue(any("private native controls" in item for item in validate(read_text)))

    def test_missing_event_authority_fails(self):
        def read_text(path: str) -> str:
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace("'value-change'", "'legacy-change'") if path.endswith(".vue") else value

        self.assertTrue(any("event authority" in item for item in validate(read_text)))

    def test_multiple_primary_actions_fail(self):
        def read_text(path: str) -> str:
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace('variant="ghost"', 'variant="primary"') if path.endswith(".vue") else value

        self.assertTrue(any("exactly one primary" in item for item in validate(read_text)))

    def test_native_required_projection_fails(self):
        def read_text(path: str) -> str:
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace("required: props.required", "required: undefined") if path.endswith("ScInput.vue") else value

        self.assertTrue(any("native control" in item for item in validate(read_text)))

    def test_primitive_token_consumption_fails(self):
        def read_text(path: str) -> str:
            value = (ROOT / path).read_text(encoding="utf-8")
            return value + "\n.fixture{gap:var(--sc-space-xs)}\n" if path.endswith(".css") else value

        self.assertTrue(any("primitive design tokens" in item for item in validate(read_text)))

    def test_parent_page_grid_integration_fails(self):
        def read_text(path: str) -> str:
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ContractFormPage.css"):
                return value.replace(".action-prompt-form {", ".legacy-prompt-form {")
            return value

        self.assertTrue(any("parent page grid integration" in item for item in validate(read_text)))

    def test_parent_page_grid_column_removal_fails(self):
        def read_text(path: str) -> str:
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ContractFormPage.css"):
                prompt_rule = ".action-prompt-form {\n  grid-column: 1 / -1;"
                return value.replace(prompt_rule, ".action-prompt-form {")
            return value

        self.assertTrue(any("parent page grid integration" in item for item in validate(read_text)))


if __name__ == "__main__":
    unittest.main()
