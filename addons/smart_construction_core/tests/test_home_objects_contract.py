# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.smart_construction_core.core_extension import get_system_init_fact_contributions
from odoo.addons.smart_construction_core.core_extension_system_init_rows import build_home_object_rows


@tagged("post_install", "-at_install", "home_objects_contract")
class TestHomeObjectsContract(TransactionCase):
    def test_rows_only_reference_declared_business_records(self):
        rows = build_home_object_rows(self.env)
        self.assertTrue(rows, "demo database must expose project, contract or payment rows")
        allowed_models = {"project.project", "construction.contract", "payment.request"}
        for row in rows:
            self.assertIn(row["model"], allowed_models)
            self.assertGreater(row["record_id"], 0)
            self.assertTrue(row["route"].startswith("/r/"))
            self.assertTrue(row["title"])
            self.assertEqual(row["authority"], "smart_construction_core.home_objects.v1")

    def test_system_init_contribution_exports_home_objects(self):
        contribution = get_system_init_fact_contributions(self.env, self.env.user)
        self.assertIsInstance(contribution, dict)
        collections = contribution["facts"]["workspace_collections"]
        self.assertIn("home_objects", collections)
        self.assertIsInstance(collections["home_objects"], list)
