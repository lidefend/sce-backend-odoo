from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.contract.product_view_capability_ledger_common import load_yaml
from scripts.verify.native_view_normalized_capability_map_guard import _pointer_get, validate_normalized_map


ROOT = Path(__file__).resolve().parents[2]


class NativeViewNormalizedCapabilityMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.structure = json.loads((ROOT / "contracts/generated/product_view_structure_contract.json").read_text(encoding="utf-8"))
        cls.taxonomy = load_yaml(ROOT / "contracts/product/native-view-capability-taxonomy-v1.yaml")
        cls.normalized_map = load_yaml(ROOT / "contracts/product/native-view-normalized-capability-map-v1.yaml")
        cls.reasons = load_yaml(ROOT / "contracts/product/native-view-capability-reason-codes-v1.yaml")
        cls.schema = load_yaml(ROOT / "contracts/schemas/native-view-normalized-capability-map-v1.yaml")
        fingerprint = cls.structure["authority"]["candidate_fingerprint"]
        entries = []
        for structure_entry in cls.structure["entries"]:
            for surface in structure_entry["surfaces"]:
                view_type = surface["view_type"]
                selectors = [f"/data/views/{view_type}"] + (["/data/search"] if view_type == "search" else [])
                carriers = []
                for selector in selectors:
                    value = {"view_type": view_type}
                    for mapping in cls.normalized_map["mappings"]:
                        if view_type not in mapping["view_types"]:
                            continue
                        resolved_selectors = [item.replace("{view_type}", view_type) for item in mapping["source_selectors"]]
                        if selector not in resolved_selectors:
                            continue
                        for region in mapping["value_regions"]:
                            if region:
                                value[region.removeprefix("/")] = {}
                    carriers.append({"source_selector": selector, "value": value})
                entries.append({
                    "contract_ref": surface["contract_ref"], "view_type": view_type,
                    "normalized_carriers": carriers,
                })
        cls.carrier = {
            "authority": {"candidate_fingerprint": fingerprint},
            "structure_input": {"candidate_fingerprint": fingerprint},
            "entries": entries,
        }

    def errors(self, normalized_map=None, reasons=None, carrier=None):
        return validate_normalized_map(
            self.structure, carrier or self.carrier, self.taxonomy, normalized_map or self.normalized_map,
            reasons or self.reasons, self.schema, [],
        )

    def test_tracked_structure_has_complete_unique_mapping(self) -> None:
        errors, summary = self.errors()
        self.assertEqual(errors, [])
        self.assertEqual(summary["classified_atom_count"], 26531)
        self.assertEqual(summary["unmapped_atom_count"], 0)
        self.assertEqual(summary["ambiguous_atom_count"], 0)
        self.assertEqual(summary["proven_mapping_count"], 0)

    def test_missing_mapping_fails_closed(self) -> None:
        value = deepcopy(self.normalized_map)
        value["mappings"] = value["mappings"][1:]
        errors, _ = self.errors(value)
        self.assertTrue(any("unmapped atoms" in error for error in errors))

    def test_ambiguous_mapping_fails_closed(self) -> None:
        value = deepcopy(self.normalized_map)
        duplicate = deepcopy(value["mappings"][0])
        duplicate["id"] = "duplicate_view_root"
        value["mappings"].append(duplicate)
        errors, _ = self.errors(value)
        self.assertTrue(any("ambiguously mapped atoms" in error for error in errors))

    def test_forbidden_projection_alias_fails_closed(self) -> None:
        value = deepcopy(self.normalized_map)
        value["mappings"][0]["source_selectors"] = ["/data/native_view/views"]
        errors, _ = self.errors(value)
        self.assertTrue(any("forbidden source alias" in error for error in errors))

    def test_unregistered_reason_fails_closed(self) -> None:
        value = deepcopy(self.normalized_map)
        value["mappings"][0]["missing_reason_code"] = "NOT_REGISTERED"
        errors, _ = self.errors(value)
        self.assertTrue(any("not registered" in error for error in errors))

    def test_unproven_rule_cannot_claim_proven(self) -> None:
        value = deepcopy(self.normalized_map)
        value["mappings"][1]["mapping_status"] = "proven"
        errors, _ = self.errors(value)
        self.assertTrue(any("claims proven" in error for error in errors))

    def test_empty_string_is_the_rfc6901_document_root(self) -> None:
        value = {"view_type": "form"}
        self.assertIs(_pointer_get(value, ""), value)

    def test_view_root_slash_is_not_the_document_root(self) -> None:
        value = deepcopy(self.normalized_map)
        value["mappings"][0]["value_regions"] = ["/"]
        errors, _ = self.errors(value)
        self.assertTrue(any("document-root pointer" in error for error in errors))

    def test_proven_missing_region_fails_closed(self) -> None:
        value = deepcopy(self.normalized_map)
        value["mappings"][0].update({
            "mapping_status": "proven", "matcher": "surface_identity",
            "cardinality_policy": "exactly_one", "value_regions": ["/missing"],
        })
        errors, _ = self.errors(value)
        self.assertTrue(any("value region is not resolvable" in error for error in errors))

    def test_missing_carrier_surface_fails_closed(self) -> None:
        carrier = deepcopy(self.carrier)
        carrier["entries"] = carrier["entries"][1:]
        errors, _ = self.errors(carrier=carrier)
        self.assertTrue(any("contract_ref sets differ" in error for error in errors))

    def test_canonical_view_type_drift_fails_closed(self) -> None:
        value = deepcopy(self.normalized_map)
        value["canonical_view_types"] = value["canonical_view_types"][:-1]
        errors, _ = self.errors(value)
        self.assertTrue(any("canonical view types" in error for error in errors))

    def test_capability_pair_digest_drift_fails_closed(self) -> None:
        value = deepcopy(self.normalized_map)
        value["classified_capability_pairs_sha256"] = "0" * 64
        errors, _ = self.errors(value)
        self.assertTrue(any("pair digest" in error for error in errors))

    def test_upstream_carrier_guard_failure_is_not_ignored(self) -> None:
        errors, _ = validate_normalized_map(
            self.structure, self.carrier, self.taxonomy, self.normalized_map,
            self.reasons, self.schema, ["manifest hash mismatch"],
        )
        self.assertTrue(any("carrier: manifest hash mismatch" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
