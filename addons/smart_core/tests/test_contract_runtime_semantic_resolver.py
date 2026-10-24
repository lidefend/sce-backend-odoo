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
import json
from pathlib import Path

import yaml

ADDON_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADDON_ROOT))

from core.contract_runtime import semantic_resolver as resolver  # noqa: E402
# The page assembler's widget canonicalisation is the runtime's own entry into
# the derivation rules; a test that re-implemented it could pass while the page
# and the carrier disagreed.
from core.unified_page_contract_v2_assembler import _canonical_widget_type  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
VIEW_STRUCTURE_REL = Path("contracts/generated/product_view_structure_contract.json")
DOMAIN_CONTRACT_REL = Path("contracts/domain/payment-request.yaml")
PAYMENT_MODEL = "payment.request"


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


class PaymentEntitySemanticsTest(unittest.TestCase):
    """The entity's semantics come from the parsed model/view facts, not a hand list.

    ``payment.request`` is the first entity the domain layer binds to a model, so
    it is where "declare nothing, read the facts" has to be provable: the meaning
    of each field is resolved from the governed parse of the Odoo model metadata
    and the resolved view arch, and the carrier the runtime ships must equal that
    resolution field by field.  A hand-maintained copy would be a second input,
    which is the drift this pins out.
    """

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
        """``field -> attrs`` read from the governed parse, richest surface first."""
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

    def test_meaning_bearing_fields_resolve_from_the_parsed_facts_alone(self) -> None:
        facts = self.parsed_field_facts()
        for name, semantic in self.EXPECTED.items():
            with self.subTest(field=name):
                attrs = facts.get(name)
                self.assertIsNotNone(attrs, f"{name} is missing from the governed parse")
                field = {"name": name, "ttype": attrs.get("type")}
                native_widget = str(attrs.get("widget") or "")
                resolution = resolver.resolve(
                    field,
                    resolver.semantic_widget_type(
                        native_widget, _canonical_widget_type(native_widget, field)
                    ),
                )
                self.assertEqual(resolver.SOURCE_DERIVED, resolution["semanticSource"])
                self.assertEqual(semantic, resolution["semantic"])

    def test_shipped_carrier_equals_the_projection_of_the_parsed_facts(self) -> None:
        """The runtime carrier must be a faithful projection, never a private list."""
        from core.contract_runtime.domain_field_semantics_generated import DOMAIN_FIELD_SEMANTICS

        projected = DOMAIN_FIELD_SEMANTICS[PAYMENT_MODEL]
        for name, semantic in self.EXPECTED.items():
            with self.subTest(field=name):
                self.assertEqual(semantic, projected.get(name))
        annotated = [{"name": name} for name in self.EXPECTED]
        self.assertEqual(len(self.EXPECTED), resolver.annotate_projected_semantics(PAYMENT_MODEL, annotated))
        for row in annotated:
            with self.subTest(field=row["name"]):
                self.assertEqual(resolver.SOURCE_PROJECTED, resolver.resolve(row, "")["semanticSource"])

    def test_projection_never_overwrites_an_explicit_semantic(self) -> None:
        rows = [{"name": "amount", "semantic": "number"}]
        self.assertEqual(0, resolver.annotate_projected_semantics(PAYMENT_MODEL, rows))
        self.assertEqual("number", rows[0]["semantic"])

    def test_unknown_model_or_field_projects_nothing(self) -> None:
        self.assertEqual("", resolver.projected_field_semantics("sc.unknown.model", "amount"))
        self.assertEqual("", resolver.projected_field_semantics(PAYMENT_MODEL, "not_a_field"))

    def test_semantic_widgets_survive_canonicalisation(self) -> None:
        # The status rule matches the native spelling; folding it into the
        # generic display token would make the rule unreachable.
        self.assertEqual("statusbar", resolver.semantic_widget_type("statusbar", "display"))
        self.assertEqual("monetary", resolver.semantic_widget_type("monetary", "number"))
        self.assertEqual("select", resolver.semantic_widget_type("", "select"))

    def test_domain_contract_carries_no_hand_written_semantic(self) -> None:
        document = yaml.safe_load((REPO_ROOT / DOMAIN_CONTRACT_REL).read_text(encoding="utf-8"))
        declared = {
            name
            for name, entry in (document.get("fields") or {}).items()
            if isinstance(entry, dict) and entry.get("semantic")
        }
        self.assertEqual(set(), declared, "the model/view facts already carry the semantic")


class ComponentRegistryTest(unittest.TestCase):
    """The single identity/version builder every runtime producer publishes through."""

    def test_declared_keys_publish_the_one_contract_version(self) -> None:
        self.assertEqual(
            {
                "sc.value.money": {"version": resolver.COMPONENT_CONTRACT_VERSION},
                "sc.relation.many2one": {"version": resolver.COMPONENT_CONTRACT_VERSION},
            },
            resolver.component_registry(["sc.relation.many2one", "sc.value.money"]),
        )
        self.assertEqual("1.0", resolver.COMPONENT_CONTRACT_VERSION)

    def test_undeclared_key_rejects_the_whole_registration(self) -> None:
        with self.assertRaisesRegex(ValueError, "COMPONENT_UNREGISTERED"):
            resolver.component_registry(["sc.input.absent", "sc.value.money"])

    def test_a_non_sequence_declares_nothing(self) -> None:
        self.assertEqual({}, resolver.component_registry(None))
        self.assertEqual({}, resolver.component_registry("sc.value.money"))
        self.assertEqual({}, resolver.component_registry(["", "   "]))

    def test_every_resolvable_key_is_publishable(self) -> None:
        # A key the resolver can produce must never be dropped by the builder,
        # otherwise a page would render through an identity it cannot publish.
        for semantic, key in sorted(resolver.SEMANTIC_COMPONENTS.items()):
            with self.subTest(semantic=semantic):
                self.assertEqual({key: {"version": resolver.COMPONENT_CONTRACT_VERSION}},
                                 resolver.component_registry([key]))


if __name__ == "__main__":
    unittest.main()
