# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "sc_perm", "rr_gate")
class TestRecordRuleBehaviorGate(TransactionCase):
    """P0 record rule behavior gate: verify allowed/denied boundaries on key models."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.ref("base.main_company")
        ctx = dict(
            cls.env.context,
            mail_create_nosubscribe=True,
            mail_notify_noemail=True,
            mail_auto_subscribe_no_notify=True,
            tracking_disable=True,
        )
        def _ctx(model):
            return cls.env[model].with_context(ctx)

        def _create_user(login, group_xmlids):
            groups = [(6, 0, [cls.env.ref(x).id for x in group_xmlids])]
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@example.com",
                    "company_id": company.id,
                    "company_ids": [(6, 0, [company.id])],
                    "groups_id": groups,
                }
            )

        cls.user_project_read = _create_user(
            "rr_project_read",
            ["smart_construction_core.group_sc_cap_project_read"],
        )
        cls.user_project_user = _create_user(
            "rr_project_user",
            ["smart_construction_core.group_sc_cap_project_user"],
        )
        cls.user_project_manager = _create_user(
            "rr_project_manager",
            ["smart_construction_core.group_sc_cap_project_manager"],
        )
        cls.user_finance_read = _create_user(
            "rr_finance_read",
            ["smart_construction_core.group_sc_cap_finance_read"],
        )
        cls.user_finance_user = _create_user(
            "rr_finance_user",
            ["smart_construction_core.group_sc_cap_finance_user"],
        )
        cls.user_settlement_read = _create_user(
            "rr_settlement_read",
            ["smart_construction_core.group_sc_cap_settlement_read"],
        )
        cls.user_settlement_user = _create_user(
            "rr_settlement_user",
            ["smart_construction_core.group_sc_cap_settlement_user"],
        )
        cls.user_cost_user = _create_user(
            "rr_cost_user",
            ["smart_construction_core.group_sc_cap_cost_user"],
        )
        cls.user_cost_manager = _create_user(
            "rr_cost_manager",
            ["smart_construction_core.group_sc_cap_cost_manager"],
        )

        project_vals = {
            "privacy_visibility": "followers",
            "company_id": company.id,
        }
        cls.project_cost_user = _ctx("project.project").create(
            dict(project_vals, name="RR Project Cost User", user_id=cls.user_cost_user.id)
        )
        cls.project_cost_other = _ctx("project.project").create(
            dict(project_vals, name="RR Project Cost Other", user_id=cls.user_cost_manager.id)
        )
        cls.project_read = _ctx("project.project").create(
            dict(project_vals, name="RR Project Read", user_id=cls.user_project_read.id)
        )
        cls.project_user = _ctx("project.project").create(
            dict(project_vals, name="RR Project User", user_id=cls.user_project_user.id)
        )
        cls.project_other = _ctx("project.project").create(
            dict(project_vals, name="RR Project Other", user_id=cls.user_project_manager.id)
        )
        cls.project_finance = _ctx("project.project").create(
            dict(project_vals, name="RR Project Finance", user_id=cls.user_finance_user.id)
        )
        cls.project_finance_read = _ctx("project.project").create(
            dict(project_vals, name="RR Project Finance Read", user_id=cls.user_finance_read.id)
        )
        cls.project_settlement = _ctx("project.project").create(
            dict(project_vals, name="RR Project Settlement", user_id=cls.user_settlement_user.id)
        )
        cls.project_settlement_read = _ctx("project.project").create(
            dict(project_vals, name="RR Project Settlement Read", user_id=cls.user_settlement_read.id)
        )

        # Finance record rules admit the project responsible user or an
        # explicit project follower. Keep the fixture independent from mail's
        # automatic subscription side effects by declaring membership here.
        cls.project_finance.message_subscribe(partner_ids=[cls.user_finance_user.partner_id.id])
        cls.project_finance_read.message_subscribe(partner_ids=[cls.user_finance_read.partner_id.id])

        cls.task_read = _ctx("project.task").create(
            {"name": "RR Task Read", "project_id": cls.project_read.id}
        )
        cls.task_user = _ctx("project.task").create(
            {"name": "RR Task User", "project_id": cls.project_user.id}
        )
        cls.task_other = _ctx("project.task").create(
            {"name": "RR Task Other", "project_id": cls.project_other.id}
        )

        cls.partner = _ctx("res.partner").create({"name": "RR Partner"})

        tax = cls.env["account.tax"].search([], limit=1)
        if not tax:
            tax = _ctx("account.tax").create(
                {
                    "name": "RR Contract Tax",
                    "amount": 0.0,
                    "amount_type": "percent",
                    "type_tax_use": "sale",
                }
            )

        def _create_contract(name, project):
            return _ctx("construction.contract").create(
                {
                    "subject": name,
                    "type": "out",
                    "project_id": project.id,
                    "partner_id": cls.partner.id,
                    "tax_id": tax.id,
                }
            )

        cls.contract_settlement_read = _create_contract(
            "RR Contract Settlement Read", cls.project_settlement_read
        )
        cls.contract_settlement_user = _create_contract(
            "RR Contract Settlement User", cls.project_settlement
        )
        cls.contract_settlement_other = _create_contract(
            "RR Contract Settlement Other", cls.project_other
        )

        cls.payment_req_read = _ctx("payment.request").create(
            {
                "project_id": cls.project_finance_read.id,
                "partner_id": cls.partner.id,
                "amount": 10.0,
                "type": "pay",
            }
        )
        cls.payment_req_user = _ctx("payment.request").create(
            {
                "project_id": cls.project_finance.id,
                "partner_id": cls.partner.id,
                "amount": 20.0,
                "type": "pay",
            }
        )
        cls.payment_req_other = _ctx("payment.request").create(
            {
                "project_id": cls.project_other.id,
                "partner_id": cls.partner.id,
                "amount": 30.0,
                "type": "pay",
            }
        )

        cls.settlement_read = _ctx("sc.settlement.order").create(
            {
                "project_id": cls.project_settlement_read.id,
                "partner_id": cls.partner.id,
                "contract_id": cls.contract_settlement_read.id,
                "settlement_type": "in",
                "line_ids": [(0, 0, {"name": "RR Line Read", "amount": 10.0})],
            }
        )
        cls.settlement_user = _ctx("sc.settlement.order").create(
            {
                "project_id": cls.project_settlement.id,
                "partner_id": cls.partner.id,
                "contract_id": cls.contract_settlement_user.id,
                "settlement_type": "in",
                "line_ids": [(0, 0, {"name": "RR Line User", "amount": 20.0})],
            }
        )
        cls.settlement_other = _ctx("sc.settlement.order").create(
            {
                "project_id": cls.project_other.id,
                "partner_id": cls.partner.id,
                "contract_id": cls.contract_settlement_other.id,
                "settlement_type": "in",
                "line_ids": [(0, 0, {"name": "RR Line Other", "amount": 30.0})],
            }
        )

        # Ensure denied records do not inherit follower-based access.
        partners = [
            cls.user_project_read.partner_id.id,
            cls.user_project_user.partner_id.id,
            cls.user_finance_read.partner_id.id,
            cls.user_finance_user.partner_id.id,
            cls.user_settlement_read.partner_id.id,
            cls.user_settlement_user.partner_id.id,
        ]
        cls.project_cost_other.message_unsubscribe(partner_ids=partners)
        cls.project_other.message_unsubscribe(partner_ids=partners)
        cls.task_other.message_unsubscribe(partner_ids=partners)
        cls.payment_req_other.project_id.message_unsubscribe(partner_ids=partners)
        cls.settlement_other.project_id.message_unsubscribe(partner_ids=partners)

        uom = cls.env.ref("uom.product_uom_unit")

        def _create_boq(project, code):
            version = _ctx("project.boq.version").create(
                {"name": code, "code": code, "project_id": project.id}
            )
            line = _ctx("project.boq.line").create(
                {
                    "project_id": project.id,
                    "version_id": version.id,
                    "code": code,
                    "name": code,
                    "uom_id": uom.id,
                }
            )
            return version, line

        cls.boq_version_user, cls.boq_line_user = _create_boq(
            cls.project_cost_user, "RRBOQ-USER"
        )
        cls.boq_version_other, cls.boq_line_other = _create_boq(
            cls.project_cost_other, "RRBOQ-OTHER"
        )

        # --- cross-company fixture -------------------------------------------
        # Neither project.boq.line nor project.boq.version has a company_id, so
        # the company boundary can only travel project_id -> project.project.
        # It has to be measured on real reads: seeing the rule definition (or
        # an ACL) is not proof that a role cannot cross the boundary.
        cls.company_secondary = _ctx("res.company").create({"name": "RR Secondary Company"})

        def _create_company_user(login, group_xmlids, company):
            groups = [(6, 0, [cls.env.ref(x).id for x in group_xmlids])]
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@example.com",
                    "company_id": company.id,
                    "company_ids": [(6, 0, [company.id])],
                    "groups_id": groups,
                }
            )

        cls.user_cost_user_secondary = _create_company_user(
            "rr_cost_user_secondary",
            ["smart_construction_core.group_sc_cap_cost_user"],
            cls.company_secondary,
        )
        cls.user_cost_manager_secondary = _create_company_user(
            "rr_cost_manager_secondary",
            ["smart_construction_core.group_sc_cap_cost_manager"],
            cls.company_secondary,
        )
        cls.project_cost_secondary = _ctx("project.project").create(
            dict(
                project_vals,
                name="RR Project Cost Secondary",
                company_id=cls.company_secondary.id,
                user_id=cls.user_cost_user_secondary.id,
            )
        )
        cls.boq_version_secondary, cls.boq_line_secondary = _create_boq(
            cls.project_cost_secondary, "RRBOQ-SECONDARY"
        )
        # A secondary-company project whose responsible user belongs to the
        # primary company only. Project membership alone would hand that user a
        # line whose project it cannot even read.
        cls.project_cost_secondary_foreign = _ctx("project.project").create(
            dict(
                project_vals,
                name="RR Project Cost Secondary Foreign",
                company_id=cls.company_secondary.id,
                user_id=cls.user_cost_user.id,
            )
        )
        cls.boq_version_secondary_foreign, cls.boq_line_secondary_foreign = _create_boq(
            cls.project_cost_secondary_foreign, "RRBOQ-SECONDARY-FOREIGN"
        )

    def _can_read(self, user, record):
        Model = self.env[record._name].with_user(user)
        return bool(Model.search_count([("id", "=", record.id)]))

    def _assert_write_allowed(self, user, record, values):
        record.with_user(user).write(values)

    def _assert_write_denied(self, user, record, values):
        with self.assertRaises(AccessError):
            record.with_user(user).write(values)

    def test_project_project_rules(self):
        # Read-only role: can read own project, cannot see others.
        self.assertTrue(self._can_read(self.user_project_read, self.project_read))
        self.assertFalse(self._can_read(self.user_project_read, self.project_other))

        # User role: can write own project, denied on others.
        self._assert_write_allowed(
            self.user_project_user, self.project_user, {"name": "RR Project User Updated"}
        )
        self._assert_write_denied(
            self.user_project_user, self.project_other, {"name": "RR Project Other Updated"}
        )

        # Manager role: can read and write all.
        self.assertTrue(self._can_read(self.user_project_manager, self.project_other))
        self._assert_write_allowed(
            self.user_project_manager, self.project_other, {"name": "RR Project Other Manager"}
        )

    def test_project_task_rules(self):
        # Read-only role: can read tasks on own project, cannot see others.
        self.assertTrue(self._can_read(self.user_project_read, self.task_read))
        self.assertFalse(self._can_read(self.user_project_read, self.task_other))

        # User role: can write tasks on own project, denied on others.
        self._assert_write_allowed(
            self.user_project_user, self.task_user, {"name": "RR Task User Updated"}
        )
        self._assert_write_denied(
            self.user_project_user, self.task_other, {"name": "RR Task Other Updated"}
        )

        # Manager role: can read and write all tasks.
        self.assertTrue(self._can_read(self.user_project_manager, self.task_other))
        self._assert_write_allowed(
            self.user_project_manager, self.task_other, {"name": "RR Task Other Manager"}
        )

    def test_payment_request_rules(self):
        # Finance read: can read own project, cannot see others.
        self.assertTrue(self._can_read(self.user_finance_read, self.payment_req_read))
        self.assertFalse(self._can_read(self.user_finance_read, self.payment_req_other))

        # Finance user: can write own project, denied on others.
        self._assert_write_allowed(
            self.user_finance_user,
            self.payment_req_user,
            {"note": "RR Payment User Updated"},
        )
        self._assert_write_denied(
            self.user_finance_user,
            self.payment_req_other,
            {"note": "RR Payment Other Updated"},
        )

    def test_settlement_order_rules(self):
        # Settlement read: can read own project, cannot see others.
        self.assertTrue(self._can_read(self.user_settlement_read, self.settlement_read))
        self.assertFalse(self._can_read(self.user_settlement_read, self.settlement_other))

        # Settlement user: can write own project, denied on others.
        self._assert_write_allowed(
            self.user_settlement_user,
            self.settlement_user,
            {"note": "RR Settlement User Updated"},
        )
        self._assert_write_denied(
            self.user_settlement_user,
            self.settlement_other,
            {"note": "RR Settlement Other Updated"},
        )

    def test_settlement_contract_direction_constraint_remains_enforced(self):
        with self.assertRaisesRegex(
            ValidationError,
            "合同类型与收支类型不一致",
        ), self.env.cr.savepoint():
            self.env["sc.settlement.order"].create(
                {
                    "project_id": self.project_settlement.id,
                    "partner_id": self.partner.id,
                    "contract_id": self.contract_settlement_user.id,
                    "settlement_type": "out",
                    "line_ids": [(0, 0, {"name": "RR Invalid Direction", "amount": 1.0})],
                }
            )

    def test_boq_line_project_scope(self):
        """project.boq.line must not expose other projects' rows to a cost operator."""
        model = self.env["project.boq.line"]

        # Cost capability user: only the project it owns is readable.
        self.assertTrue(self._can_read(self.user_cost_user, self.boq_line_user))
        self.assertFalse(self._can_read(self.user_cost_user, self.boq_line_other))

        # A list read must not leak the foreign project either.
        visible = model.with_user(self.user_cost_user).search([]).ids
        self.assertIn(self.boq_line_user.id, visible)
        self.assertNotIn(self.boq_line_other.id, visible)

        # Read-by-id is denied, not merely filtered out of the list.
        with self.assertRaises(AccessError):
            self.boq_line_other.with_user(self.user_cost_user).read(["name"])

        # Cost manager keeps the all-records scope.
        self.assertTrue(self._can_read(self.user_cost_manager, self.boq_line_other))

    def test_boq_line_scope_matches_parent_version_scope(self):
        """The BOQ line scope must not silently diverge from project.boq.version."""
        for user in (self.user_cost_user, self.user_cost_manager):
            self.assertEqual(
                self._can_read(user, self.boq_line_other),
                self._can_read(user, self.boq_version_other),
                "project.boq.line scope diverged from project.boq.version for %s" % user.login,
            )

    def test_boq_line_cross_company_scope(self):
        """Cross-company boundary of the BOQ line and version rules.

        Measuring this boundary (rather than reading the rule text) exposed two
        real cross-company reads before the allowed-companies rule was added -
        a primary-company operator could read a secondary-company line merely by
        being that project's responsible user, and the cost-manager exception
        had no company dimension at all. See
        docs/ops/iterations/boq_line_record_rule_scope_20260924.md.
        """
        line_model = self.env["project.boq.line"]

        # The foreign company's line is denied on both read paths.
        self.assertFalse(self._can_read(self.user_cost_user, self.boq_line_secondary))
        self.assertEqual(
            line_model.with_user(self.user_cost_user).search_count(
                [("id", "=", self.boq_line_secondary.id)]
            ),
            0,
        )
        with self.assertRaises(AccessError):
            line_model.with_user(self.user_cost_user).browse(
                self.boq_line_secondary.id
            ).read(["name"])
        self.assertFalse(self._can_read(self.user_cost_user, self.boq_version_secondary))

        # Symmetric: the secondary-company operator cannot reach primary rows.
        self.assertFalse(self._can_read(self.user_cost_user_secondary, self.boq_line_user))
        self.assertFalse(self._can_read(self.user_cost_user_secondary, self.boq_version_user))

        # Project membership is not a company bypass, and the denied line is not
        # simply a side effect of the project being denied.
        self.assertFalse(
            self._can_read(self.user_cost_user, self.project_cost_secondary_foreign)
        )
        self.assertFalse(
            self._can_read(self.user_cost_user, self.boq_line_secondary_foreign)
        )
        self.assertFalse(
            self._can_read(self.user_cost_user, self.boq_version_secondary_foreign)
        )

        # The cost-manager exception means "all projects of the allowed
        # companies": it still covers every primary-company line, including one
        # owned by another user, and it stops at the company boundary.
        self.assertTrue(self._can_read(self.user_cost_manager, self.boq_line_other))
        self.assertTrue(self._can_read(self.user_cost_manager, self.boq_line_user))
        self.assertFalse(self._can_read(self.user_cost_manager, self.boq_line_secondary))
        self.assertFalse(self._can_read(self.user_cost_manager, self.boq_version_secondary))

        # Inside its own company the exception keeps working.
        self.assertTrue(
            self._can_read(self.user_cost_manager_secondary, self.boq_line_secondary)
        )
        self.assertTrue(
            self._can_read(self.user_cost_manager_secondary, self.boq_version_secondary)
        )
        self.assertFalse(
            self._can_read(self.user_cost_manager_secondary, self.boq_line_user)
        )
