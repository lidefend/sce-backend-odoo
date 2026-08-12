import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "scripts/verify/product_customer_runtime_decoupling_guard.py"
SPEC = importlib.util.spec_from_file_location("product_customer_runtime_decoupling_guard", GUARD)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProductCustomerRuntimeDecouplingGuardTest(unittest.TestCase):
    def test_repository_product_runtime_is_decoupled(self):
        self.assertEqual(MODULE.main(), 0)

    def test_customer_module_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            addon = root / "smart_core"
            addon.mkdir()
            fixed_module = "sce_" + "customer_" + "baosheng"
            (addon / "runtime.py").write_text("MODULE = %r\n" % fixed_module, encoding="utf-8")
            with patch.object(MODULE, "PRODUCT_ROOTS", (addon,)):
                self.assertEqual(MODULE.main(), 1)


if __name__ == "__main__":
    unittest.main()
