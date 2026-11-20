# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from psycopg2 import IntegrityError


@tagged("post_install", "-at_install", "sc_gate", "product_job")
class TestProductJob(TransactionCase):
    def test_job_entry_uses_native_authority_and_product_fields(self):
        job = self.env["hr.job"].create({"name": "项目成本经理", "sc_job_code": "COST-MGR", "sc_responsibility": "负责项目成本计划与分析"})
        self.assertEqual(job.sc_job_code, "COST-MGR")
        action = self.env.ref("smart_construction_core.action_sc_product_job_management_v1")
        self.assertEqual(action.res_model, "hr.job")
        views = {row.view_mode: row.view_id for row in action.view_ids}
        self.assertEqual(views["form"], self.env.ref("smart_construction_core.view_sc_product_job_form_v1"))
        contract = self.env.ref("smart_construction_core.business_config_contract_product_job_form_v1")
        self.assertEqual(contract.action_id, action)

    def test_job_code_is_unique_within_company(self):
        self.env["hr.job"].create({
            "name": "项目成本经理",
            "sc_job_code": "COST-MGR",
            "company_id": self.env.company.id,
        })

        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self.env["hr.job"].create({
                "name": "重复岗位",
                "sc_job_code": "COST-MGR",
                "company_id": self.env.company.id,
            })

        self.assertEqual(
            self.env["hr.job"].search_count([
                ("sc_job_code", "=", "COST-MGR"),
                ("company_id", "=", self.env.company.id),
            ]),
            1,
        )
