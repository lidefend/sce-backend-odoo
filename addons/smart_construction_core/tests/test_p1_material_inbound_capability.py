# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "p1_material_inbound")
class TestP1MaterialInboundCapability(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.write(
            {
                "groups_id": [
                    (4, self.env.ref("smart_construction_core.group_sc_cap_material_user").id)
                ]
            }
        )
        self.project = self.env["project.project"].create(
            {"name": "P1 Material Inbound Project", "company_id": self.env.company.id}
        )
        self.supplier = self.env["res.partner"].create(
            {"name": "P1 Material Supplier", "supplier_rank": 1}
        )
        self.product = self.env["product.product"].create(
            {"name": "P1 Inbound Material", "type": "product"}
        )

    def _line_vals(self):
        return {
            "product_id": self.product.id,
            "product_uom_id": self.product.uom_id.id,
            "qty": 2,
            "unit_price": 100,
        }

    def test_only_contract_execution_requires_expense_contract(self):
        spot = self.env["sc.material.inbound"].create(
            {
                "project_id": self.project.id,
                "supplier_id": self.supplier.id,
                "source_type": "spot_purchase",
                "line_ids": [(0, 0, self._line_vals())],
            }
        )
        self.assertTrue(spot._validate_source_relationships(final=True))

        contract_execution = self.env["sc.material.inbound"].create(
            {
                "project_id": self.project.id,
                "supplier_id": self.supplier.id,
                "source_type": "contract_execution",
                "line_ids": [(0, 0, self._line_vals())],
            }
        )
        with self.assertRaisesRegex(ValidationError, "必须关联支出合同"):
            contract_execution._validate_source_relationships(final=True)

    def test_contract_source_auto_fills_and_validates_business_identity(self):
        contract = self.env["construction.contract"].create(
            {
                "subject": "P1 Material Expense Contract",
                "type": "in",
                "project_id": self.project.id,
                "partner_id": self.supplier.id,
            }
        )
        self.env.cr.execute(
            "UPDATE construction_contract SET state = 'confirmed' WHERE id = %s",
            (contract.id,),
        )
        contract.invalidate_recordset(["state"])
        inbound = self.env["sc.material.inbound"].create(
            {
                "source_type": "contract_execution",
                "contract_id": contract.id,
                "line_ids": [(0, 0, self._line_vals())],
            }
        )
        self.assertEqual(inbound.project_id, self.project)
        self.assertEqual(inbound.supplier_id, self.supplier)
        self.assertTrue(inbound._validate_source_relationships(final=True))

        other_supplier = self.env["res.partner"].create(
            {"name": "P1 Other Material Supplier", "supplier_rank": 1}
        )
        with self.assertRaisesRegex(ValidationError, "往来单位与入库供应商不一致"):
            inbound.supplier_id = other_supplier

    def test_blocked_supplier_cannot_submit_external_inbound(self):
        self.supplier.write(
            {
                "sc_blacklisted": True,
                "sc_blacklist_level": "blocked",
                "sc_blacklist_reason": "停止材料合作",
            }
        )
        inbound = self.env["sc.material.inbound"].create(
            {
                "project_id": self.project.id,
                "supplier_id": self.supplier.id,
                "source_type": "spot_purchase",
                "line_ids": [(0, 0, self._line_vals())],
            }
        )
        with self.assertRaisesRegex(UserError, "无法发起材料入库"):
            inbound.action_submit()
        self.assertEqual(inbound.state, "draft")

    def test_material_inbound_form_exposes_conditional_source_contract(self):
        form = self.env.ref("smart_construction_core.view_sc_material_inbound_form")
        self.assertIn('name="source_type"', form.arch_db)
        self.assertIn('name="contract_id"', form.arch_db)
        self.assertIn("source_type == 'contract_execution'", form.arch_db)
        self.assertIn('name="origin_inbound_id"', form.arch_db)
        self.assertIn('name="supplier_transaction_eligibility"', form.arch_db)

    def test_system_default_supplier_remains_visible_recoverable_fallback(self):
        inbound = self.env["sc.material.inbound"].create(
            {
                "project_id": self.project.id,
                "source_type": "spot_purchase",
                "line_ids": [(0, 0, self._line_vals())],
            }
        )
        self.assertTrue(inbound.supplier_id)
        self.assertTrue(inbound.sc_has_system_default)
        self.assertIn("supplier_id", inbound.sc_system_default_fields)
        self.assertTrue(inbound.action_submit())
        self.assertEqual(inbound.state, "submitted")

    def test_adjustment_and_transfer_sources_require_their_own_evidence(self):
        adjustment = self.env["sc.material.inbound"].create(
            {
                "project_id": self.project.id,
                "supplier_id": self.supplier.id,
                "source_type": "adjustment_reversal",
                "line_ids": [(0, 0, self._line_vals())],
            }
        )
        with self.assertRaisesRegex(ValidationError, "必须关联原入库单"):
            adjustment._validate_source_relationships(final=True)

        transfer = self.env["sc.material.inbound"].create(
            {
                "project_id": self.project.id,
                "source_type": "internal_transfer",
                "line_ids": [(0, 0, self._line_vals())],
            }
        )
        self.assertFalse(transfer.supplier_id)
        with self.assertRaisesRegex(ValidationError, "必须关联来源调拨出库单"):
            transfer._validate_source_relationships(final=True)
