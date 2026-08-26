from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.audit.generate_frontend_visual_projection_inventory import category, inspect_tree, normalized_source_root


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


if __name__ == "__main__":
    unittest.main()
