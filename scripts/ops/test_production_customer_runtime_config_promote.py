from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ProductionCustomerRuntimeConfigPromoteTests(unittest.TestCase):
    def test_promotion_is_narrow_and_fail_closed(self):
        source = (ROOT / "scripts/ops/production_customer_runtime_config_promote.py").read_text()
        self.assertIn('"SC_CUSTOMER_ADDONS_ROOT=" + str(next_root)', source)
        self.assertIn('"/mnt/customer-addons"', source)
        self.assertIn("production_release_set.verify_bound_files(lock)", source)
        self.assertIn('modules = set(lock.get("customer_modules") or [])', source)
        self.assertIn('git("branch", "--show-current") != "main"', source)
        self.assertIn('for remote in ("origin", "gitee-mirror")', source)
        self.assertIn("CUSTOMER_RUNTIME_ACTIVE_MOUNT_MISMATCH", source)
        self.assertNotIn("EXPECTED_RELEASE_SHA=", source)

    def test_make_target_is_governed(self):
        makefile = (ROOT / "make/release.mk").read_text()
        self.assertIn("production.customer.runtime.config.promote: guard.prod.danger", makefile)
        self.assertIn("PROMOTE_VERIFIED_PRODUCTION_CUSTOMER_RUNTIME_CONFIG", makefile)


if __name__ == "__main__":
    unittest.main()
