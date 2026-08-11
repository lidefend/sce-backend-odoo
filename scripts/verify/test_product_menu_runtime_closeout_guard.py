from __future__ import annotations

import unittest

from scripts.verify.product_menu_runtime_closeout_guard import validate


class ProductMenuRuntimeCloseoutGuardTest(unittest.TestCase):
    def test_locked_candidate_hidden_menus_are_fail_closed(self) -> None:
        self.assertEqual(validate(), [])


if __name__ == "__main__":
    unittest.main()
