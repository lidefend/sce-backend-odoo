from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.contract.product_view_capability_ledger_common import (
    NativeCandidate, atom_identity, classify_candidate, classify_structure, load_yaml,
)
from scripts.verify.native_view_capability_taxonomy_guard import validate_taxonomy

ROOT = Path(__file__).resolve().parents[2]


class NativeViewCapabilityTaxonomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.taxonomy = load_yaml(ROOT / "contracts/product/native-view-capability-taxonomy-v1.yaml")
        cls.structure = json.loads((ROOT / "contracts/generated/product_view_structure_contract.json").read_text(encoding="utf-8"))

    def test_tracked_structure_has_zero_unknown_or_ambiguous_candidates(self):
        errors, report = validate_taxonomy(self.structure, self.taxonomy)
        self.assertEqual(errors, [], report)
        self.assertEqual(report["summary"]["surface_count"], 280)
        self.assertGreater(report["summary"]["classified_atom_count"], 8532)

    def test_unknown_tag_fails_closed(self):
        candidate = NativeCandidate(
            kind="node", view_type="form", tag="future_tag", attribute="",
            locator="resolved:x/future_tag", native_locator="resolved:x/future_tag",
            occurrence_index=1, resolved_view_ref="x", ancestors=(), canonical_value={"tag": "future_tag"},
        )
        self.assertEqual(classify_candidate(candidate, self.taxonomy), [])

    def test_ambiguous_rule_is_observable(self):
        taxonomy = deepcopy(self.taxonomy)
        taxonomy["node_rules"].append({"id": "duplicate_field", "tags_exact": ["field"], "view_types": ["form"], "capability_key": "field.occurrence"})
        candidate = NativeCandidate(
            kind="node", view_type="form", tag="field", attribute="",
            locator="resolved:x/form/field[name=x]", native_locator="resolved:x/form/field[name=x]",
            occurrence_index=1, resolved_view_ref="x", ancestors=(), canonical_value={"tag": "field"},
        )
        self.assertEqual(len(classify_candidate(candidate, taxonomy)), 2)

    def test_atom_identity_ignores_translated_value(self):
        left = NativeCandidate(
            kind="attribute", view_type="form", tag="field", attribute="string",
            locator="resolved:x/form/field[name=x]/@string", native_locator="resolved:x/form/field[name=x]/@string",
            occurrence_index=1, resolved_view_ref="x", ancestors=(), canonical_value="Name",
        )
        right = NativeCandidate(
            kind="attribute", view_type="form", tag="field", attribute="string",
            locator="resolved:x/form/field[name=x]/@string", native_locator="resolved:x/form/field[name=x]/@string",
            occurrence_index=1, resolved_view_ref="x", ancestors=(), canonical_value="名称",
        )
        self.assertEqual(atom_identity("x.menu::form", "field.label", left), atom_identity("x.menu::form", "field.label", right))

    def test_classification_is_deterministic(self):
        left = classify_structure(self.structure, self.taxonomy)
        right = classify_structure(self.structure, self.taxonomy)
        self.assertEqual(left, right)


if __name__ == "__main__":
    unittest.main()
