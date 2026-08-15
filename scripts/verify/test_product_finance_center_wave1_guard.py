from __future__ import annotations
import unittest
from scripts.verify.product_finance_center_wave1_guard import validate

class ProductFinanceCenterWave1GuardTest(unittest.TestCase):
    def test_finance_wave_contract_passes(self) -> None:
        self.assertEqual(validate(), [])

    def test_payment_request_has_one_formal_navigation_identity(self) -> None:
        from scripts.verify import product_finance_center_wave1_guard as guard

        navigation = guard.NAVIGATION.read_text(encoding="utf-8")
        self.assertIn(guard.FORMAL_PAYMENT_MENU, navigation)
        self.assertNotIn(guard.RETIRED_PAYMENT_MENU, navigation)

    def test_final_finance_wave_loads_after_legacy_menu_sources(self) -> None:
        from scripts.verify import product_finance_center_wave1_guard as guard

        manifest = guard.MANIFEST.read_text(encoding="utf-8")
        wave = manifest.index("'views/menu_product_finance_wave1.xml'")
        self.assertLess(manifest.index("'views/menu_business_taxonomy.xml'"), wave)
        self.assertLess(manifest.index("'views/menu_user_acceptance_cleanup.xml'"), wave)

if __name__ == "__main__":
    unittest.main()
