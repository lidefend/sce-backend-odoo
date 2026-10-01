from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/verify/contract_schema_declaration_sync.py"


def load_module():
    spec = importlib.util.spec_from_file_location("contract_schema_declaration_sync", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ContractSchemaDeclarationSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_committed_declaration_matches_the_schema_authority(self) -> None:
        text = self.module.LIFECYCLE.read_text(encoding="utf-8")
        self.assertEqual(
            self.module.declared_declaration(text),
            self.module.derived_declaration(),
        )

    def test_declared_drift_is_detected(self) -> None:
        text = self.module.LIFECYCLE.read_text(encoding="utf-8")
        drifted = self.module.render_declaration(
            text, {"UNIFIED_PAGE_SCHEMA_SHA256": "0" * 64}
        )
        self.assertNotEqual(
            self.module.declared_declaration(drifted),
            self.module.derived_declaration(),
        )

    def test_render_rebinds_every_derived_constant(self) -> None:
        text = self.module.LIFECYCLE.read_text(encoding="utf-8")
        broken = self.module.render_declaration(
            text,
            {
                "UNIFIED_PAGE_SCHEMA_SHA256": "0" * 64,
                "UNIFIED_PAGE_SCHEMA_VERSION": "0.0.0",
                "UNIFIED_PAGE_NORMATIVE_STATUS": "draft",
            },
        )
        repaired = self.module.render_declaration(broken, self.module.derived_declaration())
        self.assertEqual(
            self.module.declared_declaration(repaired),
            self.module.derived_declaration(),
        )

    def test_derived_sha256_binds_the_normative_schema_bytes(self) -> None:
        import hashlib

        expected = hashlib.sha256(self.module.SCHEMA.read_bytes()).hexdigest()
        self.assertEqual(self.module.derived_declaration()["UNIFIED_PAGE_SCHEMA_SHA256"], expected)


if __name__ == "__main__":
    unittest.main()
