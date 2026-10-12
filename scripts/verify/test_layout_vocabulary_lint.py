#!/usr/bin/env python3
"""Focused tests for the delivered form-structure vocabulary lint.

Positive case: the real repository payload surface must be self-consistent.

Negative cases: every assertion below mutates exactly one carrier of the
vocabulary and requires a specific failure.  Each fixture is verified clean
before the mutation, so a failure can never be attributed to the fixture.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import layout_vocabulary_lint as lint  # noqa: E402

REPO_ROOT = lint.ROOT
SURFACE_RELS = (lint.SCHEMA_REL, *lint.PAYLOAD_RELS)


class TempPayloadTree:
    """A copy of the real contract payload surface that tests may corrupt."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="layout-vocabulary-")
        self.root = Path(self._tmp.name)
        for rel in SURFACE_RELS:
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / rel, target)

    def read(self, rel: Path) -> str:
        return (self.root / rel).read_text(encoding="utf-8")

    def write(self, rel: Path, source: str) -> None:
        (self.root / rel).write_text(source, encoding="utf-8")

    def schema(self) -> dict:
        return json.loads(self.read(lint.SCHEMA_REL))

    def write_schema(self, payload: dict) -> None:
        self.write(lint.SCHEMA_REL, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    def errors(self) -> list[str]:
        return lint.run(self.root)[0]

    def assert_clean(self) -> None:
        errors = self.errors()
        if errors:
            raise AssertionError(f"fixture must be clean before the mutation: {errors}")


class LayoutVocabularyLintTest(unittest.TestCase):
    def test_repository_payload_surface_is_consistent(self) -> None:
        errors, summary = lint.run(REPO_ROOT)
        self.assertEqual(errors, [])
        self.assertEqual(summary["structure_sources"], list(lint.STRUCTURE_SOURCES))
        self.assertEqual(summary["structure_authorities"], list(lint.STRUCTURE_AUTHORITIES))
        self.assertEqual(summary["payload_surfaces"], len(SURFACE_RELS))

    def test_retired_field_name_is_rejected_on_a_producer(self) -> None:
        tree = TempPayloadTree()
        tree.assert_clean()
        source = tree.read(lint.PAYLOAD_RELS[0])
        tree.write(lint.PAYLOAD_RELS[0], source + '\nLAYOUT = {"layoutPolicy": "legacy"}\n')
        self.assertTrue(any("retired 'layoutPolicy' field" in error for error in tree.errors()))

    def test_retired_value_is_rejected_in_the_decoder(self) -> None:
        tree = TempPayloadTree()
        tree.assert_clean()
        source = tree.read(lint.DECODER_REL)
        tree.write(lint.DECODER_REL, source.replace("'container_tree'", "'container_tree_authority'", 1))
        self.assertTrue(any("container_tree_authority" in error for error in tree.errors()))

    def test_schema_must_require_both_facts(self) -> None:
        tree = TempPayloadTree()
        tree.assert_clean()
        payload = tree.schema()
        contract = payload["$defs"]["formStructureContract"]
        contract["required"] = [name for name in contract["required"] if name != "structureAuthority"]
        tree.write_schema(payload)
        self.assertTrue(any("required must declare structureAuthority" in error for error in tree.errors()))

    def test_schema_enum_must_match_the_reconciled_authority_set(self) -> None:
        tree = TempPayloadTree()
        tree.assert_clean()
        payload = tree.schema()
        contract = payload["$defs"]["formStructureContract"]
        contract["properties"]["structureAuthority"]["enum"] = [
            value for value in contract["properties"]["structureAuthority"]["enum"] if value != "task_sections"
        ]
        tree.write_schema(payload)
        self.assertTrue(any("structureAuthority enum must be" in error for error in tree.errors()))

    def test_schema_must_bind_the_container_tree_rule_to_the_authority_fact(self) -> None:
        tree = TempPayloadTree()
        tree.assert_clean()
        payload = tree.schema()
        contract = payload["$defs"]["formStructureContract"]
        contract["allOf"] = []
        tree.write_schema(payload)
        self.assertTrue(
            any("bind the container-tree rule" in error for error in tree.errors())
        )

    def test_decoder_literals_must_match_the_declaration(self) -> None:
        tree = TempPayloadTree()
        tree.assert_clean()
        source = tree.read(lint.DECODER_REL)
        tree.write(
            lint.DECODER_REL,
            source.replace(
                "const FORM_STRUCTURE_AUTHORITIES = ['container_tree', 'native_form_slots', 'task_sections'] as const;",
                "const FORM_STRUCTURE_AUTHORITIES = ['container_tree'] as const;",
                1,
            ),
        )
        self.assertTrue(any("FORM_STRUCTURE_AUTHORITIES must be" in error for error in tree.errors()))

    def test_strict_type_union_must_match_the_declaration(self) -> None:
        tree = TempPayloadTree()
        tree.assert_clean()
        source = tree.read(lint.TYPES_REL)
        tree.write(
            lint.TYPES_REL,
            source.replace(
                "  | 'entry_semantic_surface';",
                "  | 'entry_semantic_projection';",
                1,
            ),
        )
        self.assertTrue(any("ContractV2FormStructureSource must be" in error for error in tree.errors()))

    def test_only_the_retired_field_is_forbidden_not_the_governance_vocabulary(self) -> None:
        # `native_authority` is the live orchestrator governance token; only the
        # retired structure-vocabulary spellings may fail here.
        tree = TempPayloadTree()
        tree.assert_clean()
        self.assertIn('"native_authority"', tree.read(lint.PAYLOAD_RELS[1]))
        self.assertEqual(tree.errors(), [])

    def test_producers_must_actually_publish_the_facts(self) -> None:
        tree = TempPayloadTree()
        tree.assert_clean()
        for rel in lint.PAYLOAD_RELS:
            if rel.suffix != ".py":
                continue
            tree.write(rel, tree.read(rel).replace('"structureSource"', '"legacySource"'))
        self.assertTrue(any("no contract producer publishes 'structureSource'" in error for error in tree.errors()))

    def test_missing_payload_surface_is_reported(self) -> None:
        tree = TempPayloadTree()
        tree.assert_clean()
        (tree.root / lint.TYPES_REL).unlink()
        self.assertTrue(any("required contract payload surface is missing" in error for error in tree.errors()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
