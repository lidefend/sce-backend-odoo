# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "admin_vis_p3_project_record_rule_orm")
class TestUmP3SubcontractRegisterSettlementAuthorityOrm(TransactionCase):
    """Real-ORM proof for explicit subcontract performance settlement scope."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create(
            {"name": "UM-P3 S05 company B"}
        )
        base_user = cls.env.ref("base.group_user")
        internal = cls.env.ref(
            "smart_construction_core.group_sc_internal_user"
        )
        contract_read = cls.env.ref(
            "smart_construction_core.group_sc_cap_contract_read"
        )
        project_read = cls.env.ref(
            "smart_construction_core.group_sc_cap_project_read"
        )
        cls.caller = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "UM-P3 S05 caller",
                "login": "um_p3_s05_caller",
                "email": "um_p3_s05@example.invalid",
                "company_id": cls.company_a.id,
                "company_ids": [(6, 0, [cls.company_a.id])],
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            base_user.id,
                            internal.id,
                            contract_read.id,
                            project_read.id,
                        ],
                    )
                ],
            }
        )
        cls.context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company_a.id, cls.company_b.id],
            "tracking_disable": True,
        }

        def project(label, company, owner):
            return cls.env["project.project"].with_context(
                cls.context
            ).create(
                {
                    "name": f"UM-P3 S05 {label}",
                    "code": f"UM-P3-S05-{label}",
                    "company_id": company.id,
                    "privacy_visibility": "followers",
                    "user_id": owner.id,
                }
            )

        cls.project_a = project("project-a", cls.company_a, cls.caller)
        cls.project_a2 = project("project-a2", cls.company_a, cls.caller)
        cls.project_b = project("project-b", cls.company_b, cls.env.user)
        cls.partner_a = cls.env["res.partner"].create(
            {"name": "UM-P3 S05 subcontractor A"}
        )
        cls.partner_b = cls.env["res.partner"].create(
            {"name": "UM-P3 S05 subcontractor B"}
        )

        def tax(label, company):
            TaxGroup = cls.env["account.tax.group"].with_company(
                company
            ).with_context(cls.context)
            group = TaxGroup.search(
                [("company_id", "=", company.id)], limit=1
            )
            if not group:
                group = TaxGroup.create(
                    {
                        "name": f"UM-P3 S05 {label} tax group",
                        "company_id": company.id,
                    }
                )
            return cls.env["account.tax"].with_company(company).with_context(
                cls.context
            ).create(
                {
                    "name": f"UM-P3 S05 {label} 3%",
                    "amount": 3.0,
                    "amount_type": "percent",
                    "type_tax_use": "purchase",
                    "price_include": False,
                    "company_id": company.id,
                    "tax_group_id": group.id,
                    "country_id": (
                        company.country_id or cls.env.ref("base.cn")
                    ).id,
                }
            )

        cls.tax_a = tax("company-a", cls.company_a)
        cls.tax_b = tax("company-b", cls.company_b)

        def contract(label, project_record, partner, tax_record):
            contract_record = cls.env["construction.contract"].with_company(
                project_record.company_id
            ).with_context(cls.context).create(
                {
                    "subject": f"UM-P3 S05 {label}",
                    "type": "in",
                    "project_id": project_record.id,
                    "partner_id": partner.id,
                    "company_id": project_record.company_id.id,
                    "currency_id": project_record.company_id.currency_id.id,
                    "tax_id": tax_record.id,
                }
            )
            cls.env["construction.contract.line"].with_context(
                cls.context
            ).create(
                {
                    "contract_id": contract_record.id,
                    "qty_contract": 1.0,
                    "price_contract": 1000000.0,
                }
            )
            return contract_record

        cls.contract_a = contract(
            "contract-a", cls.project_a, cls.partner_a, cls.tax_a
        )
        cls.contract_a2 = contract(
            "contract-a2", cls.project_a, cls.partner_a, cls.tax_a
        )
        cls.contract_project_conflict = contract(
            "contract-project-conflict",
            cls.project_a2,
            cls.partner_a,
            cls.tax_a,
        )
        cls.contract_partner_conflict = contract(
            "contract-partner-conflict",
            cls.project_a,
            cls.partner_b,
            cls.tax_a,
        )
        cls.contract_company_b = contract(
            "contract-company-b",
            cls.project_b,
            cls.partner_a,
            cls.tax_b,
        )

        def register(label, contract_record, line_count=2):
            record = cls.env["sc.subcontract.register"].with_context(
                cls.context
            ).create(
                {
                    "contract_id": contract_record.id,
                    "subcontract_scope": f"UM-P3 S05 {label}",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "work_scope": (
                                    f"UM-P3 S05 {label} line {index}"
                                ),
                                "contract_qty": 10.0,
                                "unit_name": "项",
                                "registered_amount": 1000.0,
                            },
                        )
                        for index in range(line_count)
                    ],
                }
            )
            record.action_register()
            return record

        cls.register_a1 = register("register-a1", cls.contract_a)
        cls.register_a2 = register(
            "register-a2", cls.contract_a, line_count=1
        )
        cls.register_contract_a2 = register(
            "register-contract-a2", cls.contract_a2, line_count=1
        )
        cls.register_project_conflict = register(
            "register-project-conflict",
            cls.contract_project_conflict,
            line_count=1,
        )
        cls.register_partner_conflict = register(
            "register-partner-conflict",
            cls.contract_partner_conflict,
            line_count=1,
        )
        cls.register_company_b = register(
            "register-company-b", cls.contract_company_b, line_count=1
        )
        cls.caller_env = cls.env(
            user=cls.caller,
            context={
                **cls.env.context,
                "allowed_company_ids": [cls.company_a.id],
                "tracking_disable": True,
            },
        )

    def _settlement(
        self,
        label,
        register_lines=(),
        project=None,
        contract=None,
        partner=None,
        quantities=None,
    ):
        project = project or self.project_a
        partner = partner or self.partner_a
        quantities = quantities or [1.0] * max(len(register_lines), 1)
        line_values = []
        for index, quantity in enumerate(quantities):
            vals = {
                "work_scope": f"UM-P3 S05 {label} line {index}",
                "qty": quantity,
                "unit_name": "项",
                "unit_price": 100.0,
                "tax_rate": 3.0,
            }
            if register_lines:
                vals["register_line_id"] = register_lines[index].id
            line_values.append((0, 0, vals))
        values = {
            "name": f"UM-P3 S05 {label}",
            "project_id": project.id,
            "subcontractor_id": partner.id,
            "line_ids": line_values,
        }
        if contract:
            values["contract_id"] = contract.id
        return self.env["sc.subcontract.settlement"].with_context(
            self.context
        ).create(values)

    def _new_register(self, label, contract, quantity=10.0):
        register = self.env["sc.subcontract.register"].with_context(
            self.context
        ).create(
            {
                "contract_id": contract.id,
                "subcontract_scope": f"UM-P3 S05 {label}",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "work_scope": f"UM-P3 S05 {label} line",
                            "contract_qty": quantity,
                            "unit_name": "项",
                            "registered_amount": 10000.0,
                        },
                    )
                ],
            }
        )
        register.action_register()
        return register

    def test_single_multi_register_projection_and_detail_preservation(self):
        single = self._settlement(
            "single",
            [self.register_a1.line_ids[0]],
        )
        self.assertEqual(single.register_id, self.register_a1)
        self.assertEqual(single.contract_id, self.contract_a)
        self.assertEqual(single.project_id, self.project_a)
        self.assertEqual(single.subcontractor_id, self.partner_a)

        multiple = self._settlement(
            "multiple",
            [
                self.register_a1.line_ids[1],
                self.register_a2.line_ids[0],
            ],
        )
        self.assertFalse(multiple.register_id)
        self.assertEqual(multiple.contract_id, self.contract_a)
        self.assertEqual(
            set(multiple.line_ids.mapped("register_line_id").ids),
            {
                self.register_a1.line_ids[1].id,
                self.register_a2.line_ids[0].id,
            },
        )

    def test_one_register_can_be_split_across_multiple_settlements(self):
        source = self.register_a1.line_ids[0]
        first = self._settlement("split-first", [source])
        second = self._settlement("split-second", [source])
        self.assertEqual(first.line_ids.register_line_id, source)
        self.assertEqual(second.line_ids.register_line_id, source)
        self.assertEqual(
            set(source.settlement_line_ids.mapped("settlement_id").ids),
            {first.id, second.id},
        )

    def test_cross_contract_project_counterparty_and_company_are_rejected(self):
        conflicts = (
            self.register_contract_a2,
            self.register_project_conflict,
            self.register_partner_conflict,
            self.register_company_b,
        )
        for index, register in enumerate(conflicts):
            with self.env.cr.savepoint(), self.assertRaises(ValidationError):
                self._settlement(
                    f"cross-scope-{index}",
                    [
                        self.register_a1.line_ids[0],
                        register.line_ids[0],
                    ],
                )

    def test_explicit_header_conflicts_and_non_override_hold(self):
        source = self.register_a1.line_ids[0]
        cases = (
            {
                "project": self.project_a2,
                "contract": self.contract_a,
                "partner": self.partner_a,
            },
            {
                "project": self.project_a,
                "contract": self.contract_a2,
                "partner": self.partner_a,
            },
            {
                "project": self.project_a,
                "contract": self.contract_a,
                "partner": self.partner_b,
            },
        )
        for index, values in enumerate(cases):
            with self.env.cr.savepoint(), self.assertRaises(ValidationError):
                self._settlement(
                    f"explicit-conflict-{index}",
                    [source],
                    **values,
                )
        self.assertEqual(self.register_a1.project_id, self.project_a)
        self.assertEqual(self.register_a1.contract_id, self.contract_a)
        self.assertEqual(self.contract_a.partner_id, self.partner_a)

    def test_empty_relation_is_legal_and_header_register_cannot_substitute(self):
        unrelated = self._settlement("unrelated")
        self.assertFalse(unrelated.line_ids.register_line_id)
        self.assertFalse(unrelated.register_id)
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            self.env["sc.subcontract.settlement"].with_context(
                self.context
            ).create(
                {
                    "name": "UM-P3 S05 header-only register",
                    "project_id": self.project_a.id,
                    "register_id": self.register_a1.id,
                    "contract_id": self.contract_a.id,
                    "subcontractor_id": self.partner_a.id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "work_scope": "UM-P3 S05 header-only",
                                "qty": 1.0,
                                "unit_price": 100.0,
                            },
                        )
                    ],
                }
            )

    def test_direct_create_write_and_unlink_revalidate(self):
        empty = self.env["sc.subcontract.settlement"].with_context(
            self.context
        ).create(
            {
                "name": "UM-P3 S05 direct-create",
                "project_id": self.project_a.id,
                "subcontractor_id": self.partner_a.id,
            }
        )
        line = self.env["sc.subcontract.settlement.line"].create(
            {
                "settlement_id": empty.id,
                "register_line_id": self.register_a1.line_ids[0].id,
                "work_scope": "UM-P3 S05 direct-create",
                "qty": 1.0,
                "unit_price": 100.0,
            }
        )
        self.assertEqual(empty.contract_id, self.contract_a)
        with self.env.cr.savepoint(), self.assertRaises(UserError):
            line.unlink()
        line.write({"register_line_id": False})
        self.assertFalse(empty.register_id)
        self.assertFalse(empty.contract_id)
        line.unlink()
        self.assertFalse(empty.line_ids)

    def test_one2many_commands_use_final_state(self):
        settlement = self._settlement(
            "commands",
            [
                self.register_a1.line_ids[0],
                self.register_a1.line_ids[1],
            ],
        )
        target = self.register_a2.line_ids[0]
        settlement.write(
            {
                "line_ids": [
                    (
                        1,
                        line.id,
                        {"register_line_id": target.id},
                    )
                    for line in settlement.line_ids
                ]
            }
        )
        self.assertEqual(settlement.register_id, self.register_a2)
        settlement.write(
            {
                "line_ids": [
                    (1, line.id, {"register_line_id": False})
                    for line in settlement.line_ids
                ]
            }
        )
        self.assertFalse(settlement.register_id)
        self.assertFalse(settlement.contract_id)
        self.assertFalse(settlement.line_ids.mapped("register_line_id"))

    def test_generic_import_and_partial_relation_cannot_bypass(self):
        settlement = self._settlement(
            "generic-import", quantities=[1.0, 1.0]
        )
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            settlement.line_ids[0].with_context(import_file=True).write(
                {
                    "register_line_id": self.register_a1.line_ids[0].id
                }
            )
        self.assertFalse(settlement.line_ids.mapped("register_line_id"))

    def test_unauthorized_and_nonexistent_identifiers_are_equivalent(self):
        settlement = self._settlement("caller-visibility")
        line = settlement.line_ids.with_env(self.caller_env)
        observations = []
        for register_line_id in (
            self.register_company_b.line_ids.id,
            self.register_company_b.line_ids.id + 1000000,
        ):
            with self.env.cr.savepoint(), self.assertRaises(
                AccessError
            ) as raised:
                line.write({"register_line_id": register_line_id})
            observations.append((type(raised.exception), str(raised.exception)))
        self.assertEqual(observations[0], observations[1])

    def test_no_cumulative_limit_or_cancellation_policy_is_invented(self):
        register = self._new_register(
            "no-limit-register", self.contract_a
        )
        source = register.line_ids
        oversized = self._settlement(
            "no-invented-limit",
            [source],
            quantities=[source.contract_qty + 100.0],
        )
        oversized.action_submit()
        self.assertEqual(oversized.state, "submitted")

        cancellable = self._settlement("cancellation-undefined", [source])
        register.action_cancel()
        self.assertEqual(register.state, "cancel")
        with self.assertRaises(UserError):
            cancellable.action_submit()

    def test_contract_mutation_refreshes_authoritative_projections(self):
        contract = self.contract_a.copy(
            {"subject": "UM-P3 S05 mutable contract"}
        )
        self.env["construction.contract.line"].create(
            {
                "contract_id": contract.id,
                "qty_contract": 1.0,
                "price_contract": 1000000.0,
            }
        )
        register = self._new_register("mutable-register", contract)
        settlement = self._settlement(
            "contract-refresh",
            [register.line_ids],
        )
        contract.write({"partner_id": self.partner_b.id})
        self.assertEqual(register.subcontractor_id, self.partner_b)
        self.assertEqual(settlement.subcontractor_id, self.partner_b)

    def test_administrator_contract_holds(self):
        self.assertTrue(self.env.is_superuser())
        settlement = self._settlement(
            "administrator",
            [self.register_a1.line_ids[0]],
        )
        self.assertEqual(settlement.contract_id, self.contract_a)
