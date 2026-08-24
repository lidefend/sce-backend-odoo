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


from pathlib import Path

if __name__ == "__main__":
    unittest.main()
