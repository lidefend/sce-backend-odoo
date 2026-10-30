import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GUARD_PATH = ROOT / "scripts" / "verify" / "product_release_version_guard.py"
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _load_guard():
    spec = importlib.util.spec_from_file_location("product_release_version_guard", GUARD_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProductReleaseVersionGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guard = _load_guard()

    def test_registered_historical_identity_passes(self):
        for relative in self.guard.HISTORICAL_IDENTITY_OBSERVATIONS:
            content = (ROOT / relative).read_text(encoding="utf-8")
            self.assertTrue(
                self.guard.is_registered_historical_identity(relative, content),
                str(relative),
            )
            self.assertFalse(
                self.guard.has_release_version_duplicate(relative, content, VERSION),
                str(relative),
            )

    def test_content_change_invalidates_digest(self):
        relative = Path("docs/ops/iterations/page-convergence-01/baseline.md")
        content = (ROOT / relative).read_text(encoding="utf-8")
        self.assertFalse(self.guard.is_registered_historical_identity(relative, content + "\n"))

    def test_unregistered_duplicate_still_fails(self):
        relative = Path("docs/unregistered-note.md")
        self.assertTrue(
            self.guard.has_release_version_duplicate(relative, f"v {VERSION}", VERSION)
        )

    def test_version_token_rejects_longer_suffix(self):
        token = self.guard.version_token_pattern(VERSION)
        self.assertIsNone(token.search(VERSION + "0"))
        self.assertIsNotNone(token.search(VERSION))
        self.assertIsNone(token.search("v" + VERSION))


if __name__ == "__main__":
    unittest.main()
