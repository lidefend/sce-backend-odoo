from __future__ import annotations

import unittest

from scripts.verify.product_workbench_wave1_guard import validate


class ProductWorkbenchWave1GuardTest(unittest.TestCase):
    def test_workbench_wave_contract_passes(self) -> None:
        self.assertEqual(validate(), [])


if __name__ == "__main__":
    unittest.main()
