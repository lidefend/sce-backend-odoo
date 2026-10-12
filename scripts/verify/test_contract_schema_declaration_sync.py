from __future__ import annotations

import importlib.util
import json
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

    def test_canonical_examples_bind_the_schema_authority(self) -> None:
        authority = self.module.derived_declaration()
        files = self.module.example_files()
        self.assertTrue(files)
        for path in files:
            with self.subTest(example=path.name):
                content = path.read_text(encoding="utf-8")
                self.assertEqual(self.module.example_definition_drift(content, authority), {})

    def test_example_drift_is_detected_inside_the_definition_only(self) -> None:
        authority = self.module.derived_declaration()
        path = self.module.example_files()[0]
        content = path.read_text(encoding="utf-8")
        tampered = content.replace(
            f'"schemaSha256": "{authority["UNIFIED_PAGE_SCHEMA_SHA256"]}"',
            '"schemaSha256": "' + "0" * 64 + '"',
        )
        self.assertNotEqual(tampered, content)
        drift = self.module.example_definition_drift(tampered, authority)
        self.assertEqual(sorted(drift), ["schemaSha256"])
        self.assertEqual(drift["schemaSha256"]["derived"], authority["UNIFIED_PAGE_SCHEMA_SHA256"])

    def test_example_render_rebinds_only_the_derived_binding(self) -> None:
        authority = self.module.derived_declaration()
        path = self.module.example_files()[0]
        content = path.read_text(encoding="utf-8")
        broken = content.replace(
            f'"schemaSha256": "{authority["UNIFIED_PAGE_SCHEMA_SHA256"]}"',
            '"schemaSha256": "' + "0" * 64 + '"',
        )
        # Repairing with the authority reproduces the committed bytes exactly, so
        # the render touched only the derived value and no surrounding formatting.
        self.assertEqual(self.module.render_example_declaration(broken, authority), content)

    def test_canonical_examples_seal_their_own_body(self) -> None:
        authority = self.module.load_lifecycle_authority()
        files = self.module.example_files()
        self.assertTrue(files)
        for path in files:
            with self.subTest(example=path.name):
                content = path.read_text(encoding="utf-8")
                derived = self.module.derived_example_integrity(content, authority)
                self.assertEqual(self.module.example_integrity_drift(content, derived), {})

    def test_a_stale_body_seal_is_detected_and_rebound(self) -> None:
        authority = self.module.load_lifecycle_authority()
        path = self.module.example_files()[0]
        content = path.read_text(encoding="utf-8")
        derived = self.module.derived_example_integrity(content, authority)
        stale = content.replace(f'"contractSha256": "{derived}"', '"contractSha256": "' + "0" * 64 + '"')
        self.assertNotEqual(stale, content)
        drift = self.module.example_integrity_drift(stale, derived)
        self.assertEqual(sorted(drift), ["contractSha256"])
        self.assertEqual(drift["contractSha256"]["declared"], "0" * 64)
        self.assertEqual(self.module.render_example_integrity(stale, derived), content)

    def test_the_body_seal_is_recomputed_from_the_payload_not_the_file_bytes(self) -> None:
        authority = self.module.load_lifecycle_authority()
        path = self.module.example_files()[0]
        content = path.read_text(encoding="utf-8")
        derived = self.module.derived_example_integrity(content, authority)
        # Reformatting the file must not change the seal: it covers the semantic
        # payload (meta excluded), not the stored bytes.
        self.assertEqual(
            self.module.derived_example_integrity(json.dumps(json.loads(content)), authority),
            derived,
        )

    def test_example_render_preserves_a_document_without_a_definition(self) -> None:
        authority = self.module.derived_declaration()
        self.assertEqual(self.module.render_example_declaration("{}", authority), "{}")
        self.assertEqual(self.module.example_definition_drift("{}", authority), {})

    def test_derived_sha256_binds_the_normative_schema_bytes(self) -> None:
        import hashlib

        expected = hashlib.sha256(self.module.SCHEMA.read_bytes()).hexdigest()
        self.assertEqual(self.module.derived_declaration()["UNIFIED_PAGE_SCHEMA_SHA256"], expected)


if __name__ == "__main__":
    unittest.main()
