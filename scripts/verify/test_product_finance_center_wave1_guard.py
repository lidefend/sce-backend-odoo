from __future__ import annotations
import unittest
from scripts.verify.product_finance_center_wave1_guard import validate

class ProductFinanceCenterWave1GuardTest(unittest.TestCase):
    def test_finance_wave_contract_passes(self) -> None:
        self.assertEqual(validate(), [])

if __name__ == "__main__":
    unittest.main()
