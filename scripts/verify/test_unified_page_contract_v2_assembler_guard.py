from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
GUARD_PATH = ROOT / "scripts/verify/unified_page_contract_v2_assembler_guard.py"
ASSEMBLER_PATH = ROOT / "addons/smart_core/core/unified_page_contract_v2_assembler.py"
NATIVE_WIDGET_BRIDGE = "addons/smart_core/core/contract_runtime/native_widget_contract.py"


def load_guard():
    spec = importlib.util.spec_from_file_location("assembler_guard_review_target", GUARD_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load assembler guard")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AssembledCacheInputClosureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.guard = load_guard()

    def test_native_widget_bridge_is_declared_as_a_cache_input(self) -> None:
        self.assertIn(NATIVE_WIDGET_BRIDGE, self.guard.ASSEMBLED_CACHE_INPUTS)
        self.assertIn(
            "from .contract_runtime.native_widget_contract import",
            ASSEMBLER_PATH.read_text(encoding="utf-8"),
        )

    def test_changing_an_included_input_changes_the_cache_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_path = root / "bridge.py"
            input_path.write_text("SEMANTIC = 'date'\n", encoding="utf-8")
            with (
                patch.object(self.guard, "ROOT", root),
                patch.object(self.guard, "ASSEMBLED_CACHE_VERSION", "test-v1"),
                patch.object(self.guard, "ASSEMBLED_CACHE_INPUTS", ("bridge.py",)),
            ):
                before = self.guard._assembled_cache_digest()
                input_path.write_text("SEMANTIC = 'readable_value'\n", encoding="utf-8")
                after = self.guard._assembled_cache_digest()
        self.assertNotEqual(before, after)


if __name__ == "__main__":
    unittest.main()
