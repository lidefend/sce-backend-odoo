from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify import frontend_inline_style_guard as guard


class FrontendInlineStyleGuardTest(unittest.TestCase):
    def make_root(self, files: dict[str, str], allowlisted: list[str]) -> Path:
        root = Path(tempfile.mkdtemp())
        web = root / "frontend/apps/web/src"
        web.mkdir(parents=True)
        for relative, content in files.items():
            path = web / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        allowlist = root / "docs/architecture/inline_style_allowlist.json"
        allowlist.parent.mkdir(parents=True)
        allowlist.write_text(json.dumps({
            "schema_version": 1,
            "scope": "frontend/apps/web/src",
            "mechanisms": {
                "declared_layout": {
                    "owner": "frontend.test",
                    "reason": "runtime layout fixture",
                },
            },
            "files": {
                f"frontend/apps/web/src/{relative}": ["declared_layout"]
                for relative in allowlisted
            },
        }), encoding="utf-8")
        return root

    def test_registered_dynamic_style_passes(self) -> None:
        root = self.make_root(
            {"Probe.vue": "<template><div :style=\"layout\" /></template>"},
            ["Probe.vue"],
        )
        self.assertEqual(guard.inspect(root)["errors"], [])

    def test_unregistered_dynamic_style_fails(self) -> None:
        root = self.make_root(
            {"Probe.vue": "<template><div :style=\"layout\" /></template>"},
            [],
        )
        errors = guard.inspect(root)["errors"]
        self.assertTrue(any("unregistered inline-style site" in error for error in errors))

    def test_external_html_template_dynamic_style_is_detected(self) -> None:
        root = self.make_root(
            {"template.html": "<section :style=\"layout\" />"},
            ["template.html"],
        )
        result = guard.inspect(root)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["files"], ["frontend/apps/web/src/template.html"])

    def test_v_bind_style_forms_are_detected(self) -> None:
        root = self.make_root(
            {"Probe.vue": '<template><div v-bind:style="layout" /><Panel v-bind:layout-style="layout" /></template>'},
            ["Probe.vue"],
        )
        self.assertEqual(guard.inspect(root)["errors"], [])

    def test_literal_static_style_fails_even_when_registered(self) -> None:
        root = self.make_root(
            {"Probe.vue": '<template><div style="color: red" /></template>'},
            ["Probe.vue"],
        )
        errors = guard.inspect(root)["errors"]
        self.assertTrue(any("literal static inline style" in error for error in errors))

    def test_component_style_prop_and_script_style_are_detected(self) -> None:
        root = self.make_root(
            {
                "Probe.vue": (
                    '<template><Panel :layout-style="layout" /></template>'
                    "<script setup>const cell = () => h('div', { style: indent })</script>"
                ),
                "List.ts": "const cell = () => ({ style: columnStyle(field) });\n",
            },
            ["Probe.vue", "List.ts"],
        )
        result = guard.inspect(root)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["files"], [
            "frontend/apps/web/src/List.ts",
            "frontend/apps/web/src/Probe.vue",
        ])

    def test_stale_allowlist_entry_fails(self) -> None:
        root = self.make_root(
            {"Probe.vue": "<template><div /></template>"},
            ["Probe.vue"],
        )
        errors = guard.inspect(root)["errors"]
        self.assertTrue(any("stale inline-style allowlist entry" in error for error in errors))

    def test_css_style_properties_and_intl_style_do_not_match(self) -> None:
        root = self.make_root(
            {
                "Probe.vue": "<template><ul /></template><style>.x{list-style:none}</style>",
                "values.ts": "const format = new Intl.NumberFormat('zh-CN', { style: 'currency' });\n",
            },
            [],
        )
        self.assertEqual(guard.inspect(root)["errors"], [])


if __name__ == "__main__":
    unittest.main()
