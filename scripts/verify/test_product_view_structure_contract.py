from __future__ import annotations

import unittest

from scripts.contract.product_view_structure_common import (
    collect_references, manifest_digest, normalize_arch, policy_menu_rows, sha256_json,
)
from scripts.verify.product_view_structure_contract_guard import validate_manifest


class ProductViewStructureContractTests(unittest.TestCase):
    def test_semantic_normalization_is_attribute_order_stable(self):
        left = normalize_arch('<form string="A"><field name="name" required="1"/></form>', semantic=True)
        right = normalize_arch('<form string="A"><field required="1" name="name"/></form>', semantic=True)
        self.assertEqual(left, right)
        self.assertEqual(sha256_json(left), sha256_json(right))

    def test_semantic_hash_changes_with_field_order(self):
        left = normalize_arch('<tree><field name="name"/><field name="state"/></tree>', semantic=True)
        right = normalize_arch('<tree><field name="state"/><field name="name"/></tree>', semantic=True)
        self.assertNotEqual(sha256_json(left), sha256_json(right))

    def test_reference_collection_covers_fields_and_buttons(self):
        structure = normalize_arch('<form><field name="name"/><button name="action_done" type="object"/></form>', semantic=True)
        self.assertEqual(collect_references(structure), {"field_refs": ["name"], "action_refs": ["action_done"]})

    def test_policy_rows_deduplicate_product_projections(self):
        capability = {"enabled": True, "release_state": "released", "menu_xmlid": "x.menu", "res_model": "x.model"}
        policy = {"products": [{"capabilities": [capability]}, {"capabilities": [dict(capability)]}]}
        self.assertEqual(len(policy_menu_rows(policy)), 1)

    def test_guard_rejects_zero_surface_view_action(self):
        policy = {"products": [{"capabilities": [{"enabled": True, "release_state": "released", "menu_xmlid": "x.menu", "res_model": "x.model"}]}]}
        entries = [{"menu_xmlid": "x.menu", "status": "resolved_view_action", "declared_view_types": ["form"], "surfaces": []}]
        manifest = {
            "schema": "product_view_structure_contract/1.0.0",
            "authority": {"database_role": "clean_install", "demo_data": False},
            "summary": {"formal_menu_count": 1, "resolved_surface_count": 0, "error_count": 0},
            "entries": entries,
            "manifest_sha256": manifest_digest(entries),
        }
        errors = validate_manifest(manifest, policy)
        self.assertTrue(any("zero surfaces" in error for error in errors))
        self.assertTrue(any("non-zero" in error for error in errors))

    def test_schema_uses_semantic_version_and_has_no_v1_alias(self):
        from scripts.contract.product_view_structure_common import SCHEMA

        self.assertEqual(SCHEMA, "product_view_structure_contract/1.0.0")
        self.assertNotIn("/v1", SCHEMA)


if __name__ == "__main__":
    unittest.main()
