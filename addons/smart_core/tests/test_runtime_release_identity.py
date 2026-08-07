import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch


TARGET = Path(__file__).resolve().parents[1] / "utils" / "product_release.py"
SPEC = importlib.util.spec_from_file_location("smart_core_product_release", TARGET)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class RuntimeReleaseIdentityTest(unittest.TestCase):
    def test_exposes_exact_runtime_identity(self):
        source_revision = "a" * 40
        build_sha = "b" * 64
        with patch.dict(
            os.environ,
            {
                "SC_SOURCE_REVISION": source_revision,
                "SC_ENVIRONMENT": "daily",
                "FRONTEND_BUILD_SHA256": build_sha,
            },
            clear=False,
        ):
            payload = MODULE.runtime_release_identity("sc_demo")

        self.assertEqual(payload["git_sha"], source_revision)
        self.assertEqual(payload["source_revision"], source_revision)
        self.assertEqual(payload["database"], "sc_demo")
        self.assertEqual(payload["environment"], "daily")
        self.assertEqual(payload["frontend_build_sha256"], build_sha)

    def test_invalid_optional_hashes_fail_closed(self):
        with patch.dict(
            os.environ,
            {"SC_SOURCE_REVISION": "unknown", "FRONTEND_BUILD_SHA256": "invalid"},
            clear=False,
        ):
            payload = MODULE.runtime_release_identity("sc_demo")

        self.assertEqual(payload["git_sha"], "unknown")
        self.assertEqual(payload["frontend_build_sha256"], "")


if __name__ == "__main__":
    unittest.main()
