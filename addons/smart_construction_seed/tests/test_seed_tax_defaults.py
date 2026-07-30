# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_smoke")
class TestSeedTaxDefaults(TransactionCase):
    def test_fresh_product_does_not_publish_business_tax_seed_records(self):
        bootstrap = self.env.ref("base.main_company")
        self.assertTrue(bootstrap.is_platform_bootstrap_company)
        for xmlid in (
            "smart_construction_seed.tax_1",
            "smart_construction_seed.tax_3",
            "smart_construction_seed.tax_6",
            "smart_construction_seed.tax_9",
            "smart_construction_seed.tax_13",
        ):
            self.assertFalse(self.env.ref(xmlid, raise_if_not_found=False))
        self.assertFalse(
            self.env["account.tax"].sudo().search(
                [
                    ("company_id", "=", bootstrap.id),
                    ("type_tax_use", "=", "none"),
                    ("tax_group_id.name", "=", "合同税率"),
                ],
                limit=1,
            )
        )

    def test_registered_business_company_can_receive_contract_tax_defaults(self):
        importer_group = self.env.ref(
            "smart_core.group_smart_core_tenant_payload_importer"
        )
        self.env.user.write({"groups_id": [(4, importer_group.id)]})
        company = self.env["res.company"].create({"name": "Registered company fixture"})
        self.env["sc.tenant.company.registration"].with_context(
            sc_tenant_payload_import=True
        ).create(
            {
                "tenant_key": "registered-fixture",
                "company_id": company.id,
                "source_module": "test_tenant_payload",
                "source_external_key": "company-1",
            }
        )

        taxes = self.env["account.tax"].sudo().search(
            [
                ("company_id", "=", company.id),
                ("type_tax_use", "=", "none"),
                ("tax_group_id.name", "=", "合同税率"),
            ]
        )
        self.assertEqual(set(taxes.mapped("amount")), {1.0, 3.0, 6.0, 9.0, 13.0})
        self.assertFalse(
            self.env["account.tax"].sudo().search(
                [
                    ("company_id.is_platform_bootstrap_company", "=", True),
                    ("type_tax_use", "=", "none"),
                    ("tax_group_id.name", "=", "合同税率"),
                ],
                limit=1,
            )
        )
