# -*- coding: utf-8 -*-
"""Contract V2.7 client-independent semantic resolver tests."""
from __future__ import annotations

import json
import sys
import unittest
import yaml
from pathlib import Path

ADDON_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADDON_ROOT))

from core.contract_runtime import semantic_resolver as resolver  # noqa: E402
from core.unified_page_contract_v2_assembler import _canonical_widget_type  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
VIEW_STRUCTURE_REL = Path("contracts/generated/product_view_structure_contract.json")
DOMAIN_CONTRACT_REL = Path("contracts/domain/payment-request.yaml")
PAYMENT_MODEL = "payment.request"


class SemanticResolutionTest(unittest.TestCase):
    CASES = (
        ({"type": "many2one_reference", "model_field": "m"}, "input", "reference"),
        ({"type": "reference"}, "select", "reference"),
        ({"type": "monetary"}, "number", "money"),
        ({"type": "float"}, "monetary", "money"),
        ({"type": "float"}, "percentage", "percentage"),
        ({"type": "float"}, "float_time", "duration"),
        ({"type": "selection"}, "statusbar", "status"),
        ({"type": "binary"}, "account-tax-totals-field", "readable_value"),
        ({"type": "many2one", "relation": "res.currency"}, "select", "relation"),
        ({"type": "many2many", "relation": "x.related"}, "table", "relation_collection"),
        ({"type": "many2many", "relation": "res.users"}, "many2many_tags", "tag_collection"),
        ({"type": "one2many", "relation": "x.line"}, "table", "detail_collection"),
        ({"type": "char"}, "input", "text"),
        ({"type": "text"}, "textarea", "long_text"),
        ({"type": "integer"}, "number", "number"),
        ({"type": "selection"}, "select", "choice"),
        ({"type": "boolean"}, "checkbox", "boolean"),
        ({"type": "date"}, "date", "date"),
        ({"type": "datetime"}, "datetime", "datetime"),
        ({"type": "binary"}, "binary", "binary"),
        ({"type": "char"}, "tree", "hierarchical_collection"),
        ({"type": "char"}, "table", "detail_table"),
        ({"type": "char"}, "button", "action"),
        ({"type": "char"}, "display", "readable_value"),
    )

    def test_semantics_are_derived_without_component_identity(self) -> None:
        for descriptor, widget_type, expected in self.CASES:
            with self.subTest(widget=widget_type, expected=expected):
                result = resolver.resolve(descriptor, widget_type)
                self.assertEqual(result["semantic"], expected)
                self.assertNotIn("componentKey", result)

    def test_declared_semantic_is_the_backend_authority(self) -> None:
        result = resolver.resolve({"type": "char", "semantic": "money"})
        self.assertEqual(result, {
            "semantic": "money",
            "semanticSource": resolver.SOURCE_DECLARED,
        })

    def test_unknown_declared_semantic_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "CONTRACT_SEMANTIC_UNDECLARED"):
            resolver.resolve({"name": "amount", "type": "char", "semantic": "not_a_semantic"})

    def test_unknown_widget_uses_declared_fallback_semantic(self) -> None:
        self.assertEqual(
            resolver.resolve({"type": "char"}, "unregistered_widget")["semantic"],
            resolver.FALLBACK_SEMANTIC,
        )

    def test_semantic_spec_is_independent_from_frontend_implementations(self) -> None:
        # reference and readable_value legally share one frontend implementation.
        # Backend semantic validity must not depend on one-to-one component rows.
        self.assertTrue(resolver.is_field_semantic("reference"))
        self.assertTrue(resolver.is_field_semantic("readable_value"))
        self.assertFalse(resolver.is_node_semantic("readable_value"))
        self.assertFalse(resolver.is_field_semantic("feedback_message"))


class PaymentEntitySemanticsTest(unittest.TestCase):
    EXPECTED = {
        "name": "text",
        "project_id": "relation",
        "contract_id": "relation",
        "settlement_id": "relation",
        "amount": "money",
        "state": "status",
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = json.loads((REPO_ROOT / VIEW_STRUCTURE_REL).read_text(encoding="utf-8"))

    def parsed_field_facts(self) -> dict[str, dict]:
        entry = next(
            item for item in self.baseline["entries"] if item.get("res_model") == PAYMENT_MODEL
        )
        surfaces = sorted(
            (s for s in entry.get("surfaces") or [] if s.get("view_type") == "form"),
            key=lambda s: str(s.get("view_ref") or ""),
        )
        facts: dict[str, dict] = {}

        def walk(node: object) -> None:
            if isinstance(node, dict):
                attrs = node.get("attrs") or {}
                if node.get("tag") == "field" and attrs.get("name"):
                    facts.setdefault(str(attrs["name"]), attrs)
                for child in node.get("children") or []:
                    walk(child)

        for surface in surfaces:
            walk(surface.get("semantic_structure") or {})
        return facts

    def test_meaning_fields_resolve_from_parsed_facts(self) -> None:
        facts = self.parsed_field_facts()
        for name, semantic in self.EXPECTED.items():
            with self.subTest(field=name):
                attrs = facts.get(name)
                self.assertIsNotNone(attrs, f"{name} is missing from the governed parse")
                field = {"name": name, "ttype": attrs.get("type")}
                native_widget = str(attrs.get("widget") or "")
                result = resolver.resolve(
                    field,
                    resolver.semantic_widget_type(
                        native_widget,
                        _canonical_widget_type(native_widget, field),
                    ),
                )
                self.assertEqual(resolver.SOURCE_DERIVED, result["semanticSource"])
                self.assertEqual(semantic, result["semantic"])

    def test_domain_contract_carries_no_hand_written_semantic(self) -> None:
        document = yaml.safe_load((REPO_ROOT / DOMAIN_CONTRACT_REL).read_text(encoding="utf-8"))
        declared = {
            name
            for name, entry in (document.get("fields") or {}).items()
            if isinstance(entry, dict) and entry.get("semantic")
        }
        self.assertEqual(set(), declared)


if __name__ == "__main__":
    unittest.main()
