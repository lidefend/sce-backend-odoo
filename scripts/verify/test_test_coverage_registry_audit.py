from __future__ import annotations

import unittest

from scripts.verify.test_coverage_registry_audit import (
    STATUS_GATED,
    STATUS_ON_DEMAND,
    STATUS_UNWIRED,
    audit_failures,
    default_entry,
    parse_tagged_declarations,
    tag_token_pattern,
)


def item(group: str, status: str, kind: str = "odoo_tag", declarations: int = 1) -> dict:
    return {
        "group": group,
        "status": status,
        "kind": kind,
        "declarations": declarations,
        "files": [f"addons/smart_core/tests/{group}.py"],
        "owner": "platform-team",
        "evidence": [],
    }


class TaggedDeclarationParsingTest(unittest.TestCase):
    def test_single_line_decorator_binds_class(self) -> None:
        text = (
            '@tagged("post_install", "-at_install", "uc4_native_lowcode")\n'
            "class TestThing(TransactionCase):\n"
            "    pass\n"
        )
        self.assertEqual(
            parse_tagged_declarations(text),
            [
                ("post_install", "TestThing"),
                ("-at_install", "TestThing"),
                ("uc4_native_lowcode", "TestThing"),
            ],
        )

    def test_multiline_decorator_is_parsed(self) -> None:
        """The 2026-10-10 defect: multi-line @tagged(...) was invisible."""
        text = (
            "@tagged(\n"
            '    "post_install",\n'
            '    "-at_install",\n'
            '    "acceptance_fixture_execution_freeze",\n'
            ")\n"
            "class TestFreeze(TransactionCase):\n"
            "    pass\n"
        )
        self.assertIn(
            ("acceptance_fixture_execution_freeze", "TestFreeze"),
            parse_tagged_declarations(text),
        )

    def test_decorator_on_method_has_no_class(self) -> None:
        text = '@tagged("post_install", "relation_entry_override")\ndef test_x(self):\n    pass\n'
        self.assertIn(("relation_entry_override", None), parse_tagged_declarations(text))

    def test_stacked_decorators_still_bind_class(self) -> None:
        text = (
            '@tagged("post_install")\n'
            "@classmethod\n"
            'class TestStacked(TransactionCase):\n'
            "    pass\n"
        )
        self.assertIn(("post_install", "TestStacked"), parse_tagged_declarations(text))


class TagTokenMatchingTest(unittest.TestCase):
    def test_module_qualified_expression_selects_tag(self) -> None:
        pattern = tag_token_pattern("sc_gate")
        self.assertTrue(pattern.search("sc_smoke/${module},sc_gate/${module}"))

    def test_prefix_and_suffix_neighbours_do_not_match(self) -> None:
        pattern = tag_token_pattern("sc_gate")
        self.assertIsNone(pattern.search("sc_smoke"))
        self.assertIsNone(pattern.search("sc_gate_v2"))
        self.assertIsNone(pattern.search("my_sc_gate"))

    def test_bare_tag_still_matches(self) -> None:
        self.assertTrue(tag_token_pattern("sc_perm").search("sc_gate,sc_perm"))


class AuditFailureTest(unittest.TestCase):
    def test_gated_group_needs_no_entry(self) -> None:
        failures = audit_failures([item("sc_gate", STATUS_GATED)], [], {"entries": []})
        self.assertEqual(failures, [])

    def test_undispositioned_unwired_group_fails(self) -> None:
        failures = audit_failures(
            [item("uc4_native_lowcode", STATUS_UNWIRED, declarations=17)],
            [],
            {"entries": []},
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("uc4_native_lowcode", failures[0])
        self.assertIn("not dispositioned", failures[0])

    def test_dispositioned_unwired_group_passes(self) -> None:
        registry = {
            "entries": [
                {
                    "group": "uc4_native_lowcode",
                    "kind": "odoo_tag",
                    "status": STATUS_UNWIRED,
                    "owner": "construction-product",
                    "dispose": "wire-pending",
                    "reason": "no governed selection yet",
                    "review_by": "2026-12-31",
                }
            ]
        }
        self.assertEqual(
            audit_failures([item("uc4_native_lowcode", STATUS_UNWIRED)], [], registry), []
        )

    def test_unwired_entry_without_review_by_fails(self) -> None:
        registry = {
            "entries": [
                {
                    "group": "uc4_native_lowcode",
                    "kind": "odoo_tag",
                    "status": STATUS_UNWIRED,
                    "owner": "construction-product",
                    "dispose": "wire-pending",
                    "reason": "no governed selection yet",
                }
            ]
        }
        failures = audit_failures([item("uc4_native_lowcode", STATUS_UNWIRED)], [], registry)
        self.assertTrue(any("review_by" in failure for failure in failures))

    def test_class_selected_disposition_requires_gate(self) -> None:
        registry = {
            "entries": [
                {
                    "group": "user_feedback",
                    "kind": "odoo_tag",
                    "status": STATUS_ON_DEMAND,
                    "owner": "construction-product",
                    "dispose": "class-selected",
                    "reason": "reached via a class-name make target",
                }
            ]
        }
        failures = audit_failures([item("user_feedback", STATUS_ON_DEMAND)], [], registry)
        self.assertTrue(any("must name its gate" in failure for failure in failures))

    def test_stale_entry_fails(self) -> None:
        registry = {
            "entries": [
                {
                    "group": "removed_group",
                    "kind": "odoo_tag",
                    "status": STATUS_UNWIRED,
                    "owner": "platform-team",
                    "dispose": "wire-pending",
                    "reason": "gone",
                    "review_by": "2026-12-31",
                }
            ]
        }
        failures = audit_failures([item("live_group", STATUS_GATED)], [], registry)
        self.assertTrue(any("removed_group" in failure for failure in failures))

    def test_registry_that_now_gates_is_inconsistent(self) -> None:
        registry = {
            "entries": [
                {
                    "group": "sc_perm",
                    "kind": "odoo_tag",
                    "status": STATUS_UNWIRED,
                    "owner": "platform-team",
                    "dispose": "wire-pending",
                    "reason": "was unwired",
                    "review_by": "2026-12-31",
                }
            ]
        }
        failures = audit_failures([item("sc_perm", STATUS_GATED)], [], registry)
        self.assertTrue(any("still records status" in failure for failure in failures))

    def test_unknown_dispose_fails(self) -> None:
        registry = {
            "entries": [
                {
                    "group": "uc4_native_lowcode",
                    "kind": "odoo_tag",
                    "status": STATUS_UNWIRED,
                    "owner": "construction-product",
                    "dispose": "invented",
                    "reason": "typo",
                    "review_by": "2026-12-31",
                }
            ]
        }
        failures = audit_failures([item("uc4_native_lowcode", STATUS_UNWIRED)], [], registry)
        self.assertTrue(any("unknown dispose" in failure for failure in failures))


class DefaultEntryTest(unittest.TestCase):
    def test_unwired_defaults_to_wire_pending_with_deadline(self) -> None:
        entry = default_entry(item("uc4_native_lowcode", STATUS_UNWIRED, declarations=17))
        self.assertEqual(entry["dispose"], "wire-pending")
        self.assertTrue(entry["review_by"])
        self.assertEqual(entry["owner"], "platform-team")

    def test_on_demand_defaults_to_class_selected_with_gate(self) -> None:
        entry = default_entry(
            {
                **item("user_feedback", STATUS_ON_DEMAND),
                "evidence": ["make:verify.workflow_contract.backend :: /TestUserFeedbackBusinessViews"],
            }
        )
        self.assertEqual(entry["dispose"], "class-selected")
        self.assertIn("make:verify.workflow_contract.backend", entry["gate"])
        self.assertNotIn("review_by", entry)


if __name__ == "__main__":
    unittest.main()
