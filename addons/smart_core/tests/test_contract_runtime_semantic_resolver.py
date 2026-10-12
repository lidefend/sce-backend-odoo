# -*- coding: utf-8 -*-
"""Focused tests for the contract-runtime semantic resolver.

The resolver replaced the assembler-private ``_component_key`` mapping
(FE-CONTRACT-RUNTIME-00 gap G1).  These tests pin the *behaviour* that mapping
produced, so removing the second vocabulary is proven not to change what the
frontend is told to render, and they pin the declaration/derivation precedence
that the registry introduced.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ADDON_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADDON_ROOT))

from core.contract_runtime import semantic_resolver as resolver  # noqa: E402


class ComponentKeyBaselineTest(unittest.TestCase):
    """Behaviour baseline: every case the former private mapping decided."""

    CASES = (
        # declared field type outranks widget spelling
        ({"type": "many2one_reference", "model_field": "m"}, "input", "sc.display.text"),
        ({"type": "reference"}, "many2one_reference", "sc.display.text"),
        ({"type": "reference"}, "select", "sc.display.text"),
        ({"type": "reference"}, "number", "sc.display.text"),
        # monetary by type or by explicit widget
        ({"type": "monetary"}, "number", "sc.value.money"),
        ({"type": "float"}, "monetary", "sc.value.money"),
        # business widgets on a generic field
        ({"type": "float"}, "percentage", "sc.value.percentage"),
        ({"type": "float"}, "percentpie", "sc.value.percentage"),
        ({"type": "float"}, "float_time", "sc.value.duration"),
        ({"type": "selection"}, "statusbar", "sc.display.status"),
        ({"type": "selection"}, "badge", "sc.display.status"),
        # relations
        ({"type": "many2one", "relation": "res.currency"}, "select", "sc.relation.many2one"),
        ({"type": "many2many", "relation": "x.related"}, "table", "sc.relation.many2many"),
        ({"type": "many2many", "relation": "res.users"}, "many2many_tags", "sc.select.tags"),
        ({"type": "one2many", "relation": "x.line"}, "table", "sc.relation.table"),
        # scalar widgets
        ({"type": "char"}, "input", "sc.input.text"),
        ({"type": "text"}, "textarea", "sc.input.textarea"),
        ({"type": "integer"}, "number", "sc.input.number"),
        ({"type": "selection"}, "select", "sc.select.remote"),
        ({"type": "boolean"}, "checkbox", "sc.input.boolean"),
        ({"type": "date"}, "date", "sc.input.date"),
        ({"type": "datetime"}, "datetime", "sc.input.datetime"),
        ({"type": "binary"}, "binary", "sc.input.binary"),
        ({"type": "one2many"}, "table", "sc.relation.table"),
        # the declared relation type still outranks a collection widget name
        ({"type": "one2many"}, "tree", "sc.relation.table"),
        ({"type": "char"}, "tree", "sc.tree.data"),
        ({"type": "char"}, "table", "sc.table.data"),
        ({"type": "char"}, "button", "sc.button.action"),
        ({"type": "char"}, "display", "sc.display.text"),
    )

    def test_component_keys_match_the_former_mapping(self) -> None:
        for descriptor, widget_type, expected in self.CASES:
            with self.subTest(widget=widget_type, expected=expected):
                self.assertEqual(resolver.component_key(widget_type, descriptor), expected)

    def test_field_names_never_change_the_component(self) -> None:
        self.assertEqual(
            resolver.component_key("number", {"name": "payment_percentage", "type": "float"}),
            "sc.input.number",
        )
        self.assertEqual(
            resolver.component_key("number", {"name": "amount_total", "type": "monetary"}),
            "sc.value.money",
        )

    def test_unknown_widget_uses_the_declared_default(self) -> None:
        self.assertEqual(resolver.component_key("unregistered_widget", {"type": "char"}), "sc.display.text")
        self.assertEqual(
            resolver.semantic_of("unregistered_widget", {"type": "char"}), resolver.FALLBACK_SEMANTIC
        )

    def test_widget_matching_is_case_insensitive(self) -> None:
        self.assertEqual(resolver.component_key("STATUSBAR", {"type": "selection"}), "sc.display.status")
        self.assertEqual(resolver.component_key("Input", {"type": "char"}), "sc.input.text")


class ResolutionSourceTest(unittest.TestCase):
    def test_declared_semantic_wins(self) -> None:
        result = resolver.resolve({"semantic": "money"})
        self.assertEqual(result["semantic"], "money")
        self.assertEqual(result["componentKey"], "sc.value.money")
        self.assertEqual(result["semanticSource"], resolver.SOURCE_DECLARED)

    def test_declared_semantic_overrides_a_conflicting_field_type(self) -> None:
        # A declared semantic is a deliberate contract decision, not a hint the
        # field type may overrule.
        self.assertEqual(resolver.component_key("input", {"type": "char", "semantic": "money"}), "sc.value.money")

    def test_derived_source_is_reported_when_nothing_is_declared(self) -> None:
        result = resolver.resolve({"type": "date"}, "date")
        self.assertEqual(result["semantic"], "date")
        self.assertEqual(result["semanticSource"], resolver.SOURCE_DERIVED)

    def test_undeclared_semantic_is_reported_and_does_not_bind_an_unregistered_component(self) -> None:
        with self.assertLogs("core.contract_runtime.semantic_resolver", level="ERROR") as captured:
            result = resolver.resolve(
                {"name": "amount", "type": "char", "semantic": "not_a_semantic"}, "input"
            )
        self.assertTrue(any("contract_semantic_undeclared" in line for line in captured.output))
        self.assertTrue(any("not_a_semantic" in line for line in captured.output))
        self.assertEqual(result["semanticSource"], resolver.SOURCE_DERIVED)
        self.assertEqual(result["componentKey"], "sc.input.text")

    def test_every_declared_semantic_resolves_to_its_declared_component(self) -> None:
        # The declaration is the expectation, so this fails if the resolver ever
        # drifts from the registry it is supposed to consume.
        from core.contract_runtime.semantic_registry_generated import SEMANTIC_COMPONENTS

        for semantic, component_key in sorted(SEMANTIC_COMPONENTS.items()):
            with self.subTest(semantic=semantic):
                self.assertEqual(
                    resolver.resolve({"semantic": semantic})["componentKey"], component_key
                )


class DeprecationSignalTest(unittest.TestCase):
    def setUp(self) -> None:
        resolver._deprecation_reported = False

    def tearDown(self) -> None:
        resolver._deprecation_reported = False

    def test_authority_path_never_reports_deprecation(self) -> None:
        with self.assertNoLogs("core.contract_runtime.semantic_resolver", level="WARNING"):
            resolver.component_key("input", {"type": "char"})

    def test_legacy_shim_reports_the_event_exactly_once(self) -> None:
        with self.assertLogs("core.contract_runtime.semantic_resolver", level="WARNING") as first:
            # Same result as the authority path: the shim is compatible, only
            # its entry point is deprecated.
            self.assertEqual(
                resolver.legacy_component_key("input", {"type": "char"}), "sc.input.text"
            )
        self.assertTrue(any(resolver.DEPRECATION_EVENT in line for line in first.output))
        with self.assertNoLogs("core.contract_runtime.semantic_resolver", level="WARNING"):
            resolver.legacy_component_key("input", {"type": "char"})


if __name__ == "__main__":
    unittest.main()
