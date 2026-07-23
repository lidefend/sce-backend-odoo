# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "r11f2_tax_certificate")
class TestTaxCertificateRegistration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create({"name": "R11F2 Company B"})

        def create_user(login, groups, companies=None):
            companies = companies or cls.company_a
            company_ids = companies.ids if hasattr(companies, "ids") else [companies.id]
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@example.com",
                    "company_id": company_ids[0],
                    "company_ids": [(6, 0, company_ids)],
                    "groups_id": [(6, 0, [cls.env.ref(xmlid).id for xmlid in groups])],
                }
            )

        cls.project_member = create_user(
            "r11f2.project.member",
            ["smart_construction_core.group_sc_cap_project_read"],
        )
        cls.finance_read = create_user(
            "r11f2.finance.read",
            ["smart_construction_core.group_sc_cap_finance_read"],
        )
        cls.finance_user = create_user(
            "r11f2.finance.user",
            [
                "smart_construction_core.group_sc_cap_project_read",
                "smart_construction_core.group_sc_cap_finance_user",
            ],
        )
        cls.finance_manager = create_user(
            "r11f2.finance.manager",
            [
                "smart_construction_core.group_sc_cap_project_read",
                "smart_construction_core.group_sc_cap_finance_manager",
            ],
        )
        cls.regular_user = create_user("r11f2.regular", ["base.group_user"])

        cls.project_member_a = cls.env["project.project"].create(
            {"name": "R11F2 Member Project", "company_id": cls.company_a.id, "user_id": cls.finance_user.id}
        )
        cls.project_member_a.message_subscribe(partner_ids=[cls.project_member.partner_id.id])
        cls.project_other_a = cls.env["project.project"].create(
            {"name": "R11F2 Other Project", "company_id": cls.company_a.id}
        )
        cls.project_b = cls.env["project.project"].create(
            {"name": "R11F2 Company B Project", "company_id": cls.company_b.id}
        )

        cls.record_member_a = cls._create_registration(cls.project_member_a, "R11F2-A-001")
        cls.record_other_a = cls._create_registration(cls.project_other_a, "R11F2-A-002")
        cls.record_b = cls._create_registration(cls.project_b, "R11F2-B-001")

    @classmethod
    def _create_registration(cls, project, report_no):
        return cls.env["sc.tax.certificate.registration"].create(
            {
                "company_id": project.company_id.id,
                "project_id": project.id,
                "taxpayer_name": project.company_id.name,
                "taxpayer_identifier": f"TAX-{report_no}",
                "tax_report_management_no": report_no,
                "cross_region_business_address": "跨区域经营地址",
                "validity_start_date": "2026-01-01",
                "validity_end_date": "2026-12-31",
            }
        )

    def test_formal_action_menu_and_model_identity(self):
        action = self.env.ref("smart_construction_core.action_sc_tax_certificate_registration_user")
        menu = self.env.ref("smart_construction_core.menu_sc_tax_certificate_registration_user")
        self.assertEqual(action.res_model, "sc.tax.certificate.registration")
        self.assertEqual(menu.action, action)
        self.assertEqual(menu.parent_id, self.env.ref("smart_construction_core.menu_sc_invoice_tax_user_group"))
        self.assertNotIn("sc.legacy.payment.residual.fact", self.env.registry.models)

    def test_acl_is_role_explicit_and_not_public(self):
        model = self.env["sc.tax.certificate.registration"]
        self.assertTrue(model.with_user(self.project_member).check_access_rights("read", raise_exception=False))
        self.assertFalse(model.with_user(self.project_member).check_access_rights("write", raise_exception=False))
        self.assertTrue(model.with_user(self.finance_user).check_access_rights("create", raise_exception=False))
        self.assertFalse(model.with_user(self.finance_read).check_access_rights("write", raise_exception=False))
        with self.assertRaises(AccessError):
            model.with_user(self.regular_user).check_access_rights("read")

    def test_project_member_and_multicompany_record_rules(self):
        member_ids = set(
            self.env["sc.tax.certificate.registration"].with_user(self.project_member).search([]).ids
        )
        self.assertIn(self.record_member_a.id, member_ids)
        self.assertNotIn(self.record_other_a.id, member_ids)
        self.assertNotIn(self.record_b.id, member_ids)

        finance_ids = set(
            self.env["sc.tax.certificate.registration"].with_user(self.finance_user).search([]).ids
        )
        self.assertIn(self.record_member_a.id, finance_ids)
        self.assertIn(self.record_other_a.id, finance_ids)
        self.assertNotIn(self.record_b.id, finance_ids)

    def test_minimal_state_flow_and_direct_state_write_denial(self):
        record = self.record_member_a.with_user(self.finance_user)
        record.action_register()
        self.assertEqual(record.state, "registered")
        with self.assertRaises(ValidationError):
            record.write({"state": "completed"})
        record.with_user(self.finance_manager).action_complete()
        self.assertEqual(record.state, "completed")

    def test_failed_transition_rolls_back_transaction_savepoint(self):
        record = self.record_other_a
        with self.assertRaises(AccessError):
            with self.env.cr.savepoint():
                record.with_user(self.finance_user).action_register()
                record.with_user(self.finance_user).action_complete()
        self.env.invalidate_all()
        self.assertEqual(record.state, "draft")

    def test_invalid_validity_range_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["sc.tax.certificate.registration"].create(
                {
                    "company_id": self.company_a.id,
                    "project_id": self.project_member_a.id,
                    "taxpayer_name": "R11F2 Taxpayer",
                    "taxpayer_identifier": "R11F2-TAX-INVALID",
                    "tax_report_management_no": "R11F2-INVALID-DATE",
                    "cross_region_business_address": "跨区域经营地址",
                    "validity_start_date": "2026-12-31",
                    "validity_end_date": "2026-01-01",
                }
            )
