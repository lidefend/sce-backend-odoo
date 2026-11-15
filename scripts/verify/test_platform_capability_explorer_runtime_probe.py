import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("platform_capability_explorer_runtime_probe.py")
SPEC = importlib.util.spec_from_file_location(
    "platform_capability_explorer_runtime_probe_under_test",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RuntimeProbeContractTests(unittest.TestCase):
    def test_runtime_probe_binds_exact_discovery_counts(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn('"PLATFORM_CAPABILITY_EXPLORER_EXPECTED_ENTRY_COUNT", "282"', source)
        self.assertIn('"PLATFORM_CAPABILITY_EXPLORER_EXPECTED_SCENE_BOUND", "75"', source)
        self.assertIn('"PLATFORM_CAPABILITY_EXPLORER_EXPECTED_CENTER_ONLY", "207"', source)
        self.assertIn('"PLATFORM_CAPABILITY_EXPLORER_EXPECTED_UNCLASSIFIED", "0"', source)
        self.assertIn(
            '"PLATFORM_CAPABILITY_EXPLORER_REQUIRE_RELEASE_AUTHORITY", "1"',
            source,
        )

    def test_runtime_probe_is_read_only_and_checks_stale_concurrency_and_security(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        for token in (
            "CatalogStaleError",
            "ThreadPoolExecutor",
            "public_user",
            "domain_force",
            "ACTION_NOT_FOUND",
            "XMLID_NOT_FOUND",
            "query_count",
            "serialization_ms",
        ):
            with self.subTest(token=token):
                self.assertIn(token, source)
        for forbidden in (".write(", ".create(", ".unlink("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        self.assertIn('"write_operations": 0', source)


if __name__ == "__main__":
    unittest.main()
