import unittest
from unittest.mock import patch

from scripts.verify.frontend_product_page_header_guard import validate


class ProductPageHeaderGuardTest(unittest.TestCase):
    def test_repository_contract_passes(self):
        self.assertEqual(validate(), [])

    def test_missing_semantic_marker_fails(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            return value.replace("data-product-page-header", "data-removed") if path.name == "ProductPageHeader.vue" else value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("data-product-page-header" in item for item in validate()))

    def test_floorplan_decision_mode_rendering_required(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "contractFormHeaderCanonicalActions.ts":
                return value.replace("input.floorplan?.decisionMode", "input.floorplan?.removedDecisionMode")
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertIn(
                "canonical header action floorplan rendering misses input.floorplan?.decisionMode",
                validate(),
            )

    def test_content_heading_authority_is_required(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "index.ts" and path.parent.name == "router":
                return value.replace(
                    "name: 'api-key-management', component:",
                    "name: 'api-key-management', pageHeadingOwnerRemoved: true, component:",
                ).replace(
                    "meta: { layout: 'shell', pageHeadingOwner: 'content' } },\n    { path: '/a/:actionId'",
                    "meta: { layout: 'shell' } },\n    { path: '/a/:actionId'",
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertIn(
                "page-header route does not declare content heading authority: api-key-management",
                validate(),
            )

    def test_low_code_query_cannot_override_content_heading_authority(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "AppShell.vue":
                return value.replace(
                    "const contentOwnsPageHeading",
                    "const formDesignerKeepsHeadline = BUSINESS_CONFIG_MODES.lowCode;\nconst contentOwnsPageHeading",
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertIn(
                "AppShell must not override content heading authority for low-code form routes",
                validate(),
            )


from pathlib import Path

if __name__ == "__main__":
    unittest.main()
