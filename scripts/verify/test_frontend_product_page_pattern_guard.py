import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.verify.frontend_product_page_pattern_guard import validate


class ProductPagePatternGuardTest(unittest.TestCase):
    def test_repository_contract_passes(self):
        self.assertEqual(validate(), [])

    def test_missing_pattern_identity_fails(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            return value.replace('data-product-page-pattern="task-form"', 'data-pattern-removed') if path.name == "TaskFormPattern.vue" else value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("task-form" in item for item in validate()))

    def test_task_floorplan_cannot_expand_supplementary_regions_by_default(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ObjectTaskPage.vue":
                return value.replace('title="补充信息"', 'data-title-removed', 1)
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("professional disclosure" in item for item in validate()))


if __name__ == "__main__":
    unittest.main()
