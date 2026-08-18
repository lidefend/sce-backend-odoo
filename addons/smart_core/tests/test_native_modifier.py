# -*- coding: utf-8 -*-
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "utils" / "native_modifier.py"
SPEC = importlib.util.spec_from_file_location("smart_core_native_modifier_test", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class TestNativeModifier(unittest.TestCase):
    def test_odoo_state_comparison_is_normalized(self):
        self.assertEqual(
            MODULE.normalize_native_modifier("state != 'upload'"),
            {
                "kind": "field_compare",
                "field": "state",
                "operator": "!=",
                "value": "upload",
                "raw": "state != 'upload'",
            },
        )

    def test_boolean_composition_is_normalized(self):
        value = MODULE.normalize_native_modifier("state == 'preview' or preview_error_count != 0")
        self.assertEqual(value["kind"], "any")
        self.assertEqual([row["field"] for row in value["exprs"]], ["state", "preview_error_count"])

    def test_field_to_field_comparison_preserves_rhs_identity(self):
        value = MODULE.normalize_native_modifier("completed_count < required_count")

        self.assertEqual(value["field"], "completed_count")
        self.assertEqual(value["operator"], "<")
        self.assertEqual(value["value_field"], "required_count")
        self.assertNotIn("value", value)


if __name__ == "__main__":
    unittest.main()
