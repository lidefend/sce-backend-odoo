# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "admin_vis_p3_project_record_rule_orm")
class TestUmP2SettlementRelationAggregationOrm(TransactionCase):
    """Real-ORM proof for detail-authoritative settlement contracts."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create(
            {"name": "UM-P2 S05 company B"}
        )
        base_user = cls.env.ref("base.group_user")
        settlement_manager = cls.env.ref(
            "smart_construction_core.group_sc_cap_settlement_manager"
        )
        contract_read = cls.env.ref(
            "smart_construction_core.group_sc_cap_contract_read"
        )
        cls.caller = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "UM-P2 S05 settlement caller",
                "login": "um_p2_s05_settlement_caller",
                "email": "um_p2_s05@example.invalid",
                "company_id": cls.company_a.id,
                "company_ids": [(6, 0, [cls.company_a.id])],
                "groups_id": [
                    (6, 0, [base_user.id, settlement_manager.id, contract_read.id])
                ],
            }
        )
        setup_context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company_a.id, cls.company_b.id],
            "tracking_disable": True,
        }
        Project = cls.env["project.project"].with_context(setup_context)
        cls.project_a = Project.create(
            {
                "name": "UM-P2 S05 project A",
                "company_id": cls.company_a.id,
                "privacy_visibility": "followers",
                "user_id": cls.caller.id,
            }
        )
        cls.project_a_other = Project.create(
            {
                "name": "UM-P2 S05 project A other",
                "company_id": cls.company_a.id,
                "privacy_visibility": "followers",
                "user_id": cls.caller.id,
            }
        )
        cls.project_b = Project.create(
            {
                "name": "UM-P2 S05 project B",
                "company_id": cls.company_b.id,
                "privacy_visibility": "followers",
                "user_id": cls.env.user.id,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "UM-P2 S05 counterparty"}
        )
        cls.other_partner = cls.env["res.partner"].create(
            {"name": "UM-P2 S05 other counterparty"}
        )
        tax = cls.env["account.tax"].search(
            [("type_tax_use", "in", ("purchase", "none"))], limit=1
        )

        def contract(label, project, partner):
            return cls.env["construction.contract"].with_context(
                setup_context
            ).create(
                {
                    "subject": f"UM-P2 S05 {label}",
                    "type": "in",
                    "project_id": project.id,
                    "company_id": project.company_id.id,
                    "partner_id": partner.id,
                    "tax_id": tax.id,
                }
            )

        cls.contract_a = contract("contract A", cls.project_a, cls.partner)
        cls.contract_b = contract("contract B", cls.project_a, cls.partner)
        cls.other_project_contract = contract(
            "other project", cls.project_a_other, cls.partner
        )
        cls.other_partner_contract = contract(
            "other partner", cls.project_a, cls.other_partner
        )
        cls.hidden_contract = contract(
            "hidden company", cls.project_b, cls.partner
        )
        cls.caller_env = cls.env(
            user=cls.caller,
            context={
                **cls.env.context,
                "allowed_company_ids": [cls.company_a.id],
                "tracking_disable": True,
            },
        )

    def _line_command(self, contract, label):
        return (
            0,
            0,
            {
                "name": label,
                "contract_id": contract.id,
                "qty": 1.0,
                "price_unit": 100.0,
            },
        )

    def _settlement(self, contracts, **values):
        vals = {
            "project_id": self.project_a.id,
            "company_id": self.company_a.id,
            "partner_id": self.partner.id,
            "settlement_type": "out",
            "title": "UM-P2 S05 settlement",
            "line_ids": [
                self._line_command(contract, f"line {index}")
                for index, contract in enumerate(contracts, start=1)
            ],
        }
        vals.update(values)
        return self.caller_env["sc.settlement.order"].create(vals)

    def test_single_and_same_contract_details_project_one_header_contract(self):
        single = self._settlement([self.contract_a])
        repeated = self._settlement([self.contract_a, self.contract_a])
        self.assertEqual(single.contract_id, self.contract_a)
        self.assertEqual(repeated.contract_id, self.contract_a)
        self.assertEqual(repeated.line_ids.mapped("contract_id"), self.contract_a)

    def test_multiple_contract_details_are_preserved_with_empty_header(self):
        settlement = self._settlement([self.contract_a, self.contract_b])
        self.assertFalse(settlement.contract_id)
        self.assertEqual(
            set(settlement.line_ids.mapped("contract_id").ids),
            {self.contract_a.id, self.contract_b.id},
        )

    def test_explicit_header_contract_must_match_complete_detail_set(self):
        accepted = self._settlement(
            [self.contract_a], contract_id=self.contract_a.id
        )
        self.assertEqual(accepted.contract_id, self.contract_a)
        with self.assertRaises(UserError):
            self._settlement([self.contract_a], contract_id=self.contract_b.id)
        with self.assertRaises(UserError):
            self._settlement(
                [self.contract_a, self.contract_b],
                contract_id=self.contract_a.id,
            )

    def test_existing_unique_header_default_remains_compatible(self):
        settlement = self._settlement(
            [],
            contract_id=self.contract_a.id,
            line_ids=[
                (
                    0,
                    0,
                    {"name": "unique default", "qty": 1.0, "price_unit": 1.0},
                )
            ],
        )
        self.assertEqual(settlement.line_ids.contract_id, self.contract_a)
        self.assertEqual(settlement.contract_id, self.contract_a)

    def test_direct_line_create_write_and_unlink_reproject_header(self):
        settlement = self._settlement([self.contract_a])
        added = self.caller_env["sc.settlement.order.line"].create(
            {
                "settlement_id": settlement.id,
                "contract_id": self.contract_b.id,
                "name": "direct B",
                "qty": 1.0,
                "price_unit": 10.0,
            }
        )
        self.assertFalse(settlement.contract_id)
        added.unlink()
        self.assertEqual(settlement.contract_id, self.contract_a)
        line = settlement.line_ids
        line.with_context(allow_contract_change=True).write(
            {"contract_id": self.contract_b.id}
        )
        self.assertEqual(settlement.contract_id, self.contract_b)
        self.assertEqual(line.contract_id, self.contract_b)

    def test_one2many_commands_revalidate_complete_final_state(self):
        settlement = self._settlement([self.contract_a])
        settlement.write(
            {"line_ids": [self._line_command(self.contract_b, "nested B")]}
        )
        self.assertFalse(settlement.contract_id)
        line_b = settlement.line_ids.filtered(
            lambda line: line.contract_id == self.contract_b
        )
        settlement.write({"line_ids": [(2, line_b.id, 0)]})
        self.assertEqual(settlement.contract_id, self.contract_a)

    def test_project_company_counterparty_and_hidden_relations_are_rejected(self):
        with self.assertRaises(UserError):
            self._settlement([self.other_project_contract])
        with self.assertRaises(UserError):
            self._settlement([self.other_partner_contract])

        observations = []
        for contract_id in (
            self.hidden_contract.id,
            self.hidden_contract.id + 1000000,
        ):
            with self.assertRaises(AccessError) as raised:
                self._settlement(
                    [],
                    line_ids=[
                        (
                            0,
                            0,
                            {
                                "name": "hidden relation",
                                "contract_id": contract_id,
                                "qty": 1.0,
                                "price_unit": 1.0,
                            },
                        )
                    ],
                )
            observations.append((type(raised.exception), str(raised.exception)))
        self.assertEqual(observations[0], observations[1])

    def test_material_settlement_remains_non_contract_bearing(self):
        material_header = self.env["sc.material.settlement"]
        material_line = self.env["sc.material.settlement.line"]
        self.assertNotIn("contract_id", material_header._fields)
        self.assertNotIn("contract_id", material_line._fields)
        self.assertIn("purchase_order_id", material_header._fields)
        self.assertIn("supplier_id", material_header._fields)
