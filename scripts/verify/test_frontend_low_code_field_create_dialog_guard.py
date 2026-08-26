import unittest
from pathlib import Path

from scripts.verify.frontend_low_code_field_create_dialog_guard import validate

ROOT = Path(__file__).resolve().parents[2]


class LowCodeFieldCreateDialogGuardTests(unittest.TestCase):
    def test_current_sources_pass(self):
        self.assertEqual(validate(), [])

    def test_private_control_fails(self):
        def read_text(path: str) -> str:
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace("<ScInput", "<input") if path.endswith(".vue") else value

        self.assertTrue(any("private native controls" in error for error in validate(read_text)))

    def test_event_authority_fails(self):
        def read_text(path: str) -> str:
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace("'update:ttype'", "'legacy-type'") if path.endswith(".vue") else value

        self.assertTrue(any("event authority" in error for error in validate(read_text)))

    def test_field_type_option_fails(self):
        def read_text(path: str) -> str:
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace("{ value: 'datetime',", "{ value: 'date',") if path.endswith(".vue") else value

        self.assertTrue(any("field type options" in error for error in validate(read_text)))

    def test_multiple_primary_actions_fail(self):
        def read_text(path: str) -> str:
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace('variant="ghost"', 'variant="primary"') if path.endswith(".vue") else value

        self.assertTrue(any("exactly one primary" in error for error in validate(read_text)))

    def test_legacy_styling_fails(self):
        def read_text(path: str) -> str:
            value = (ROOT / path).read_text(encoding="utf-8")
            return value + "\n.contract-mode-fixture {}\n" if path.endswith(".css") else value

        self.assertTrue(any("legacy prompt styling" in error for error in validate(read_text)))


if __name__ == "__main__":
    unittest.main()
