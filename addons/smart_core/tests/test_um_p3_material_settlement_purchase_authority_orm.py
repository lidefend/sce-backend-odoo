# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "admin_vis_p3_project_record_rule_orm")
class TestUmP3MaterialSettlementPurchaseAuthorityOrm(TransactionCase):
    """Real-ORM proof for explicit material-settlement procurement scopes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create(
            {"name": "UM-P3 S04 company B"}
        )
        base_user = cls.env.ref("base.group_user")
        material_user = cls.env.ref(
            "smart_construction_core.group_sc_cap_material_user"
        )
        purchase_user = cls.env.ref(
            "smart_construction_core.group_sc_cap_purchase_user"
        )
        project_read = cls.env.ref(
            "smart_construction_core.group_sc_cap_project_read"
        )
        cls.caller = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "UM-P3 S04 caller",
                "login": "um_p3_s04_caller",
                "email": "um_p3_s04@example.invalid",
                "company_id": cls.company_a.id,
                "company_ids": [(6, 0, [cls.company_a.id])],
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            base_user.id,
                            material_user.id,
                            purchase_user.id,
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
        Project = cls.env["project.project"].with_context(cls.context)

        def project(label, company, owner):
            return Project.create(
                {
                    "name": f"UM-P3 S04 {label}",
                    "code": f"UM-P3-S04-{label}",
                    "company_id": company.id,
                    "privacy_visibility": "followers",
                    "user_id": owner.id,
                }
            )

        cls.project_a = project("project-a", cls.company_a, cls.caller)
        cls.project_a2 = project("project-a2", cls.company_a, cls.caller)
        cls.project_b = project("project-b", cls.company_b, cls.env.user)
        cls.supplier_a = cls.env["res.partner"].create(
            {"name": "UM-P3 S04 supplier A"}
        )
        cls.supplier_b = cls.env["res.partner"].create(
            {"name": "UM-P3 S04 supplier B"}
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "UM-P3 S04 material",
                "purchase_ok": True,
                "standard_price": 10.0,
            }
        )

        def purchase(label, project_record, supplier, company=None):
            company = company or project_record.company_id
            return cls.env["purchase.order"].with_context(cls.context).create(
                {
                    "partner_id": supplier.id,
                    "company_id": company.id,
                    "project_id": project_record.id,
                    "order_line": [
                        (
                            0,
                            0,
                            {
                                "name": f"UM-P3 S04 {label} line",
                                "product_id": cls.product.id,
                                "product_qty": 10.0,
                                "product_uom": cls.product.uom_po_id.id,
                                "price_unit": 10.0,
                                "project_id": project_record.id,
                                "date_planned": "2026-07-26 00:00:00",
                            },
                        )
                    ],
                }
            )

        cls.po_a1 = purchase("po-a1", cls.project_a, cls.supplier_a)
        cls.po_a2 = purchase("po-a2", cls.project_a, cls.supplier_a)
        cls.po_project_conflict = purchase(
            "po-project-conflict", cls.project_a2, cls.supplier_a
        )
        cls.po_supplier_conflict = purchase(
            "po-supplier-conflict", cls.project_a, cls.supplier_b
        )
        cls.po_company_b = purchase(
            "po-company-b", cls.project_b, cls.supplier_a, cls.company_b
        )

        def settlement(label, project_record=None, supplier=None):
            return cls.env["sc.material.settlement"].with_context(
                cls.context
            ).create(
                {
                    "name": f"UM-P3 S04 {label}",
                    "project_id": (project_record or cls.project_a).id,
                    "supplier_id": (supplier or cls.supplier_a).id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": cls.product.id,
                                "qty": 1.0,
                                "unit_price": 10.0,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "product_id": cls.product.id,
                                "qty": 2.0,
                                "unit_price": 10.0,
                            },
                        ),
                    ],
                }
            )

        cls.settlement = settlement("settlement")
        cls.caller_env = cls.env(
            user=cls.caller,
            context={
                **cls.env.context,
                "allowed_company_ids": [cls.company_a.id],
                "tracking_disable": True,
            },
        )

    def _scope(self, settlement_line, purchase_line, env=None):
        env = env or self.env
        return env["sc.material.settlement.purchase.scope"].create(
            {
                "settlement_id": settlement_line.settlement_id.id,
                "settlement_line_id": settlement_line.id,
                "purchase_order_line_id": purchase_line.id,
            }
        )

    def test_single_and_multi_purchase_projection_and_preservation(self):
        first = self._scope(
            self.settlement.line_ids[0], self.po_a1.order_line[0]
        )
        self.assertEqual(self.settlement.purchase_order_id, self.po_a1)
        self.assertEqual(self.settlement.project_id, self.project_a)
        self.assertEqual(self.settlement.supplier_id, self.supplier_a)
        second = self._scope(
            self.settlement.line_ids[1], self.po_a2.order_line[0]
        )
        self.assertFalse(self.settlement.purchase_order_id)
        self.assertEqual(
            set(self.settlement.purchase_scope_ids.ids),
            {first.id, second.id},
        )
        self.assertEqual(
            set(
                self.settlement.purchase_scope_ids.mapped(
                    "purchase_order_line_id"
                ).ids
            ),
            {self.po_a1.order_line.id, self.po_a2.order_line.id},
        )

    def test_cross_project_supplier_and_company_sets_are_rejected(self):
        self._scope(self.settlement.line_ids[0], self.po_a1.order_line[0])
        for purchase in (
            self.po_project_conflict,
            self.po_supplier_conflict,
            self.po_company_b,
        ):
            with self.env.cr.savepoint(), self.assertRaises(ValidationError):
                self._scope(
                    self.settlement.line_ids[1],
                    purchase.order_line[0],
                )

    def test_explicit_header_conflicts_and_non_override_hold(self):
        self._scope(self.settlement.line_ids[0], self.po_a1.order_line[0])
        for vals in (
            {"project_id": self.project_a2.id},
            {"supplier_id": self.supplier_b.id},
            {"purchase_order_id": self.po_a2.id},
        ):
            with self.env.cr.savepoint(), self.assertRaises(ValidationError):
                self.settlement.write(vals)
        self.assertEqual(self.po_a1.project_id, self.project_a)
        self.assertEqual(self.po_a1.partner_id, self.supplier_a)

    def test_direct_create_write_unlink_revalidates_final_set(self):
        scope = self._scope(
            self.settlement.line_ids[0], self.po_a1.order_line[0]
        )
        scope.write({"purchase_order_line_id": self.po_a2.order_line.id})
        self.assertEqual(self.settlement.purchase_order_id, self.po_a2)
        scope.unlink()
        self.assertFalse(self.settlement.purchase_scope_ids)
        self.assertFalse(self.settlement.purchase_order_id)

    def test_one2many_and_import_paths_cannot_bypass_validation(self):
        self.settlement.write(
            {
                "purchase_scope_ids": [
                    (
                        0,
                        0,
                        {
                            "settlement_line_id": self.settlement.line_ids[0].id,
                            "purchase_order_line_id": self.po_a1.order_line.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "settlement_line_id": self.settlement.line_ids[1].id,
                            "purchase_order_line_id": self.po_a2.order_line.id,
                        },
                    ),
                ]
            }
        )
        self.assertEqual(len(self.settlement.purchase_scope_ids), 2)
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            self.env[
                "sc.material.settlement.purchase.scope"
            ].with_context(import_file=True).create(
                {
                    "settlement_id": self.settlement.id,
                    "settlement_line_id": self.settlement.line_ids[0].id,
                    "purchase_order_line_id": (
                        self.po_project_conflict.order_line.id
                    ),
                }
            )

    def test_no_automatic_matching_or_historical_backfill(self):
        unrelated = self.env["sc.material.settlement"].with_context(
            self.context
        ).create(
            {
                "name": "UM-P3 S04 unrelated",
                "project_id": self.project_a.id,
                "supplier_id": self.supplier_a.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "qty": 1.0,
                            "unit_price": 10.0,
                        },
                    )
                ],
            }
        )
        self.assertFalse(unrelated.purchase_scope_ids)
        self.assertFalse(unrelated.purchase_order_id)
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            self.env["sc.material.settlement"].with_context(
                self.context
            ).create(
                {
                    "name": "UM-P3 S04 header-only purchase",
                    "project_id": self.project_a.id,
                    "supplier_id": self.supplier_a.id,
                    "purchase_order_id": self.po_a1.id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "qty": 1.0,
                                "unit_price": 10.0,
                            },
                        )
                    ],
                }
            )

    def test_purchase_mutations_revalidate_and_refresh_projection(self):
        scope = self._scope(
            self.settlement.line_ids[0], self.po_a1.order_line[0]
        )
        self.po_a1.write({"partner_id": self.supplier_b.id})
        self.assertEqual(self.settlement.supplier_id, self.supplier_b)
        self.po_a1.order_line.write({"project_id": self.project_a2.id})
        self.assertEqual(self.settlement.project_id, self.project_a2)
        self.assertEqual(scope.purchase_order_id, self.po_a1)

    def test_relation_blocks_destructive_parent_deletion(self):
        scope = self._scope(
            self.settlement.line_ids[0], self.po_a1.order_line[0]
        )
        for record in (
            self.settlement,
            self.settlement.line_ids[0],
            self.po_a1,
            self.po_a1.order_line[0],
        ):
            with self.env.cr.savepoint(), self.assertRaises(UserError):
                record.unlink()
        scope.unlink()

    def test_unauthorized_and_nonexistent_identifiers_are_equivalent(self):
        observations = []
        for line_id in (
            self.po_company_b.order_line.id,
            self.po_company_b.order_line.id + 1000000,
        ):
            with self.env.cr.savepoint(), self.assertRaises(AccessError) as raised:
                self.caller_env[
                    "sc.material.settlement.purchase.scope"
                ].create(
                    {
                        "settlement_id": self.settlement.id,
                        "settlement_line_id": self.settlement.line_ids[0].id,
                        "purchase_order_line_id": line_id,
                    }
                )
            observations.append((type(raised.exception), str(raised.exception)))
        self.assertEqual(observations[0], observations[1])

    def test_allowed_company_and_administrator_contracts_hold(self):
        scope = self._scope(
            self.settlement.line_ids[0], self.po_a1.order_line[0]
        )
        self.assertIn(scope, self.settlement.purchase_scope_ids)
        self.assertFalse(
            self.caller_env[
                "sc.material.settlement.purchase.scope"
            ].search([("company_id", "=", self.company_b.id)])
        )
