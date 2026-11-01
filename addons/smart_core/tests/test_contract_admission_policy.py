# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from odoo.addons.smart_core.core import contract_admission_policy as policy


class TestContractAdmissionPolicy(unittest.TestCase):
    def test_admitted_fields_keep_occurrence_and_raw_modifiers(self):
        self.assertIn("native_locator", policy.ADMITTED_FIELDS)
        self.assertIn("modifiers_raw", policy.ADMITTED_FIELDS)
        self.assertIn("field_occurrences", policy.ADMITTED_FIELDS)

    def test_forbidden_inference_blocks_order_and_type_guesses(self):
        self.assertIn("primary_owner_from_occurrence_order", policy.FORBIDDEN_INFERENCE)
        self.assertIn("business_role_from_orm_type", policy.FORBIDDEN_INFERENCE)
        self.assertIn("identity_from_field_name", policy.FORBIDDEN_INFERENCE)

    def test_manager_id_lifecycle_keeps_relation_and_hydration(self):
        labels = policy.classify_field_lifecycle(
            in_view=True,
            in_named_group=True,
            needs_hydration=True,
            is_technical_dependency=False,
            has_relation_capability=True,
        )
        self.assertIn("ViewField", labels)
        self.assertIn("BusinessField", labels)
        self.assertIn("HydrationField", labels)
        self.assertIn("RelationField", labels)
        self.assertNotIn("TechnicalDependency", labels)

    def test_undeclared_business_role_is_not_guessed(self):
        role = policy.business_role_for(
            native_group="sc_project_information_responsible",
            declared_semantics={},
        )
        self.assertIs(role, policy.NOT_DECLARED)

    def test_admission_rejects_undeclared_business_ownership(self):
        result = policy.validate_admission(
            field_code="manager_id",
            in_view=True,
            in_named_group=True,
            business_role_declared=False,
        )
        self.assertIn("ViewField", result.admitted)
        self.assertNotIn("BusinessField", result.admitted)


if __name__ == "__main__":
    unittest.main()

