from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify.frontend_primitive_port_guard import validate


class PrimitivePortGuardTest(unittest.TestCase):
    def make_root(self) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        port = root / "frontend/packages/ui/src/primitive-port"
        port.mkdir(parents=True)
        package = root / "frontend/packages/ui/package.json"
        package.write_text(json.dumps({
            "exports": {"./primitive-port": "./src/primitive-port/index.ts"},
        }), encoding="utf-8")
        for name in ("types", "events", "slots", "validation"):
            (port / f"{name}.ts").write_text("export {};\n", encoding="utf-8")
        (port / "index.ts").write_text(
            "".join(f"export * from './{name}';\n" for name in ("events", "slots", "types", "validation")),
            encoding="utf-8",
        )
        return root

    def test_valid_structure_passes(self) -> None:
        self.assertEqual(validate(self.make_root()), [])

    def test_missing_export_fails(self) -> None:
        root = self.make_root()
        package = root / "frontend/packages/ui/package.json"
        package.write_text('{"exports": {}}', encoding="utf-8")
        self.assertTrue(any("exports must expose" in error for error in validate(root)))

    def test_vendor_or_application_import_fails(self) -> None:
        root = self.make_root()
        source = root / "frontend/packages/ui/src/primitive-port/types.ts"
        source.write_text("import type { Button } from 'tdesign-vue-next';\n", encoding="utf-8")
        self.assertTrue(any("escapes the protocol boundary" in error for error in validate(root)))

    def test_as_compatibility_proof_fails(self) -> None:
        root = self.make_root()
        source = root / "frontend/packages/ui/src/primitive-port/types.ts"
        source.write_text("declare const component: unknown;\nconst proof = component as PrimitiveComponent<{}, {}, {}>;\n", encoding="utf-8")
        self.assertTrue(any("forbidden compatibility" in error for error in validate(root)))

    def test_bundle_cannot_load_scene_or_vendor(self) -> None:
        root = self.make_root()
        metafile = root / "metafile.json"
        metafile.write_text(json.dumps({
            "inputs": {
                "frontend/packages/ui/src/primitive-port/index.ts": {"bytes": 1},
                "frontend/packages/ui/src/components/SceneObjectPage.vue": {"bytes": 1},
            },
        }), encoding="utf-8")
        self.assertTrue(any("forbidden input" in error for error in validate(root, metafile)))


if __name__ == "__main__":
    unittest.main()
