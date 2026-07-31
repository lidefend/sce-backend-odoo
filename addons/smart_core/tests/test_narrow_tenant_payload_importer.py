# -*- coding: utf-8 -*-

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "smart_core", "tenant_payload")
class TestNarrowTenantPayloadImporter(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal = cls.env.ref("base.group_user")
        cls.importer = cls.env.ref(
            "smart_core.group_smart_core_tenant_payload_importer"
        )
        cls.data_operator = cls.env.ref(
            "smart_core.group_smart_core_data_operator"
        )
        cls.user = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "Narrow payload importer",
                "login": "narrow-payload-importer",
                "company_id": cls.env.company.id,
                "company_ids": [Command.set([cls.env.company.id])],
                "groups_id": [Command.set([cls.internal.id])],
            }
        )

    def test_importer_closure_and_effective_addition_are_narrow(self):
        self.assertFalse(self.importer.implied_ids)
        before = set(self.user.groups_id.ids)
        self.user.write({"groups_id": [Command.link(self.importer.id)]})
        after = set(self.user.groups_id.ids)
        self.assertEqual(after - before, {self.importer.id})
        self.assertIn(self.internal, self.user.groups_id)
        self.assertNotIn(self.data_operator, self.user.groups_id)

    def test_import_control_write_requires_signed_import_context(self):
        self.user.write({"groups_id": [Command.link(self.importer.id)]})
        Batch = self.env["sc.tenant.payload.import.batch"].with_user(
            self.user
        )
        with self.assertRaisesRegex(
            UserError, "TPV1_SIGNED_IMPORT_CONTEXT_REQUIRED"
        ):
            Batch.create({})

    def test_importer_does_not_enable_general_data_operator(self):
        self.user.write({"groups_id": [Command.link(self.importer.id)]})
        self.assertTrue(
            self.user.has_group(
                "smart_core.group_smart_core_tenant_payload_importer"
            )
        )
        self.assertFalse(
            self.user.has_group("smart_core.group_smart_core_data_operator")
        )
