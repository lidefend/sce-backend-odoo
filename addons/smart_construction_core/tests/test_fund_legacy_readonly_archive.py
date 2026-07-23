# -*- coding: utf-8 -*-
from ast import literal_eval

from lxml import etree
from psycopg2 import IntegrityError

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


SOURCE_MODEL = "online_old_legacy_direct:direct_acceptance"
OIL_TABLE = "direct_acceptance:油卡登记"
RECHARGE_TABLE = "direct_acceptance:充值登记"


@tagged("post_install", "-at_install", "sc_gate", "sc_perm", "fund_legacy_archive")
class TestFundLegacyReadonlyArchive(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Archive Other Company"})

        def create_user(login, group_xmlid):
            group_ids = [
                cls.env.ref("base.group_user").id,
                cls.env.ref(group_xmlid).id,
            ]
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@test.local",
                    "company_id": cls.company.id,
                    "company_ids": [(6, 0, [cls.company.id])],
                    "groups_id": [(6, 0, group_ids)],
                }
            )

        cls.finance_read = create_user(
            "fund_archive_finance_read",
            "smart_construction_core.group_sc_cap_finance_read",
        )
        cls.business_user = create_user(
            "fund_archive_business_user",
            "smart_construction_core.group_sc_cap_business_initiator",
        )
        cls.finance_user = create_user(
            "fund_archive_finance_user",
            "smart_construction_core.group_sc_cap_finance_user",
        )
        cls.account = cls.env["sc.fund.account"].create(
            {"name": "Archive Account", "account_no": "ARCHIVE-001", "company_id": cls.company.id}
        )
        cls.other_account = cls.env["sc.fund.account"].with_company(cls.other_company).create(
            {
                "name": "Other Archive Account",
                "account_no": "ARCHIVE-OTHER-001",
                "company_id": cls.other_company.id,
            }
        )
        cls.oil = cls._create_archive_record("Archive Oil", OIL_TABLE, "oil-1", cls.company, cls.account)
        cls.recharge = cls._create_archive_record(
            "Archive Recharge", RECHARGE_TABLE, "recharge-1", cls.company, cls.account
        )
        cls.other_source = cls.env["sc.fund.account.operation"].create(
            {
                "name": "Unrelated Legacy Source",
                "operation_type": "fund_daily_report",
                "fund_account_id": cls.account.id,
                "operation_reason": "unrelated",
                "company_id": cls.company.id,
            }
        )
        cls.other_company_oil = cls._create_archive_record(
            "Other Company Archive Oil", OIL_TABLE, "oil-other-company", cls.other_company, cls.other_account
        )

    @classmethod
    def _create_archive_record(cls, name, source_table, legacy_record_id, company, account):
        record = cls.env["sc.fund.account.operation"].with_company(company).create(
            {
                "name": name,
                "operation_type": "fund_daily_report",
                "fund_account_id": account.id,
                "operation_reason": "historical archive fixture",
                "company_id": company.id,
            }
        )
        # Test-only fixture setup models a record that was imported before the
        # runtime immutability guard existed. No runtime context bypass exists.
        cls.env.cr.execute(
            """
            UPDATE sc_fund_account_operation
               SET legacy_source_model = %s,
                   legacy_source_table = %s,
                   legacy_record_id = %s,
                   legacy_document_state = '2',
                   creator_name = 'historical importer'
             WHERE id = %s
            """,
            (SOURCE_MODEL, source_table, legacy_record_id, record.id),
        )
        record.invalidate_recordset()
        return record

    @staticmethod
    def _domain(action):
        return literal_eval(action.domain)

    def test_actions_menus_views_and_domains_are_stable_and_distinct(self):
        oil_action = self.env.ref("smart_construction_core.action_sc_fuel_card_registration_formal")
        recharge_action = self.env.ref("smart_construction_core.action_sc_fuel_card_recharge_formal")
        oil_menu = self.env.ref("smart_construction_core.menu_sc_legacy_fuel_card_fact_acceptance")
        recharge_menu = self.env.ref(
            "smart_construction_core.menu_sc_legacy_fuel_card_recharge_fact_acceptance"
        )
        self.assertNotEqual(oil_action, recharge_action)
        self.assertNotEqual(oil_menu, recharge_menu)
        self.assertEqual(oil_menu.action, oil_action)
        self.assertEqual(recharge_menu.action, recharge_action)
        self.assertEqual(oil_action.res_model, "sc.fund.account.operation")
        self.assertEqual(recharge_action.res_model, "sc.fund.account.operation")
        self.assertEqual(
            self._domain(oil_action),
            [("legacy_source_model", "=", SOURCE_MODEL), ("legacy_source_table", "=", OIL_TABLE)],
        )
        self.assertEqual(
            self._domain(recharge_action),
            [("legacy_source_model", "=", SOURCE_MODEL), ("legacy_source_table", "=", RECHARGE_TABLE)],
        )
        self.assertNotEqual(oil_action.search_view_id, recharge_action.search_view_id)
        self.assertEqual(set(oil_action.view_ids.mapped("view_mode")), {"tree", "form"})
        self.assertEqual(set(recharge_action.view_ids.mapped("view_mode")), {"tree", "form"})
        finance_visible = self.env["ir.ui.menu"].with_user(self.finance_read)._visible_menu_ids()
        business_visible = self.env["ir.ui.menu"].with_user(self.business_user)._visible_menu_ids()
        self.assertTrue({oil_menu.id, recharge_menu.id}.issubset(finance_visible))
        self.assertFalse({oil_menu.id, recharge_menu.id}.intersection(business_visible))
        for action in (oil_action, recharge_action):
            self.assertTrue(action.with_user(self.finance_read).read(["name", "domain"]))
            self.assertEqual(
                literal_eval(action.context),
                {"create": False, "edit": False, "delete": False, "duplicate": False},
            )
            for view in action.view_ids.mapped("view_id"):
                arch = etree.fromstring(view.arch.encode())
                self.assertEqual(arch.get("create"), "false")
                self.assertEqual(arch.get("edit"), "false")
                self.assertEqual(arch.get("delete"), "false")
                self.assertEqual(arch.get("duplicate"), "false")
                self.assertFalse(arch.xpath(".//button[@type='object']"))
                if arch.tag in {"tree", "form"}:
                    field_names = set(arch.xpath(".//field/@name"))
                    self.assertTrue(
                        {"amount", "project_id", "fund_account_id", "legacy_document_state"}.issubset(
                            field_names
                        )
                    )
                if arch.tag == "form":
                    self.assertIn("attachment_ids", set(arch.xpath(".//field/@name")))

    def test_source_domains_are_isolated(self):
        Model = self.env["sc.fund.account.operation"]
        oil_action = self.env.ref("smart_construction_core.action_sc_fuel_card_registration_formal")
        recharge_action = self.env.ref("smart_construction_core.action_sc_fuel_card_recharge_formal")
        self.assertEqual(Model.search(self._domain(oil_action)), self.oil | self.other_company_oil)
        self.assertEqual(Model.search(self._domain(recharge_action)), self.recharge)
        self.assertNotIn(self.other_source, Model.search(self._domain(oil_action)))
        self.assertNotIn(self.other_source, Model.search(self._domain(recharge_action)))

    def test_finance_read_can_list_open_and_company_rule_is_preserved(self):
        Model = self.env["sc.fund.account.operation"].with_user(self.finance_read)
        visible = Model.search([("id", "in", (self.oil | self.recharge | self.other_company_oil).ids)])
        self.assertEqual(visible, self.oil | self.recharge)
        self.assertEqual(Model.browse(self.oil.id).read(["name", "amount"])[0]["name"], self.oil.name)

    def test_non_finance_role_cannot_read_archive(self):
        Model = self.env["sc.fund.account.operation"].with_user(self.business_user)
        self.assertFalse(Model.search([("id", "in", (self.oil | self.recharge).ids)]))
        with self.assertRaises(AccessError):
            Model.browse(self.oil.id).read(["name"])

    def test_archive_create_write_unlink_and_workflows_are_server_denied(self):
        Model = self.env["sc.fund.account.operation"]
        with self.assertRaises(AccessError):
            Model.create(
                {
                    "operation_type": "fund_daily_report",
                    "fund_account_id": self.account.id,
                    "operation_reason": "must fail",
                    "legacy_source_model": SOURCE_MODEL,
                    "legacy_source_table": OIL_TABLE,
                    "legacy_record_id": "oil-forbidden-create",
                }
            )
        with self.assertRaises(AccessError):
            self.oil.write({"note": "must fail"})
        with self.assertRaises(AccessError):
            self.oil.unlink()
        for method_name in ("action_confirm", "action_done", "action_cancel", "action_reset_draft"):
            with self.assertRaises(AccessError):
                getattr(self.oil, method_name)()

    def test_formal_fund_workflow_is_unaffected(self):
        Model = self.env["sc.fund.account.operation"].with_user(self.finance_user)
        record = Model.create(
            {
                "operation_type": "fund_daily_report",
                "fund_account_id": self.account.id,
                "operation_reason": "formal workflow",
            }
        )
        record.write({"note": "normal write remains available"})
        record.action_confirm()
        self.assertEqual(record.state, "confirmed")
        disposable = self.env["sc.fund.account.operation"].create(
            {
                "operation_type": "fund_daily_report",
                "fund_account_id": self.account.id,
                "operation_reason": "formal disposable",
            }
        )
        self.assertTrue(disposable.unlink())

    def test_ordinary_record_cannot_be_reclassified_as_archive(self):
        with self.assertRaises(AccessError):
            self.other_source.write(
                {"legacy_source_model": SOURCE_MODEL, "legacy_source_table": RECHARGE_TABLE}
            )

    def test_legacy_source_identity_remains_unique(self):
        duplicate = self.env["sc.fund.account.operation"].create(
            {
                "name": "Duplicate archive source",
                "operation_type": "fund_daily_report",
                "fund_account_id": self.account.id,
                "operation_reason": "must fail uniqueness",
            }
        )
        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self.env.cr.execute(
                """
                UPDATE sc_fund_account_operation
                   SET legacy_source_model = %s,
                       legacy_source_table = %s,
                       legacy_record_id = %s
                 WHERE id = %s
                """,
                (SOURCE_MODEL, OIL_TABLE, self.oil.legacy_record_id, duplicate.id),
            )
