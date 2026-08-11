from __future__ import annotations

import unittest

from scripts.verify.product_primary_center_candidate_guard import validate


class ProductPrimaryCenterCandidateGuardTest(unittest.TestCase):
    def test_primary_center_candidate_passes(self) -> None:
        self.assertEqual(validate(), [])


if __name__ == "__main__":
    unittest.main()
