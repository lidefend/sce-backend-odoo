import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_binding():
    spec = importlib.util.spec_from_file_location(
        "acceptance_evolution_binding_guard",
        ROOT / "scripts" / "verify" / "acceptance_evolution_binding_guard.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrIntegrationAdmissionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binding = _load_binding()

    def test_unknown_path_fails_closed(self):
        registry = self.binding.load_registry(self.binding.DEFAULT_REGISTRY)
        head = "a" * 40
        plan = self.binding.build_plan(registry, ["totally/unknown/path.py"], "b" * 40, head)
        self.assertEqual(plan["status"], "FAIL")
        self.assertIn("totally/unknown/path.py", plan["unclassified"])

    def test_missing_runtime_evidence_blocks(self):
        registry = self.binding.load_registry(self.binding.DEFAULT_REGISTRY)
        head = "a" * 40
        # A frontend runtime change requires browser evidence suites.
        plan = self.binding.build_plan(
            registry, ["frontend/apps/web/src/views/ActionView.vue"], "b" * 40, head
        )
        self.assertTrue(plan["required_evidence_suites"])
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "evidence.v1.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema": self.binding.EVIDENCE_SCHEMA,
                        "head_sha": head,
                        "recorded_at": "2026-10-30T10:00:00Z",
                        "suites": {},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(Exception) as ctx:
                self.binding.validate_manifest(registry, plan, manifest_path, head)
            self.assertIn("missing required suite", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
