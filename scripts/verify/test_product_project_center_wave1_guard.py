from __future__ import annotations

import unittest

from scripts.verify.product_project_center_wave1_guard import validate


class ProductProjectCenterWave1GuardTest(unittest.TestCase):
    def test_project_wave_contract_passes(self) -> None:
        self.assertEqual(validate(), [])


if __name__ == "__main__":
    unittest.main()
