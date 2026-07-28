# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "admin_vis_p3_project_record_rule_orm")
class TestUmP1CostLedgerVisibilityContractOrm(TransactionCase):
    """Real-ORM evidence for project-member cost-ledger visibility."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create({"name": "UM-P1 S07 Company B"})
        base_user = cls.env.ref("base.group_user")
        cost_manager = cls.env.ref(
            "smart_construction_core.group_sc_cap_cost_manager"
        )

        def create_user(name, login, groups):
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": name,
                    "login": login,
                    "email": f"{login}@example.invalid",
                    "company_id": cls.company_a.id,
                    "company_ids": [(6, 0, [cls.company_a.id])],
                    "groups_id": [(6, 0, [base_user.id, *[group.id for group in groups]])],
                }
            )

        cls.cost_user = create_user(
            "UM-P1 S07 cost manager",
            "um_p1_s07_cost_manager",
            [cost_manager],
        )
        cls.non_cost_user = create_user(
            "UM-P1 S07 non-cost user",
            "um_p1_s07_non_cost_user",
            [],
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
                "name": "UM-P1 S07 owned project",
                "company_id": cls.company_a.id,
                "user_id": cls.cost_user.id,
            }
        )
        cls.followed_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S07 followed project",
                "company_id": cls.company_a.id,
                "user_id": cls.env.user.id,
            }
        )
        cls.followed_project.message_subscribe(
            partner_ids=[cls.cost_user.partner_id.id]
        )
        cls.unrelated_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S07 unrelated project",
                "company_id": cls.company_a.id,
                "user_id": cls.env.user.id,
            }
        )
        cls.manager_only_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S07 manager-only project",
                "company_id": cls.company_a.id,
                "user_id": cls.env.user.id,
                "manager_id": cls.cost_user.id,
            }
        )
        cls.cross_company_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S07 cross-company project",
                "company_id": cls.company_b.id,
                "user_id": cls.cost_user.id,
            }
        )
        cls.non_cost_owned_project = Project.create(
            {
                **project_values,
                "name": "UM-P1 S07 non-cost owned project",
                "company_id": cls.company_a.id,
                "user_id": cls.non_cost_user.id,
            }
        )
        cls.cost_code = cls.env["project.cost.code"].create(
            {
                "name": "UM-P1 S07 synthetic cost",
                "code": "UM-P1-S07",
                "type": "other",
            }
        )
        cls.periods = {
            key: cls.env["project.cost.period"].with_context(setup_context).create(
                {"project_id": project.id, "period": "2026-07"}
            )
            for key, project in (
                ("owned", cls.owned_project),
                ("followed", cls.followed_project),
                ("unrelated", cls.unrelated_project),
                ("manager_only", cls.manager_only_project),
                ("cross_company", cls.cross_company_project),
                ("non_cost_owned", cls.non_cost_owned_project),
            )
        }
        cls.records = {
            key: cls._create_ledger(project, cls.periods[key], key)
            for key, project in (
                ("owned", cls.owned_project),
                ("followed", cls.followed_project),
                ("unrelated", cls.unrelated_project),
                ("manager_only", cls.manager_only_project),
                ("cross_company", cls.cross_company_project),
                ("non_cost_owned", cls.non_cost_owned_project),
            )
        }
        cls.nonexistent_id = max(record.id for record in cls.records.values()) + 1000000
        caller_context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company_a.id],
            "tracking_disable": True,
        }
        cls.cost_env = cls.env(user=cls.cost_user, context=caller_context)
        cls.non_cost_env = cls.env(user=cls.non_cost_user, context=caller_context)

    @classmethod
    def _create_ledger(cls, project, period, label):
        return cls.env["project.cost.ledger"].with_context(
            allowed_company_ids=[cls.company_a.id, cls.company_b.id],
            tracking_disable=True,
        ).create(
            {
                "project_id": project.id,
                "period_id": period.id,
                "period": period.period,
                "cost_code_id": cls.cost_code.id,
                "amount": 1.0,
                "note": f"UM-P1 S07 {label}",
            }
        )

    def test_cost_role_sees_responsible_and_followed_projects_only(self):
        visible = self.cost_env["project.cost.ledger"].search(
            [("id", "in", [record.id for record in self.records.values()])]
        )
        self.assertEqual(
            set(visible.ids),
            {self.records["owned"].id, self.records["followed"].id},
        )

    def test_manager_field_alone_does_not_grant_visibility(self):
        self.assertEqual(self.manager_only_project.manager_id, self.cost_user)
        self.assertFalse(
            self.cost_env["project.cost.ledger"].search(
                [("id", "=", self.records["manager_only"].id)],
                limit=1,
            )
        )

    def test_non_cost_user_does_not_gain_model_access(self):
        with self.assertRaises(AccessError):
            self.non_cost_env["project.cost.ledger"].search(
                [("id", "=", self.records["non_cost_owned"].id)],
                limit=1,
            )

    def test_follower_addition_and_removal_change_visibility(self):
        project = self.unrelated_project
        record = self.records["unrelated"]
        self.assertFalse(
            self.cost_env["project.cost.ledger"].search(
                [("id", "=", record.id)],
                limit=1,
            )
        )
        project.message_subscribe(partner_ids=[self.cost_user.partner_id.id])
        self.assertTrue(
            self.cost_env["project.cost.ledger"].search(
                [("id", "=", record.id)],
                limit=1,
            )
        )
        project.message_unsubscribe(partner_ids=[self.cost_user.partner_id.id])
        self.assertFalse(
            self.cost_env["project.cost.ledger"].search(
                [("id", "=", record.id)],
                limit=1,
            )
        )

    def test_create_and_write_require_visible_target_project(self):
        created = self.cost_env["project.cost.ledger"].create(
            {
                "project_id": self.owned_project.id,
                "period_id": self.periods["owned"].id,
                "period": "2026-07",
                "cost_code_id": self.cost_code.id,
                "amount": 2.0,
                "note": "authorized create",
            }
        )
        self.assertEqual(created.company_id, self.company_a)
        with self.assertRaises(AccessError):
            self.cost_env["project.cost.ledger"].create(
                {
                    "project_id": self.unrelated_project.id,
                    "period_id": self.periods["unrelated"].id,
                    "period": "2026-07",
                    "cost_code_id": self.cost_code.id,
                    "amount": 2.0,
                }
            )
        with self.assertRaises(AccessError):
            created.write(
                {
                    "project_id": self.unrelated_project.id,
                    "period_id": self.periods["unrelated"].id,
                }
            )

    def test_delete_obeys_acl_project_and_company_scope(self):
        deletable = self.cost_env["project.cost.ledger"].create(
            {
                "project_id": self.owned_project.id,
                "period_id": self.periods["owned"].id,
                "period": "2026-07",
                "cost_code_id": self.cost_code.id,
                "amount": 3.0,
            }
        )
        self.assertTrue(deletable.unlink())
        with self.assertRaises(AccessError):
            self.records["unrelated"].with_user(self.cost_user).with_context(
                allowed_company_ids=[self.company_a.id]
            ).unlink()

    def test_cross_company_and_forged_allowed_company_context_are_denied(self):
        self.assertFalse(
            self.cost_env["project.cost.ledger"].search(
                [("id", "=", self.records["cross_company"].id)],
                limit=1,
            )
        )
        with self.assertRaises(AccessError):
            self.env(
                user=self.cost_user,
                context={
                    **self.env.context,
                    "allowed_company_ids": [self.company_b.id],
                },
            )["project.cost.ledger"].search([])

    def test_direct_read_and_identifier_observations_do_not_leak(self):
        with self.assertRaises(AccessError):
            self.cost_env["project.cost.ledger"].browse(
                self.records["unrelated"].id
            ).read(["id", "note"])
        observations = []
        for record_id in (
            self.records["unrelated"].id,
            self.records["cross_company"].id,
            self.nonexistent_id,
        ):
            result = self.cost_env["project.cost.ledger"].search(
                [("id", "=", record_id)],
                limit=1,
            )
            observations.append((bool(result), len(result)))
        self.assertEqual(observations, [(False, 0), (False, 0), (False, 0)])

    def test_superuser_and_no_scope_contracts(self):
        all_ids = {record.id for record in self.records.values()}
        visible_as_superuser = self.env["project.cost.ledger"].search(
            [("id", "in", list(all_ids))]
        )
        self.assertEqual(set(visible_as_superuser.ids), all_ids)

        visible = self.cost_env["project.cost.ledger"].search([])
        self.assertIn(self.records["owned"], visible)
        self.assertIn(self.records["followed"], visible)
        self.assertNotIn(self.records["unrelated"], visible)
        self.assertNotIn(self.records["manager_only"], visible)
        self.assertNotIn(self.records["cross_company"], visible)

    def test_company_is_stored_readonly_project_derivation(self):
        field = self.env["project.cost.ledger"]._fields["company_id"]
        self.assertTrue(field.store)
        self.assertTrue(field.readonly)
        self.assertEqual(field.related, "project_id.company_id")
        self.assertEqual(self.records["owned"].company_id, self.owned_project.company_id)
