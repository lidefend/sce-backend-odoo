import unittest
from view_orchestration_product_boundary_guard import valid_form_composition


class FormCompositionBoundaryTest(unittest.TestCase):
    def test_native_permission_annotations_are_nonstructural(self):
        self.assertTrue(valid_form_composition({"composition_mode": "native_semantic_surface", "fields": [{"name": "state", "readonly": True}]}))

    def test_native_mode_rejects_structural_declarations(self):
        for payload in ({"fields": [{"name": "state", "section": "main"}]}, {"sections": [{"name": "main"}]}, {"layout": {"columns": 2}}):
            with self.subTest(payload=payload):
                self.assertFalse(valid_form_composition({"composition_mode": "native_semantic_surface", **payload}))

    def test_unknown_mode_is_rejected(self):
        self.assertFalse(valid_form_composition({"composition_mode": "unknown", "fields": [{"name": "state"}]}))

    def test_declared_entry_structure_is_supported(self):
        self.assertTrue(valid_form_composition({"composition_mode": "entry_semantic_surface", "fields": [{"name": "state", "section": "main"}]}))


if __name__ == "__main__":
    unittest.main()
