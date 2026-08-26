from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.audit.generate_frontend_visual_projection_inventory import category, consumer_primitive_visual_chrome, evaluate_formal_gap_evidence, inspect_tree, normalized_source_root


class FrontendVisualProjectionInventoryTest(unittest.TestCase):
    def test_category_routes_formal_surfaces(self) -> None:
        self.assertEqual(category("views/LoginView.vue"), "public-entry")
        self.assertEqual(category("components/product-list/ProductListHeader.vue"), "collection")
        self.assertEqual(category("components/template/X2ManyRelationRenderer.vue"), "relations-x2many")
        self.assertEqual(category("pages/contractForm/CanonicalActionBar.vue"), "workflow")

    def test_inspection_separates_adapter_use_from_native_style_selector(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "frontend/apps/web/src/views/LoginView.vue"
            source.parent.mkdir(parents=True)
            source.write_text(
                "<template><ScInput /></template><style scoped>input:focus { color: red; }</style>",
                encoding="utf-8",
            )
            rows = inspect_tree(root)
            self.assertEqual(rows[0]["scComponents"], ["ScInput"])
            self.assertEqual(rows[0]["nativeStyleSelectors"], ["input:focus"])

    def test_source_root_must_be_explicit_repo_or_src(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "frontend/apps/web/src").mkdir(parents=True)
            self.assertEqual(normalized_source_root(root), root / "frontend/apps/web/src")
            with self.assertRaises(ValueError):
                normalized_source_root(root / "missing")

    def test_page_consumer_cannot_repaint_primitive_chrome(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "frontend/apps/web/src/views/LegacyView.vue"
            source.parent.mkdir(parents=True)
            source.write_text("<style scoped>.legacy :deep(.sc-btn) { background: red; }</style>", encoding="utf-8")
            self.assertEqual(consumer_primitive_visual_chrome(root), ["views/LegacyView.vue"])

    def test_formal_gap_cannot_self_assert_closed_without_machine_evidence(self) -> None:
        parity = {"gaps": [{"key": "overlay.dialog-drawer-focus-density", "status": "closed"}]}
        with tempfile.TemporaryDirectory() as directory:
            result = evaluate_formal_gap_evidence(parity, Path(directory))
        self.assertEqual(result[0]["status"], "invalid")
        self.assertFalse(result[0]["unitTargetWired"])

    def test_formal_gap_binding_rejects_generic_constant_pass_script(self) -> None:
        parity = {"gaps": [{"key": "overlay.dialog-drawer-focus-density", "status": "open"}]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "make").mkdir()
            (root / "make/frontend.mk").write_text(
                "verify.frontend.overlay_lifecycle.unit:\n\t@true\nverify.frontend.overlay_lifecycle.browser:\n\t@node scripts/verify/frontend_overlay_lifecycle_browser.mjs\n",
                encoding="utf-8",
            )
            source = root / "scripts/verify/frontend_overlay_lifecycle_browser.mjs"
            source.parent.mkdir(parents=True)
            source.write_text("const pass = true; if (!pass) process.exitCode = 1;", encoding="utf-8")
            result = evaluate_formal_gap_evidence(parity, root)
        self.assertEqual(result[0]["status"], "invalid")
        self.assertTrue(result[0]["browserFailureExitPresent"])

    def test_formal_gap_binding_requires_recipe_source_and_named_assertion(self) -> None:
        parity = {"gaps": [{"key": "overlay.dialog-drawer-focus-density", "status": "open"}]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "make").mkdir()
            (root / "make/frontend.mk").write_text(
                "verify.frontend.overlay_lifecycle.unit:\n\t@true\nverify.frontend.overlay_lifecycle.browser:\n\t@node scripts/verify/frontend_overlay_lifecycle_browser.mjs\n",
                encoding="utf-8",
            )
            source = root / "scripts/verify/frontend_overlay_lifecycle_browser.mjs"
            source.parent.mkdir(parents=True)
            source.write_text("const bodyLocked = false; if (!bodyLocked) process.exit(1);", encoding="utf-8")
            result = evaluate_formal_gap_evidence(parity, root)
        self.assertEqual(result[0]["status"], "bound")
        self.assertTrue(result[0]["browserTargetRecipeWired"])


if __name__ == "__main__":
    unittest.main()
