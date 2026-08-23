from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.contract.product_view_capability_ledger_common import load_yaml
from scripts.verify.native_view_frontend_capability_map_guard import validate_frontend_map


ROOT = Path(__file__).resolve().parents[2]


class NativeViewFrontendCapabilityMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.structure = json.loads((ROOT / "contracts/generated/product_view_structure_contract.json").read_text(encoding="utf-8"))
        cls.taxonomy = load_yaml(ROOT / "contracts/product/native-view-capability-taxonomy-v1.yaml")
        cls.frontend_map = load_yaml(ROOT / "contracts/product/native-view-frontend-capability-map-v1.yaml")
        cls.reasons = load_yaml(ROOT / "contracts/product/native-view-capability-reason-codes-v1.yaml")

    def errors(self, frontend_map=None, reasons=None):
        return validate_frontend_map(
            self.structure,
            self.taxonomy,
            frontend_map or self.frontend_map,
            reasons or self.reasons,
            ROOT,
        )

    def test_tracked_structure_has_complete_unique_mapping(self) -> None:
        errors, summary = self.errors()
        self.assertEqual(errors, [])
        self.assertEqual(summary["classified_atom_count"], 26531)
        self.assertEqual(summary["unmapped_atom_count"], 0)
        self.assertEqual(summary["ambiguous_atom_count"], 0)

    def test_missing_mapping_fails_closed(self) -> None:
        value = deepcopy(self.frontend_map)
        value["mappings"] = value["mappings"][1:]
        errors, _ = self.errors(value)
        self.assertTrue(any("unmapped atoms" in error for error in errors))

    def test_ambiguous_mapping_fails_closed(self) -> None:
        value = deepcopy(self.frontend_map)
        duplicate = deepcopy(value["mappings"][0])
        duplicate["id"] = "duplicate_mapping"
        value["mappings"].append(duplicate)
        errors, _ = self.errors(value)
        self.assertTrue(any("ambiguously mapped atoms" in error for error in errors))

    def test_unregistered_reason_fails_closed(self) -> None:
        value = deepcopy(self.frontend_map)
        value["mappings"][0]["reason_code"] = "NOT_REGISTERED"
        errors, _ = self.errors(value)
        self.assertTrue(any("reason is not registered" in error for error in errors))

    def test_missing_symbol_file_fails_closed(self) -> None:
        value = deepcopy(self.frontend_map)
        value["symbols"]["native_form_tree"]["path"] = "frontend/missing.vue"
        errors, _ = self.errors(value)
        self.assertTrue(any("governed file" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
