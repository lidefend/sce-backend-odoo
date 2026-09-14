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

    def test_task_floorplan_cannot_fold_editable_supplementary_regions_by_default(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ObjectTaskPage.vue":
                return value.replace(
                    'data-supplementary-presentation="direct"',
                    'data-supplementary-presentation="folded"',
                    1,
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("governed information organization" in item for item in validate()))

    def test_relation_floorplan_requires_named_region_semantics(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ObjectTaskPage.vue":
                return value.replace('role="region"', 'data-role-removed', 1)
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any('role="region"' in item for item in validate()))

    def test_task_floorplan_keeps_editable_facts_before_relation_details(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "ObjectTaskPage.vue":
                return value.replace(
                    'data-floorplan-region="supplementary-input"',
                    'data-floorplan-region="relation-placeholder"',
                    1,
                ).replace(
                    'data-floorplan-region="relation"',
                    'data-floorplan-region="supplementary-input"',
                    1,
                ).replace(
                    'data-floorplan-region="relation-placeholder"',
                    'data-floorplan-region="relation"',
                    1,
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(any("after relation details" in item for item in validate()))


if __name__ == "__main__":
    unittest.main()
