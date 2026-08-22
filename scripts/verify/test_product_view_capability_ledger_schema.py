from __future__ import annotations

import json
import unittest
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[2]


class ProductViewCapabilityLedgerSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = yaml.safe_load((ROOT / "contracts/schemas/product-view-capability-ledger-v1.yaml").read_text(encoding="utf-8"))
        cls.structure = json.loads((ROOT / "artifacts/contract/product_view_structure_contract.json").read_text(encoding="utf-8"))
        cls.carrier = json.loads((ROOT / "artifacts/contract/product_view_contract_carriers_candidate.json").read_text(encoding="utf-8"))

    def test_schema_is_valid_draft_2020_12(self) -> None:
        jsonschema.Draft202012Validator.check_schema(self.schema)

    def test_authority_uses_same_candidate_artifacts_and_normalized_map(self) -> None:
        authority = self.schema["$defs"]["authority"]["properties"]
        self.assertEqual(authority["view_structure_evidence_path"]["const"], "artifacts/contract/product_view_structure_contract.json")
        self.assertEqual(authority["carrier_evidence_path"]["const"], "artifacts/contract/product_view_contract_carriers_candidate.json")
        self.assertEqual(authority["normalized_map_path"]["const"], "contracts/product/native-view-normalized-capability-map-v1.yaml")

    def test_surface_hash_name_matches_structure_authority(self) -> None:
        hashes = self.schema["$defs"]["surface_entry"]["properties"]["hashes"]
        ledger_keys = set(hashes["required"])
        structure_keys = set(self.structure["entries"][0]["surfaces"][0]["hashes"])
        carrier_keys = set(self.carrier["entries"][0]["hashes"])
        self.assertEqual(ledger_keys, structure_keys)
        self.assertEqual(ledger_keys, carrier_keys)


if __name__ == "__main__":
    unittest.main()
