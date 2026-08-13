from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("product_form_list_requirements_v01.py")
SPEC = importlib.util.spec_from_file_location("product_form_list_requirements_v01", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProductFormListRequirementsV01Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = MODULE.load_json(MODULE.MATRIX_PATH)
        cls.pages = MODULE.load_json(MODULE.PAGES_PATH)
        cls.benchmark = MODULE.load_json(MODULE.BENCHMARK_PATH)

    def test_current_assets_pass_structural_validation(self) -> None:
        self.assertEqual(MODULE.validate_data(self.matrix, self.pages, self.benchmark), [])

    def test_missing_source_item_fails_closed(self) -> None:
        matrix = copy.deepcopy(self.matrix)
        matrix["items"].pop()
        self.assertTrue(any("expected 71" in error for error in MODULE.validate_data(matrix, self.pages, self.benchmark)))

    def test_runtime_claim_fails_closed(self) -> None:
        matrix = copy.deepcopy(self.matrix)
        matrix["items"][0]["runtime_evidence"] = "passed"
        self.assertTrue(any("runtime_unverified" in error for error in MODULE.validate_data(matrix, self.pages, self.benchmark)))

    def test_representative_set_drift_fails_closed(self) -> None:
        pages = copy.deepcopy(self.pages)
        pages["pages"][0]["requirement_id"] = "PFL-001"
        self.assertTrue(any("representative page set drifted" in error for error in MODULE.validate_data(self.matrix, pages, self.benchmark)))

    def test_benchmark_vendor_coverage_fails_closed(self) -> None:
        benchmark = copy.deepcopy(self.benchmark)
        benchmark["benchmarks"] = benchmark["benchmarks"][:2]
        self.assertTrue(any("four vendors" in error for error in MODULE.validate_data(self.matrix, self.pages, benchmark)))


if __name__ == "__main__":
    unittest.main()
