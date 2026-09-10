import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.verify.frontend_official_icon_resource_guard import validate


class FrontendOfficialIconResourceGuardTest(unittest.TestCase):
    def test_repository_contract_passes(self):
        self.assertEqual(validate(), [])

    def test_handwritten_svg_path_fails(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            return value + "\n<svg><path /></svg>" if path.name == "ScIcon.vue" else value

        with patch("pathlib.Path.read_text", altered):
            self.assertIn("ScIcon must not maintain handwritten SVG path data", validate())

    def test_manual_visual_glyph_fails(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            return value + "\nconst forbidden = '📎';" if path.name == "scIcon.ts" else value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("manual visual glyph" in item for item in validate()))

    def test_manual_visual_glyph_in_ui_package_fails(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "SceneHierarchySurface.vue":
                return value + "\n<span aria-hidden=\"true\">•</span>"
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("frontend/packages/ui/src" in item and "manual character icon" in item for item in validate()))

    def test_quoted_plus_visual_glyph_fails(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            return value + "\n<span>{{ expanded ? '−' : '+' }}</span>" if path.name == "scIcon.ts" else value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("manual character icon" in item for item in validate()))

    def test_public_package_root_is_required(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "icons.ts":
                return value.replace("from 'tdesign-icons-vue-next'", "from 'tdesign-icons-vue-next/esm/icons'")
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("package public root API" in item for item in validate()))


if __name__ == "__main__":
    unittest.main()
