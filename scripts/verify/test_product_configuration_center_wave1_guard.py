from __future__ import annotations

import unittest

from scripts.verify.product_configuration_center_wave1_guard import validate


class ProductConfigurationCenterWave1GuardTest(unittest.TestCase):
    def test_product_configuration_wave_contract_passes(self) -> None:
        self.assertEqual(validate(), [])


if __name__ == "__main__":
    unittest.main()
