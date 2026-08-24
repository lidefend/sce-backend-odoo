from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.verify.frontend_primitive_adapter_guard import PRIMITIVES, validate


class PrimitiveAdapterGuardTest(unittest.TestCase):
    def make_root(self) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        design = root / "frontend/apps/web/src/components/design-system"
        design.mkdir(parents=True)
        (design / "index.ts").write_text(
            "\n".join(f"export {{ default as {name} }} from './{name}.vue';" for name in PRIMITIVES),
            encoding="utf-8",
        )
        (design / "tdesignPrimitiveBridge.ts").write_text(
            "export { Input } from 'tdesign-vue-next/es/input';\n", encoding="utf-8"
        )
        for name in PRIMITIVES:
            modal_contract = "<!-- useModalLifecycle role=\"dialog\" aria-modal=\"true\" -->" if name in {"ScDialog", "ScDrawer"} else ""
            (design / f"{name}.vue").write_text(
                f'<template><div data-semantic-component="{name}" data-semantic-layer="primitive" /></template>{modal_contract}\n',
                encoding="utf-8",
            )
        return root

    def test_valid_adapter_surface_passes(self) -> None:
        self.assertEqual(validate(self.make_root()), [])

    def test_missing_component_fails(self) -> None:
        root = self.make_root()
        (root / "frontend/apps/web/src/components/design-system/ScInput.vue").unlink()
        self.assertTrue(any("missing primitive source" in error for error in validate(root)))

    def test_private_tdesign_import_fails(self) -> None:
        root = self.make_root()
        bridge = root / "frontend/apps/web/src/components/design-system/tdesignPrimitiveBridge.ts"
        bridge.write_text("export { Input } from 'tdesign-vue-next/src/input';\n", encoding="utf-8")
        self.assertTrue(any("private path" in error for error in validate(root)))

    def test_missing_semantic_identity_fails(self) -> None:
        root = self.make_root()
        source = root / "frontend/apps/web/src/components/design-system/ScButton.vue"
        source.write_text("<template><button /></template>\n", encoding="utf-8")
        errors = validate(root)
        self.assertTrue(any("ScButton missing exact semantic" in error for error in errors))
        self.assertTrue(any("ScButton missing primitive layer" in error for error in errors))

    def test_business_identity_fails(self) -> None:
        root = self.make_root()
        source = root / "frontend/apps/web/src/components/design-system/ScTable.vue"
        source.write_text(
            '<template><div data-semantic-component="ScTable" data-semantic-layer="primitive">payment.request</div></template>\n',
            encoding="utf-8",
        )
        self.assertTrue(any("business-specific" in error for error in validate(root)))

    def test_modal_without_shared_lifecycle_fails(self) -> None:
        root = self.make_root()
        source = root / "frontend/apps/web/src/components/design-system/ScDrawer.vue"
        source.write_text(
            '<template><aside data-semantic-component="ScDrawer" data-semantic-layer="primitive" /></template>\n',
            encoding="utf-8",
        )
        self.assertTrue(any("shared modal lifecycle" in error for error in validate(root)))


if __name__ == "__main__":
    unittest.main()
