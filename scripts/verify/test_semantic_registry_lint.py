#!/usr/bin/env python3
"""Focused tests for the contract-runtime semantic/component registry lint.

Positive case: the real repository registry must be self-consistent.

Negative cases: each synthetic mutation must be *detected*. A guard that only
passes on the happy path proves nothing, so every assertion below removes or
corrupts exactly one declaration and requires a specific failure. Each negative
case is also required to be clean before the mutation, so a failure cannot be
attributed to the fixture itself.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import semantic_registry_lint as lint  # noqa: E402

REPO_ROOT = lint.ROOT


class TempRegistryTree:
    """A copy of the real registry that tests may corrupt freely."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="semantic-registry-")
        self.root = Path(self._tmp.name)
        for rel in (
            lint.SEMANTIC_REL,
            lint.COMPONENT_REL,
            lint.SCHEMA_REL,
            lint.ENUM_REGISTRY_REL,
            lint.FRONTEND_REGISTRY_REL,
            lint.carrier.REGISTRY_REL,
            lint.carrier.CARRIER_REL,
            lint.carrier.FRONTEND_REL,
        ):
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / rel, target)
        self.semantic = self.root / lint.SEMANTIC_REL
        self.component = self.root / lint.COMPONENT_REL
        self.frontend = self.root / lint.FRONTEND_REGISTRY_REL
        self.generated_frontend = self.root / lint.carrier.FRONTEND_REL
        self.enum_registry = self.root / lint.ENUM_REGISTRY_REL

    def run(self) -> tuple[list[str], dict]:
        return lint.run(self.root)

    def edit(self, path: Path, old: str, new: str) -> None:
        text = path.read_text(encoding="utf-8")
        if old not in text:
            raise AssertionError(f"fixture anchor not found in {path.name}: {old!r}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def close(self) -> None:
        self._tmp.cleanup()


class RealRegistryTest(unittest.TestCase):
    def test_repository_registry_is_consistent(self) -> None:
        errors, summary = lint.run(REPO_ROOT)
        self.assertEqual([], errors)
        self.assertGreater(summary["semantics"], 0)
        self.assertGreater(summary["components"], 0)
        self.assertEqual(
            summary["semantics"],
            len(lint.load_yaml(REPO_ROOT / lint.SEMANTIC_REL)["semantics"]),
        )

    def test_no_duplicate_keys_in_repository_registry(self) -> None:
        for rel, section in ((lint.SEMANTIC_REL, "semantics"), (lint.COMPONENT_REL, "components")):
            text = (REPO_ROOT / rel).read_text(encoding="utf-8")
            self.assertEqual([], lint.duplicate_yaml_keys(text, section))


class NegativeCaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = TempRegistryTree()
        # Every negative case must start from a clean fixture.
        errors, _ = self.tree.run()
        self.assertEqual([], errors, "fixture baseline is not clean")

    def tearDown(self) -> None:
        self.tree.close()

    def assert_detected(self, needle: str) -> None:
        errors, _ = self.tree.run()
        self.assertTrue(errors, f"mutation was not detected; expected something like {needle!r}")
        self.assertTrue(
            any(needle in error for error in errors),
            f"expected an error containing {needle!r}, got: {errors}",
        )

    def test_renamed_semantic_is_detected(self) -> None:
        self.tree.edit(
            self.tree.semantic,
            "  money: {category: business, component: sc.value.money}",
            "  currency: {category: business, component: sc.value.money}",
        )
        self.assert_detected("undeclared semantic 'money'")

    def test_missing_component_is_detected(self) -> None:
        self.tree.edit(
            self.tree.semantic,
            "  date: {category: temporal, component: sc.input.date}",
            "  date: {category: temporal, component: sc.input.absent}",
        )
        self.assert_detected("unregistered component 'sc.input.absent'")

    def test_unregistered_renderer_is_detected(self) -> None:
        self.tree.edit(
            self.tree.component,
            "sc.input.text: {semantic: text, field_types: [char], renderer: FormSectionField}",
            "sc.input.text: {semantic: text, field_types: [char], renderer: MadeUpControl}",
        )
        self.assert_detected("unregistered renderer 'MadeUpControl'")

    def test_dangling_component_semantic_is_detected(self) -> None:
        self.tree.edit(
            self.tree.component,
            "sc.input.text: {semantic: text, field_types: [char], renderer: FormSectionField}",
            "sc.input.text: {semantic: nope, field_types: [char], renderer: FormSectionField}",
        )
        self.assert_detected("undeclared semantic 'nope'")

    def test_frontend_second_vocabulary_is_detected(self) -> None:
        # The registry module must consume the generated table; a hand-written
        # registration list would re-create the second vocabulary.
        text = self.tree.frontend.read_text(encoding="utf-8")
        self.tree.frontend.write_text(
            text + "registration('sc.extra.thing', 'text', ['char']);\n", encoding="utf-8"
        )
        self.assert_detected("holds a second component vocabulary ('sc.extra.thing')")

    def test_generated_frontend_extra_component_is_detected(self) -> None:
        text = self.tree.generated_frontend.read_text(encoding="utf-8")
        self.tree.generated_frontend.write_text(
            text.replace("];", "  {componentKey: 'sc.extra.thing', semanticType: 'text', "
                               "supportedFieldTypes: ['char'], readiness: 'ready', "
                               "renderer: 'FormSectionField'},\n];", 1),
            encoding="utf-8",
        )
        self.assert_detected("component 'sc.extra.thing' is not declared")

    def test_frontend_missing_component_is_detected(self) -> None:
        self.tree.edit(
            self.tree.generated_frontend,
            "  {componentKey: 'sc.value.money', semanticType: 'money', "
            "supportedFieldTypes: ['monetary'], readiness: 'ready', "
            "renderer: 'ProfessionalBusinessValueControl'},\n",
            "",
        )
        self.assert_detected("component 'sc.value.money' has no frontend registration")

    def test_unclaimed_widget_spelling_is_detected(self) -> None:
        # enum_registry.json is the widget universe the schema permits: a
        # spelling no rule claims would silently render as text.
        text = self.tree.enum_registry.read_text(encoding="utf-8")
        self.tree.enum_registry.write_text(
            text.replace('"many2many_tags"', '"many2many_tags",\n    "ghost_widget"', 1),
            encoding="utf-8",
        )
        self.assert_detected("widget spelling 'ghost_widget' is declared by the contract schema")

    def test_generated_frontend_carrier_drift_is_detected(self) -> None:
        # The frontend carrier is a projection of component.yaml, so a
        # semantic.yaml edit never reaches it.  Drift the generated frontend
        # table itself (a non-key field, so the cross-side vocabulary check is
        # satisfied) and require the carrier guard to notice.
        self.tree.edit(
            self.tree.generated_frontend,
            "{componentKey: 'sc.input.text', semanticType: 'text', "
            "supportedFieldTypes: ['char'], readiness: 'ready', "
            "renderer: 'FormSectionField'}",
            "{componentKey: 'sc.input.text', semanticType: 'text', "
            "supportedFieldTypes: ['char'], readiness: 'fail_closed', "
            "renderer: 'FormSectionField'}",
        )
        self.assert_detected("semantic_registry.generated.ts: out of sync with the declaration")

    def test_duplicate_semantic_key_is_detected(self) -> None:
        text = self.tree.semantic.read_text(encoding="utf-8")
        self.tree.semantic.write_text(
            text + "  money: {category: business, component: sc.value.money}\n", encoding="utf-8"
        )
        self.assert_detected("duplicate key 'semantics.money'")

    def test_contract_reference_to_unknown_semantic_is_detected(self) -> None:
        domain = self.tree.root / "contracts" / "domain" / "sample.yaml"
        domain.parent.mkdir(parents=True, exist_ok=True)
        domain.write_text("version: 1\nfields:\n  amount:\n    semantic: moneyy\n", encoding="utf-8")
        self.assert_detected("references undeclared semantic 'moneyy'")

    def test_valid_contract_reference_is_accepted(self) -> None:
        domain = self.tree.root / "contracts" / "domain" / "sample.yaml"
        domain.parent.mkdir(parents=True, exist_ok=True)
        domain.write_text("version: 1\nfields:\n  amount:\n    semantic: money\n", encoding="utf-8")
        errors, _ = self.tree.run()
        self.assertEqual([], errors)

    def test_runtime_carrier_drift_is_detected(self) -> None:
        # A declaration edit without regeneration must not silently keep the
        # previous vocabulary in the addon.
        self.tree.edit(
            self.tree.semantic,
            "  duration: {category: temporal, component: sc.value.duration}",
            "  duration: {category: temporal, component: sc.display.text}",
        )
        errors, _ = self.tree.run()
        self.assertTrue(
            any("out of sync with the declaration" in error for error in errors),
            f"carrier drift was not detected: {errors}",
        )

    def test_missing_runtime_carrier_is_detected(self) -> None:
        (self.tree.root / lint.carrier.CARRIER_REL).unlink()
        self.assert_detected("carrier is missing")


if __name__ == "__main__":
    unittest.main()
