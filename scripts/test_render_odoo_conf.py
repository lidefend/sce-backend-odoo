#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("render_odoo_conf.py")
ROOT = SCRIPT.parents[1]
SPEC = importlib.util.spec_from_file_location("render_odoo_conf", SCRIPT)
assert SPEC and SPEC.loader
TARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TARGET)


class RenderOdooConfTests(unittest.TestCase):
    def test_source_mounted_runtime_exposes_product_version_authority(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("./VERSION:/opt/sce-product/VERSION:ro", compose)

    def test_runtime_entrypoint_always_uses_validated_renderer(self):
        entrypoint = (ROOT / "scripts" / "odoo-entrypoint.sh").read_text(encoding="utf-8")

        self.assertIn('python3 /usr/local/bin/render_odoo_conf.py "$TPL" "$OUT"', entrypoint)
        self.assertNotIn("envsubst <", entrypoint)

    def test_dev_omits_only_unavailable_addons_roots(self):
        rendered = (
            "[options]\n"
            "addons_path = /native,/mnt/product-addons,/mnt/source-addons,/mnt/test-addons\n"
            "db_name = sc_demo\n"
        )

        normalized, removed = TARGET.normalize_non_production_addons_path(
            rendered,
            environment="dev",
            is_directory=lambda value: value in {"/native", "/mnt/source-addons"},
        )

        self.assertIn("addons_path = /native,/mnt/source-addons\n", normalized)
        self.assertEqual(removed, ("/mnt/product-addons", "/mnt/test-addons"))

    def test_dev_prefers_candidate_source_over_embedded_product_copy(self):
        rendered = (
            "[options]\n"
            "addons_path = /native,/mnt/product-addons,/mnt/source-addons,/mnt/demo-addons\n"
        )

        normalized, removed = TARGET.normalize_non_production_addons_path(
            rendered,
            environment="dev",
            is_directory=lambda _value: True,
        )

        self.assertIn(
            "addons_path = /native,/mnt/source-addons,/mnt/product-addons,/mnt/demo-addons\n",
            normalized,
        )
        self.assertEqual(removed, ())

    def test_production_keeps_declared_roots_unchanged(self):
        rendered = "addons_path = /native,/mnt/product-addons,/mnt/customer-addons\n"

        normalized, removed = TARGET.normalize_non_production_addons_path(
            rendered,
            environment="prod",
            is_directory=lambda _value: False,
        )

        self.assertEqual(normalized, rendered)
        self.assertEqual(removed, ())

    def test_dev_fails_closed_when_no_addons_root_exists(self):
        with self.assertRaisesRegex(SystemExit, "No available addons_path entries"):
            TARGET.normalize_non_production_addons_path(
                "addons_path = /missing\n",
                environment="daily",
                is_directory=lambda _value: False,
            )


if __name__ == "__main__":
    unittest.main()
