# -*- coding: utf-8 -*-
import importlib.util
import json
import sys
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
                "semantics": "python",
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

    def test_unknown_branch_invalidates_whole_expression(self):
        for raw in ("state == 'draft' or context.get('show_warning')",
                    "state == 'draft' and len(ids)", "not context.get('show_warning')",
                    "amount > compute_limit()", "state in [other_state]", "state ==",
                    "source().active", "state == source().state", "ids == (1, 2)",
                    "ids in [(1, 2)]", "amount == 1e999", "amount == 9007199254740992", r"state == '\ud83d'"):
            with self.subTest(raw=raw):
                value = MODULE.normalize_native_modifier(raw)
                self.assertEqual(value["kind"], "unsupported")
                self.assertEqual(value["raw"], raw)

    def test_domain_prefix_and_implicit_conjunction_preserve_all_operands(self):
        value = MODULE.normalize_native_modifier(["|", ("state", "=", "draft"), ("amount", ">", 0), ("active", "=", True)])
        self.assertEqual(value["kind"], "all")
        self.assertEqual(value["exprs"][0]["kind"], "any")
        self.assertEqual(value["exprs"][1]["field"], "active")

    def test_invalid_domain_is_never_partially_accepted(self):
        for raw in (["|", ("state", "=", "draft")],
                    [("state", "=", "draft"), "unknown"],
                    ["!"], [("id", "child_of", 3)],
                    ["|", ("state", "=", "draft"), ("id", "bad", 1)]):
            with self.subTest(raw=raw):
                self.assertEqual(MODULE.normalize_native_modifier(raw)["kind"], "unsupported")

    def test_signed_literal_and_numeric_zero(self):
        self.assertEqual(MODULE.normalize_native_modifier("amount >= -1")["value"], -1)
        self.assertIs(MODULE.normalize_native_modifier(0), False)


def differential_cases():
    # Load the same real assembler through the existing isolated Odoo fixture loader.
    spec = importlib.util.spec_from_file_location("modifier_assembler_fixture", MODULE_PATH.parents[1] / "tests" / "test_unified_page_contract_v2_mobile_compact.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    cases = []
    for value in ([], [1], {}, {"id": 1}, False, None, 0, 1, "", "draft"):
        for raw in ("ids", "not ids", "ids or active", "ids and active"):
            record = {"ids": value, "active": True}
            node = MODULE.normalize_native_modifier(raw)
            native = eval(raw, {"__builtins__": {}}, record)  # Test-only fixed expressions; never user input.
            expected = bool(native)
            actual = fixture.assembler._evaluate_action_modifier(node, record, strict=True)
            assert actual is expected, (raw, record, actual, expected)
            cases.append({"node": node, "record": record, "expected": expected})
    for state, amount, active in (("draft", 0, True), ("posted", 2, True), ("posted", 0, True), ("draft", 2, False)):
        raw = ["&", "|", ("state", "=", "draft"), ("amount", ">", 0), "!", ("active", "=", False)]
        node = MODULE.normalize_native_modifier(raw)
        record = {"state": state, "amount": amount, "active": active}
        expected = (state == "draft" or amount > 0) and active
        assert fixture.assembler._evaluate_action_modifier(node, record, strict=True) is expected
        cases.append({"node": node, "record": record, "expected": expected})
    for raw, expected in (("'false'", True), ("''", False), ("42", True), ("None", False)):
        node = MODULE.normalize_native_modifier(raw)
        assert fixture.assembler._evaluate_action_modifier(node, {}, strict=True) is expected
        cases.append({"node": node, "record": {}, "expected": expected})
    # Python itself is the reference; no expected result is inferred from either implementation.
    values = [None, False, True, 0, 1, 1.5, "", "0", "draft", "ra", "\ue000", "\U00010000",
              [], [1], [1, 2], [1, "x"], [None], [[1]], {}, {"draft": 1}, {"draft": True}]
    for left in values:
        for right in values:
            for operator in ("==", "!=", ">", ">=", "<", "<=", "in", "not in"):
                raw = f"left {operator} right"
                record = {"left": left, "right": right}
                node = MODULE.normalize_native_modifier(raw)
                try:
                    expected = eval(raw, {"__builtins__": {}}, record)
                except TypeError:
                    expected = None
                actual = fixture.assembler._evaluate_action_modifier(node, record, strict=True)
                assert actual is expected, (raw, record, actual, expected)
                cases.append({"node": node, "record": record, "expected": expected})
    for raw, record, expected in [
        ("state in ('draft', 'posted')", {"state": "draft"}, True),
        ("ids == [1, 2]", {"ids": [1, 2]}, True),
        ("ids != [1, 2]", {"ids": [1, 3]}, True),
    ]:
        node = MODULE.normalize_native_modifier(raw)
        assert fixture.assembler._evaluate_action_modifier(node, record, strict=True) is expected
        cases.append({"node": node, "record": record, "expected": expected})
    for record in ({"left": "\ud83d", "right": "😀"},
                   {"left": "x", "right": {"\ude00": 1}},
                   {"left": 9007199254740992, "right": 1}):
        node = MODULE.normalize_native_modifier("left in right")
        assert fixture.assembler._evaluate_action_modifier(node, record, strict=True) is None
        cases.append({"node": node, "record": record, "expected": None})
    for node, record in [
        (MODULE.normalize_native_modifier("state == 'draft' or context.get('x')"), {"state": "draft"}),
        ({"kind": "not", "expr": {"kind": "unknown"}}, {}),
        ({"kind": "static", "value": "false"}, {}),
        ({"kind": "field_compare", "semantics": "unknown", "field": "state", "operator": "==", "value": "draft"}, {"state": "draft"}),
        ({"kind": "not", "expr": ""}, {}),
        ({"kind": "any", "exprs": [True, ""]}, {}),
        ({"kind": "any", "exprs": [True, {"kind": "field_truthy", "field": "missing"}]}, {}),
        ({"kind": "all", "exprs": [False, {"kind": "unknown"}]}, {}),
        ({"kind": "field_compare", "field": "state", "operator": "==", "value_field": "missing"}, {"state": "draft"}),
    ]:
        assert fixture.assembler._evaluate_action_modifier(node, record, strict=True) is None
        cases.append({"node": node, "record": record, "expected": None})
    return cases


if __name__ == "__main__":
    if "--emit-differential" in sys.argv:
        print(json.dumps(differential_cases()))
    else:
        unittest.main()
