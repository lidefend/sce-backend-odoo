from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.contract.product_view_capability_ledger_common import STATIC_FORM_MODIFIERS, classify_structure, load_yaml
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
        static_atom = next(
            atom for atom in classify_structure(cls.structure, cls.taxonomy)["atoms"]
            if atom["view_type"] == "form" and atom["capability_key"] in STATIC_FORM_MODIFIERS
        )
        carrier_entry = next(item for item in entries if item["contract_ref"] == static_atom["contract_ref"])
        form_carrier = next(item for item in carrier_entry["normalized_carriers"] if item["source_selector"] == "/data/views/form")
        form_carrier["value"]["layout"] = [{
            "native_locator": static_atom["native_locator"], "occurrence_index": static_atom["occurrence_index"],
            "attributes": {static_atom["attribute"]: static_atom["canonical_value"]},
            "modifiers": {static_atom["attribute"]: True},
        }]
        behavior_atom = next(
            atom for atom in classify_structure(cls.structure, cls.taxonomy)["atoms"]
            if atom["view_type"] == "form" and atom["capability_key"] == "form.create"
        )
        behavior_entry = next(item for item in entries if item["contract_ref"] == behavior_atom["contract_ref"])
        behavior_carrier = next(item for item in behavior_entry["normalized_carriers"] if item["source_selector"] == "/data/views/form")
        behavior_carrier["value"]["capabilities"] = {
            "native_root_attributes": {"create": behavior_atom["canonical_value"]},
            "can_create": str(behavior_atom["canonical_value"]).strip().lower() not in {"0", "false"},
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
        self.assertEqual(summary["proven_mapping_count"], 2)

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

    def test_proven_form_behavior_requires_exact_raw_and_semantic_evidence(self) -> None:
        carrier = deepcopy(self.carrier)
        for entry in carrier["entries"]:
            for row in entry["normalized_carriers"]:
                capabilities = row.get("value", {}).get("capabilities")
                if isinstance(capabilities, dict):
                    capabilities.pop("native_root_attributes", None)
        errors, _ = self.errors(carrier=carrier)
        self.assertTrue(any("form_behavior" in error and "no exact" in error for error in errors))

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
