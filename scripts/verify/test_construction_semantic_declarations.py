#!/usr/bin/env python3
"""Focused tests for the construction product layer's semantic declarations.

FE-CONTRACT-RUNTIME-01 removed the payment model+field branch that wrote a
literal component key.  The product layer now declares *what a field means* and
the contract registry names the component, so these tests lock the consumption
rather than the old implementation:

* every declared semantic is one ``contracts/registry/component.yaml`` declares;
* the normalizer writes the component the registry resolves, and the module
  holds no component key of its own;
* an undeclared semantic is refused -- the field keeps the component its facts
  resolve to instead of being rendered through an unregistered key;
* the fields it does not declare are untouched;
* the delivery vocabulary it hands over satisfies every term the frontend
  dialog model requires before it opens.

The normalizer lives in an Odoo addon and is executed here through its own
module-level declarations and functions, with the real contract-runtime resolver
injected, so a declaration change is caught without an Odoo or browser round
trip.
"""

from __future__ import annotations

import ast
import copy
import logging
import re
import sys
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_REL = Path("addons/smart_construction_core/core_extension_contract_normalizers.py")
DIALOG_MODEL_REL = Path(
    "frontend/apps/web/src/components/professional-fields/paymentSettlementIntroduceDialogModel.ts"
)
DIALOG_CONFIG_KEY = "introduceDialog"
PAYMENT_MODEL = "payment.request"
PAYMENT_DETAIL_FIELD = "outflow_line_ids"
PAYMENT_DETAIL_SEMANTIC = "payment_settlement_detail_collection"

# The resolver is the real runtime consumer of the registry; without it the test
# could pass while the page and this declaration disagreed.
sys.path.insert(0, str(REPO_ROOT / "addons" / "smart_core"))
from core.contract_runtime import semantic_resolver  # noqa: E402

_WANTED_ASSIGNMENTS = {"FIELD_SEMANTIC_DECLARATIONS", "SEMANTIC_PRESENTATION_VOCABULARY"}
_WANTED_FUNCTIONS = {
    "_declared_semantic",
    "_apply_declared_semantic",
    "normalize_declared_field_presentation",
}


def load_normalizer_namespace() -> dict[str, Any]:
    """Execute the normalizer's declarations and functions with the real resolver."""
    source = (REPO_ROOT / MODULE_REL).read_text(encoding="utf-8")
    tree = ast.parse(source)
    body = []
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id in _WANTED_ASSIGNMENTS:
                body.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in _WANTED_ASSIGNMENTS for target in node.targets
        ):
            body.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in _WANTED_FUNCTIONS:
            body.append(node)
    namespace: dict[str, Any] = {
        "__name__": "construction_semantic_declarations",
        "deepcopy": copy.deepcopy,
        "Any": Any,
        "_logger": logging.getLogger(__name__),
        "_semantic_resolver": semantic_resolver,
        "_sc_text": lambda value: str(value if value is not None else "").strip(),
    }
    exec(compile(ast.Module(body=body, type_ignores=[]), str(MODULE_REL), "exec"), namespace)
    return namespace


def frontend_required_paths(repo_root: Path) -> tuple[list[str], set[str]]:
    """The dialog terms the frontend refuses to open without.

    Read from the model that consumes them, so the expected set is never a
    second copy maintained here.
    """
    source = (repo_root / DIALOG_MODEL_REL).read_text(encoding="utf-8")
    composed = re.search(
        r"SETTLEMENT_INTRODUCE_REQUIRED_PATHS[^=]*=\s*Object\.freeze\(\[(.*?)\]\)", source, re.S
    )
    if not composed:
        raise AssertionError("the frontend dialog model no longer composes its required paths")
    spread = set(re.findall(r"\.\.\.(\w+)", composed.group(1)))

    paths: list[str] = []
    for name in sorted(spread):
        block = re.search(rf"{name}[^=]*=\s*Object\.freeze\(\[(.*?)\]\)", source, re.S)
        if not block:
            raise AssertionError(f"the frontend dialog model declares {name} in a shape this test cannot read")
        body = block.group(1)
        paths.extend(
            raw.replace("${DIALOG_CONFIG_KEY}", DIALOG_CONFIG_KEY)
            for raw in re.findall(r"`([^`]+)`", body)
        )
        paths.extend(re.findall(r"'([^']+)'", body))
    return paths, spread


def read_declared_path(source: dict, path: str) -> str:
    """Mirror of the frontend ``readPath``: only a non-blank scalar counts."""
    cursor: Any = source
    for segment in path.split("."):
        if not isinstance(cursor, dict):
            return ""
        cursor = cursor.get(segment)
    return str(cursor).strip() if isinstance(cursor, (str, int, float)) else ""


class DeclarationAuthorityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.namespace = load_normalizer_namespace()
        self.declarations = self.namespace["FIELD_SEMANTIC_DECLARATIONS"]
        self.vocabulary = self.namespace["SEMANTIC_PRESENTATION_VOCABULARY"]

    def test_declared_semantics_are_declared_by_the_registry(self) -> None:
        self.assertIn(PAYMENT_MODEL, self.declarations)
        for model, fields in self.declarations.items():
            for field_code, semantic in fields.items():
                with self.subTest(model=model, field=field_code):
                    self.assertTrue(
                        semantic_resolver.component_key_for_semantic(semantic),
                        f"declared semantic '{semantic}' is not registered, so the field would "
                        "render through an unregistered key",
                    )
                    self.assertEqual(semantic, semantic.lower())

    def test_payment_detail_semantic_is_the_declared_payment_one(self) -> None:
        self.assertEqual(
            PAYMENT_DETAIL_SEMANTIC,
            self.declarations[PAYMENT_MODEL][PAYMENT_DETAIL_FIELD],
        )
        self.assertIn(PAYMENT_DETAIL_SEMANTIC, self.vocabulary)


class NormalizerConsumptionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.namespace = load_normalizer_namespace()
        self.normalize = self.namespace["normalize_declared_field_presentation"]

    def payment_contract(self) -> dict[str, Any]:
        return {
            "layoutContract": {
                "containerTree": [
                    {
                        "containerId": "payment.basic",
                        "widgetList": [
                            {
                                "widgetId": "field.amount",
                                "fieldCode": "amount",
                                "componentKey": "sc.value.money",
                                "componentConfig": {"fieldType": "monetary"},
                                "fieldDescriptor": {"name": "amount", "type": "monetary"},
                            }
                        ],
                    },
                    {
                        "containerId": "payment.detail",
                        "widgetList": [
                            {
                                "widgetId": f"field.{PAYMENT_DETAIL_FIELD}",
                                "fieldCode": PAYMENT_DETAIL_FIELD,
                                "componentKey": "sc.relation.table",
                                "componentConfig": {"fieldType": "one2many"},
                                "fieldDescriptor": {"name": PAYMENT_DETAIL_FIELD, "type": "one2many"},
                            }
                        ],
                    },
                ],
            }
        }

    def detail_node(self, contract: dict[str, Any]) -> dict[str, Any]:
        return contract["layoutContract"]["containerTree"][1]["widgetList"][0]

    def test_declared_field_takes_the_registrys_component(self) -> None:
        contract = self.payment_contract()
        self.normalize(contract, model=PAYMENT_MODEL, view_type="form")
        node = self.detail_node(contract)
        expected = semantic_resolver.component_key_for_semantic(PAYMENT_DETAIL_SEMANTIC)
        self.assertEqual(expected, node["componentKey"])
        self.assertEqual(PAYMENT_DETAIL_SEMANTIC, node["fieldDescriptor"]["semantic"])

    def test_declared_field_publishes_the_registry_identity(self) -> None:
        contract = self.payment_contract()
        self.normalize(contract, model=PAYMENT_MODEL, view_type="form")
        registry = contract["layoutContract"]["componentRegistry"]
        self.assertEqual(
            {semantic_resolver.component_key_for_semantic(PAYMENT_DETAIL_SEMANTIC): {
                "version": semantic_resolver.COMPONENT_CONTRACT_VERSION,
            }},
            registry,
        )

    def test_vocabulary_is_merged_into_the_delivered_component_config(self) -> None:
        contract = self.payment_contract()
        self.normalize(contract, model=PAYMENT_MODEL, view_type="form")
        config = self.detail_node(contract)["componentConfig"]
        vocabulary = self.namespace["SEMANTIC_PRESENTATION_VOCABULARY"][PAYMENT_DETAIL_SEMANTIC]
        self.assertEqual("one2many", config["fieldType"])
        for key, value in vocabulary.items():
            with self.subTest(key=key):
                self.assertEqual(value, config[key])

    def test_undeclared_fields_are_untouched(self) -> None:
        contract = self.payment_contract()
        before = copy.deepcopy(contract["layoutContract"]["containerTree"][0])
        self.normalize(contract, model=PAYMENT_MODEL, view_type="form")
        self.assertEqual(before, contract["layoutContract"]["containerTree"][0])

    def test_other_models_are_untouched(self) -> None:
        contract = self.payment_contract()
        before = copy.deepcopy(contract)
        self.normalize(contract, model="project.project", view_type="form")
        self.assertEqual(before, contract)

    def test_non_form_view_is_untouched(self) -> None:
        contract = self.payment_contract()
        before = copy.deepcopy(contract)
        self.normalize(contract, model=PAYMENT_MODEL, view_type="tree")
        self.assertEqual(before, contract)

    def test_undeclared_semantic_is_refused_instead_of_misrendering(self) -> None:
        """Negative case: the baseline must be clean before the mutation is injected."""
        contract = self.payment_contract()
        self.normalize(contract, model=PAYMENT_MODEL, view_type="form")
        self.assertEqual(
            semantic_resolver.component_key_for_semantic(PAYMENT_DETAIL_SEMANTIC),
            self.detail_node(contract)["componentKey"],
            "baseline did not apply the declaration, so the negative case proves nothing",
        )

        mutated = self.payment_contract()
        self.namespace["FIELD_SEMANTIC_DECLARATIONS"][PAYMENT_MODEL][PAYMENT_DETAIL_FIELD] = "sc.declared.by.nobody"
        self.normalize(mutated, model=PAYMENT_MODEL, view_type="form")
        node = self.detail_node(mutated)
        self.assertEqual("sc.relation.table", node["componentKey"])
        self.assertNotIn("semantic", node["fieldDescriptor"])
        self.assertNotIn("componentRegistry", mutated["layoutContract"])

    def test_a_new_field_needs_only_a_semantic_declaration(self) -> None:
        """The owner's acceptance standard, executed rather than asserted in prose.

        A field the facts would render as text is given the meaning ``money`` by
        one line in the declaration table.  Nothing else changes: no resolver
        branch, no component key, no renderer name.  If either side still needed
        mapping code for the new field, this test could not pass.
        """
        contract = self.payment_contract()
        contract["layoutContract"]["containerTree"][0]["widgetList"].append(
            {
                "widgetId": "field.settled_amount",
                "fieldCode": "settled_amount",
                "componentKey": semantic_resolver.component_key("input", {"ttype": "char"}),
                "fieldDescriptor": {"name": "settled_amount", "type": "char"},
            }
        )
        self.assertEqual(
            "sc.input.text",
            contract["layoutContract"]["containerTree"][0]["widgetList"][1]["componentKey"],
            "baseline: without a declaration the field's own facts select the text input",
        )

        declarations = self.namespace["FIELD_SEMANTIC_DECLARATIONS"]
        declarations[PAYMENT_MODEL]["settled_amount"] = "money"
        try:
            self.normalize(contract, model=PAYMENT_MODEL, view_type="form")
        finally:
            del declarations[PAYMENT_MODEL]["settled_amount"]

        node = contract["layoutContract"]["containerTree"][0]["widgetList"][1]
        self.assertEqual(semantic_resolver.component_key_for_semantic("money"), node["componentKey"])
        self.assertEqual("sc.value.money", node["componentKey"])
        self.assertEqual("money", node["fieldDescriptor"]["semantic"])
        self.assertIn(
            "sc.value.money",
            contract["layoutContract"]["componentRegistry"],
            "the declared field's identity must be published to the frontend registry",
        )


class FrontendVocabularyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.vocabulary = load_normalizer_namespace()["SEMANTIC_PRESENTATION_VOCABULARY"]

    def test_frontend_required_paths_are_read_from_the_model(self) -> None:
        paths, spread = frontend_required_paths(REPO_ROOT)
        self.assertEqual(
            {"REQUIRED_TERM_PATHS", "REQUIRED_PAYLOAD_PATHS", "REQUIRED_ACTION_PATHS", "REQUIRED_ENTRY_PATHS"},
            spread,
            "the frontend added a required-path group; read it here instead of assuming it is covered",
        )
        self.assertGreater(len(paths), 0)

    def test_declared_vocabulary_satisfies_the_frontend_contract(self) -> None:
        paths, _ = frontend_required_paths(REPO_ROOT)
        declared = self.vocabulary[PAYMENT_DETAIL_SEMANTIC]
        missing = [path for path in paths if not read_declared_path(declared, path)]
        self.assertEqual(
            [],
            missing,
            "the declared delivery vocabulary does not cover the dialog terms the frontend "
            "refuses to open without",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
