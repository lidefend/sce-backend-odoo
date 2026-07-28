# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "admin_vis_p3_project_record_rule_orm")
class TestUmP1ContractSettlementVisibilityContractOrm(TransactionCase):
    """Real-ORM evidence for project-personal contract settlement visibility."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create({"name": "UM-P1 S06 Company B"})
        base_user = cls.env.ref("base.group_user")
        settlement_user = cls.env.ref(
            "smart_construction_core.group_sc_role_settlement_user"
        )
        settlement_manager = cls.env.ref(
            "smart_construction_core.group_sc_role_settlement_manager"
        )
        config_admin = cls.env.ref(
            "smart_construction_core.group_sc_cap_business_config_admin"
        )

        def create_user(name, login, group):
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": name,
                    "login": login,
                    "email": f"{login}@example.invalid",
                    "company_id": cls.company_a.id,
                    "company_ids": [(6, 0, [cls.company_a.id])],
                    "groups_id": [(6, 0, [base_user.id, group.id])],
                }
            )

        cls.ordinary_user = create_user(
            "UM-P1 S06 settlement user",
            "um_p1_s06_settlement_user",
            settlement_user,
        )
        cls.manager_user = create_user(
            "UM-P1 S06 settlement manager",
            "um_p1_s06_settlement_manager",
            settlement_manager,
        )
        cls.config_admin_user = create_user(
            "UM-P1 S06 business config administrator",
            "um_p1_s06_config_admin",
            config_admin,
        )
        setup_context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company_a.id, cls.company_b.id],
            "mail_create_nosubscribe": True,
            "mail_notify_noemail": True,
            "mail_auto_subscribe_no_notify": True,
            "tracking_disable": True,
        }
        Project = cls.env["project.project"].with_context(setup_context)
        project_values = {"privacy_visibility": "followers"}
        cls.owned_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S06 owned project",
                "company_id": cls.company_a.id,
                "user_id": cls.ordinary_user.id,
            }
        )
        cls.followed_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S06 followed project",
                "company_id": cls.company_a.id,
                "user_id": cls.env.user.id,
            }
        )
        cls.followed_project.message_subscribe(
            partner_ids=[cls.ordinary_user.partner_id.id]
        )
        cls.unrelated_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S06 unrelated project",
                "company_id": cls.company_a.id,
                "user_id": cls.env.user.id,
            }
        )
        cls.cross_company_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S06 cross-company project",
                "company_id": cls.company_b.id,
                "user_id": cls.env.user.id,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "UM-P1 S06 synthetic settlement partner"}
        )
        tax = cls.env["account.tax"].search([], limit=1)
        if not tax:
            tax = cls.env["account.tax"].create(
                {
                    "name": "UM-P1 S06 contract tax",
                    "amount": 0.0,
                    "amount_type": "percent",
                    "type_tax_use": "sale",
                }
            )
        cls.contracts = {
            key: cls.env["construction.contract"].with_context(
                setup_context
            ).create(
                {
                    "subject": f"UM-P1 S06 {key} contract",
                    "type": "out",
                    "project_id": project.id,
                    "company_id": project.company_id.id,
                    "partner_id": cls.partner.id,
                    "tax_id": tax.id,
                }
            )
            for key, project in (
                ("owned", cls.owned_project),
                ("followed", cls.followed_project),
                ("unrelated", cls.unrelated_project),
                ("cross_company", cls.cross_company_project),
            )
        }
        cls.records = {
            "owned": cls._create_settlement(
                cls.owned_project,
                cls.company_a,
                cls.contracts["owned"],
                "owned",
            ),
            "followed": cls._create_settlement(
                cls.followed_project,
                cls.company_a,
                cls.contracts["followed"],
                "followed",
            ),
            "unrelated": cls._create_settlement(
                cls.unrelated_project,
                cls.company_a,
                cls.contracts["unrelated"],
                "unrelated",
                entry_user=cls.ordinary_user,
            ),
            "cross_company": cls._create_settlement(
                cls.cross_company_project,
                cls.company_b,
                cls.contracts["cross_company"],
                "cross-company",
            ),
        }
        cls.nonexistent_id = max(record.id for record in cls.records.values()) + 1000000
        caller_context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company_a.id],
            "tracking_disable": True,
        }
        cls.ordinary_env = cls.env(user=cls.ordinary_user, context=caller_context)
        cls.manager_env = cls.env(user=cls.manager_user, context=caller_context)
        cls.config_admin_env = cls.env(
            user=cls.config_admin_user,
            context=caller_context,
        )

    @classmethod
    def _create_settlement(
        cls,
        project,
        company,
        contract,
        label,
        *,
        entry_user=None,
    ):
        values = {
            "project_id": project.id,
            "company_id": company.id,
            "contract_id": contract.id,
            "partner_id": cls.partner.id,
            "settlement_type": "in",
            "title": f"UM-P1 S06 {label}",
            "line_ids": [(0, 0, {"name": label, "amount": 1.0})],
        }
        if entry_user:
            values["entry_user_id"] = entry_user.id
        return cls.env["sc.settlement.order"].with_context(
            allowed_company_ids=[cls.company_a.id, cls.company_b.id],
            tracking_disable=True,
        ).create(values)

    def test_ordinary_user_sees_owned_and_followed_projects_only(self):
        visible = self.ordinary_env["sc.settlement.order"].search(
            [("id", "in", [record.id for record in self.records.values()])]
        )
        self.assertEqual(
            set(visible.ids),
            {self.records["owned"].id, self.records["followed"].id},
        )

    def test_entry_user_does_not_grant_visibility(self):
        self.assertEqual(
            self.records["unrelated"].entry_user_id,
            self.ordinary_user,
        )
        self.assertFalse(
            self.ordinary_env["sc.settlement.order"].search(
                [("id", "=", self.records["unrelated"].id)],
                limit=1,
            )
        )

    def test_user_writes_owned_record_but_not_unrelated_record(self):
        self.records["owned"].with_user(self.ordinary_user).with_context(
            allowed_company_ids=[self.company_a.id]
        ).write({"note": "authorized"})
        with self.assertRaises(AccessError):
            self.records["unrelated"].with_user(self.ordinary_user).with_context(
                allowed_company_ids=[self.company_a.id]
            ).write({"note": "unauthorized"})

    def test_unauthorized_cross_company_and_nonexistent_are_equivalent(self):
        observations = []
        for record_id in (
            self.records["unrelated"].id,
            self.records["cross_company"].id,
            self.nonexistent_id,
        ):
            result = self.ordinary_env["sc.settlement.order"].search(
                [("id", "=", record_id)],
                limit=1,
            )
            observations.append((bool(result), len(result)))
        self.assertEqual(observations, [(False, 0), (False, 0), (False, 0)])

    def test_direct_unauthorized_read_is_rejected(self):
        with self.assertRaises(AccessError):
            self.ordinary_env["sc.settlement.order"].browse(
                self.records["unrelated"].id
            ).read(["id", "title"])

    def test_manager_is_company_scoped_not_project_scoped(self):
        visible = self.manager_env["sc.settlement.order"].search(
            [("id", "in", [record.id for record in self.records.values()])]
        )
        self.assertEqual(
            set(visible.ids),
            {
                self.records["owned"].id,
                self.records["followed"].id,
                self.records["unrelated"].id,
            },
        )

    def test_business_config_administrator_keeps_explicit_all_contract(self):
        visible = self.config_admin_env["sc.settlement.order"].search(
            [("id", "in", [record.id for record in self.records.values()])]
        )
        self.assertEqual(set(visible.ids), {record.id for record in self.records.values()})

    def test_no_scope_search_does_not_fall_back_to_all_records(self):
        visible = self.ordinary_env["sc.settlement.order"].search([])
        self.assertIn(self.records["owned"], visible)
        self.assertIn(self.records["followed"], visible)
        self.assertNotIn(self.records["unrelated"], visible)
        self.assertNotIn(self.records["cross_company"], visible)
