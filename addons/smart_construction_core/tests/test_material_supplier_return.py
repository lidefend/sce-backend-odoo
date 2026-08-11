# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "material_supplier_return")
class TestMaterialSupplierReturn(TransactionCase):
    def _user(self, login, group_xmlid):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": "%s@invalid.local" % login,
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(group_xmlid).id,
                        ],
                    )
                ],
            }
        )

    def test_supplier_return_is_distinct_from_stock_return_and_quantity_is_conserved(self):
        material_user = self._user(
            "supplier_return_user",
            "smart_construction_core.group_sc_cap_material_user",
        )
        material_manager = self._user(
            "supplier_return_manager",
            "smart_construction_core.group_sc_cap_material_manager",
        )
        project_only_user = self._user(
            "supplier_return_project_only",
            "smart_construction_core.group_sc_cap_project_user",
        )
        project = self.env["project.project"].create(
            {"name": "材料退货测试项目", "user_id": material_user.id}
        )
        supplier = self.env["res.partner"].create(
            {"name": "材料退货测试供应商", "supplier_rank": 1}
        )
        product = self.env["product.product"].create(
            {"name": "材料退货测试材料", "type": "product"}
        )
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", project.company_id.id)], limit=1
        )
        inbound = self.env["sc.material.inbound"].create(
            {
                "project_id": project.id,
                "supplier_id": supplier.id,
                "warehouse_id": warehouse.id,
                "dest_location_id": warehouse.lot_stock_id.id,
                "state": "received",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_id": product.uom_id.id,
                            "qty": 10,
                            "unit_price": 20,
                        },
                    )
                ],
            }
        )

        with self.assertRaises(AccessError):
            self.env["sc.material.supplier.return"].with_user(project_only_user).create(
                {"project_id": project.id}
            )

        supplier_return = self.env["sc.material.supplier.return"].with_user(
            material_user
        ).create(
            {
                "project_id": project.id,
                "source_inbound_id": inbound.id,
                "supplier_id": supplier.id,
                "warehouse_id": warehouse.id,
                "source_location_id": warehouse.lot_stock_id.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "source_inbound_line_id": inbound.line_ids.id,
                            "product_id": product.id,
                            "product_uom_id": product.uom_id.id,
                            "qty": 6,
                            "unit_price": 20,
                        },
                    )
                ],
            }
        )
        self.assertNotEqual(supplier_return._name, "sc.material.outbound")
        self.assertIn("建议补充退货原因", supplier_return.processing_advisory)
        supplier_return.with_user(material_user).action_submit()
        supplier_return.with_user(material_manager).action_confirm_return()
        self.assertEqual(supplier_return.state, "returned")
        self.assertEqual(supplier_return.amount_total, 120)

        excessive_return = self.env["sc.material.supplier.return"].with_user(
            material_user
        ).create(
            {
                "project_id": project.id,
                "source_inbound_id": inbound.id,
                "supplier_id": supplier.id,
                "warehouse_id": warehouse.id,
                "source_location_id": warehouse.lot_stock_id.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "source_inbound_line_id": inbound.line_ids.id,
                            "product_id": product.id,
                            "product_uom_id": product.uom_id.id,
                            "qty": 5,
                            "unit_price": 20,
                        },
                    )
                ],
            }
        )
        with self.assertRaises(ValidationError):
            excessive_return.with_user(material_user).action_submit()

        action = self.env.ref("smart_construction_core.action_sc_material_supplier_return")
        menu = self.env.ref("smart_construction_core.menu_sc_product_material_return_v1")
        self.assertEqual(action.res_model, "sc.material.supplier.return")
        self.assertEqual(menu.action, action)
