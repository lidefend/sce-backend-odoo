#!/usr/bin/env python3
"""Focused tests for Contract V2.7 semantic/implementation ownership lint."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import semantic_registry_lint as lint


class TempRegistryTree:
    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="semantic-registry-v27-")
        self.root = Path(self._tmp.name)
        for rel in (
            lint.carrier.SEMANTIC_REL,
            lint.carrier.IMPLEMENTATION_REL,
            lint.SCHEMA_REL,
            lint.ENUM_REGISTRY_REL,
            lint.carrier.REGISTRY_REL,
            lint.carrier.CARRIER_REL,
            lint.carrier.FRONTEND_REL,
            lint.carrier.INDUSTRY_FRONTEND_REL,
            lint.carrier.DOMAIN_SEMANTICS_REL,
            lint.carrier.VIEW_STRUCTURE_REL,
        ):
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(lint.ROOT / rel, target)
        shutil.copytree(lint.ROOT / "contracts/domain", self.root / "contracts/domain")
        (self.root / "addons").mkdir(exist_ok=True)

    def edit(self, rel: Path, old: str, new: str) -> None:
        path = self.root / rel
        text = path.read_text(encoding="utf-8")
        if old not in text:
            raise AssertionError(f"anchor not found in {rel}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def close(self) -> None:
        self._tmp.cleanup()


class V27RegistryLintTests(unittest.TestCase):
    def test_real_repository_is_clean(self):
        errors, summary = lint.run()
        self.assertEqual([], errors)
        self.assertEqual(29, summary["semantics"])
        self.assertEqual(6, summary["node_semantics"])
        self.assertEqual(0, summary["backend_component_identity_facts"])

    def setUp(self):
        self.tree = TempRegistryTree()
        errors, _ = lint.run(self.tree.root)
        self.assertEqual([], errors)

    def tearDown(self):
        self.tree.close()

    def assert_detected(self, needle):
        errors, _ = lint.run(self.tree.root)
        self.assertTrue(any(needle in error for error in errors), errors)

    def test_missing_semantic_applicability_is_detected(self):
        self.tree.edit(
            lint.carrier.SEMANTIC_REL,
            "  money: {category: business, applies_to: field, field_types: [monetary, float]}",
            "  money: {category: business, applies_to: field}",
        )
        self.assert_detected("field_types")

    def test_frontend_unknown_semantic_is_detected(self):
        self.tree.edit(
            lint.carrier.IMPLEMENTATION_REL,
            "  text: {component_key: sc.input.text, renderer: FormSectionField}",
            "  unknown_semantic: {component_key: sc.input.text, renderer: FormSectionField}",
        )
        self.assert_detected("undeclared semantics")

    def test_unregistered_renderer_is_detected(self):
        self.tree.edit(
            lint.carrier.IMPLEMENTATION_REL,
            "  text: {component_key: sc.input.text, renderer: FormSectionField}",
            "  text: {component_key: sc.input.text, renderer: MissingControl}",
        )
        self.assert_detected("unregistered renderer")

    def test_backend_component_identity_is_detected(self):
        path = self.tree.root / "addons/fixture.py"
        path.write_text(
            "def project():\n"
            "    return {'componentKey': 'sc.input.text'}\n",
            encoding="utf-8",
        )
        self.assert_detected("frontend component identity")

    def test_stale_generated_carrier_is_detected(self):
        path = self.tree.root / lint.carrier.CARRIER_REL
        path.write_text(path.read_text(encoding="utf-8") + "\n# stale\n", encoding="utf-8")
        self.assert_detected("generated carrier out of sync")

    def test_missing_frontend_implementation_remains_a_capability_gap_not_contract_error(self):
        self.tree.edit(
            lint.carrier.IMPLEMENTATION_REL,
            "  readable_value: {component_key: sc.display.text, renderer: FormSectionField}\n",
            "",
        )
        self.tree.edit(
            lint.carrier.CARRIER_REL,
            (lint.ROOT / lint.carrier.CARRIER_REL).read_text(encoding="utf-8"),
            lint.carrier.render_repository_carrier(self.tree.root),
        )
        self.tree.edit(
            lint.carrier.FRONTEND_REL,
            (lint.ROOT / lint.carrier.FRONTEND_REL).read_text(encoding="utf-8"),
            lint.carrier.render_frontend_repository(self.tree.root),
        )
        self.tree.edit(
            lint.carrier.INDUSTRY_FRONTEND_REL,
            (lint.ROOT / lint.carrier.INDUSTRY_FRONTEND_REL).read_text(encoding="utf-8"),
            lint.carrier.render_industry_repository(self.tree.root),
        )
        errors, summary = lint.run(self.tree.root)
        self.assertEqual([], errors)
        self.assertEqual(28, summary["field_implementations"])


if __name__ == "__main__":
    unittest.main()
