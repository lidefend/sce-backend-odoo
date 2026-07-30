# -*- coding: utf-8 -*-

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged

from odoo.addons.smart_core.core.view_orchestrator import ViewOrchestrator


@tagged("post_install", "-at_install", "smart_core", "tenant_extension")
class TestTenantExtensionStorage(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env["res.company"].create({"name": "Extension fixture A"})
        cls.company_b = cls.env["res.company"].create({"name": "Extension fixture B"})
        base_user = cls.env.ref("base.group_user")
        partner_manager = cls.env.ref("base.group_partner_manager")
        cls.user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Tenant extension fixture user",
                "login": "tenant-extension-fixture-user",
                "company_id": cls.company_a.id,
                "company_ids": [Command.set([cls.company_a.id, cls.company_b.id])],
                "groups_id": [Command.set([base_user.id, partner_manager.id])],
            }
        )
        config_admin_group = cls.env.ref(
            "smart_core.group_smart_core_business_config_admin"
        )
        cls.config_admin = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "Tenant extension fixture admin",
                "login": "tenant-extension-fixture-admin",
                "company_id": cls.company_a.id,
                "company_ids": [Command.set([cls.company_a.id])],
                "groups_id": [Command.set([base_user.id, config_admin_group.id])],
            }
        )
        cls.partner_model = cls.env["ir.model"]._get("res.partner")
        cls.action_a = cls.env["ir.actions.act_window"].create(
            {"name": "Extension fixture action A", "res_model": "res.partner", "view_mode": "form"}
        )
        cls.action_b = cls.env["ir.actions.act_window"].create(
            {"name": "Extension fixture action B", "res_model": "res.partner", "view_mode": "form"}
        )
        cls.partner_a = cls.env["res.partner"].create(
            {"name": "Extension record A", "company_id": cls.company_a.id}
        )
        cls.partner_b = cls.env["res.partner"].create(
            {"name": "Extension record B", "company_id": cls.company_b.id}
        )

    def _definition(self, company, action, key, data_type="char", **extra):
        values = {
            "company_id": company.id,
            "model_id": self.partner_model.id,
            "extension_key": key,
            "display_name": key.replace("_", " ").title(),
            "data_type": data_type,
            "slot_key": "business_extensions",
            "slot_label": "Business extensions",
            "action_id": action.id,
            "active": True,
            "lifecycle_state": "active",
            "created_source": "test_fixture",
        }
        values.update(extra)
        return self.env["ui.tenant.extension.field"].create(values)

    def _column_count(self, table):
        self.env.cr.execute(
            """
            SELECT COUNT(*)
              FROM information_schema.columns
             WHERE table_schema = current_schema()
               AND table_name = %s
            """,
            [table],
        )
        return int(self.env.cr.fetchone()[0])

    def test_definition_does_not_change_business_schema_or_global_fields(self):
        column_count = self._column_count("res_partner")
        global_field_count = self.env["ir.model.fields"].search_count(
            [("model", "=", "res.partner")]
        )
        self._definition(self.company_a, self.action_a, "site_reference")
        self.assertEqual(self._column_count("res_partner"), column_count)
        self.assertEqual(
            self.env["ir.model.fields"].search_count([("model", "=", "res.partner")]),
            global_field_count,
        )

    def test_contract_is_company_action_and_role_scoped(self):
        definition_a = self._definition(
            self.company_a,
            self.action_a,
            "company_note",
            role_group_ids=[Command.set([self.env.ref("base.group_user").id])],
        )
        self._definition(self.company_b, self.action_b, "company_note", data_type="integer")
        service_a = self.env["ui.tenant.extension.field"].with_user(self.user).with_company(
            self.company_a
        )
        contract_a = service_a.contract_for(
            model_name="res.partner",
            view_type="form",
            action_id=self.action_a.id,
        )
        self.assertEqual([row["extension_id"] for row in contract_a], [definition_a.id])
        self.assertEqual(contract_a[0]["source"], "tenant_extension")
        self.assertEqual(contract_a[0]["slot_key"], "business_extensions")
        self.assertEqual(
            service_a.contract_for(
                model_name="res.partner",
                view_type="form",
                action_id=self.action_b.id,
            ),
            [],
        )
        service_b = service_a.with_company(self.company_b)
        contract_b = service_b.contract_for(
            model_name="res.partner",
            view_type="form",
            action_id=self.action_b.id,
        )
        self.assertEqual(len(contract_b), 1)
        self.assertEqual(contract_b[0]["data_type"], "integer")
        with self.assertRaises(AccessError):
            self.env["ui.tenant.extension.field"].with_user(self.user).search([])

    def test_runtime_contract_keeps_extensions_outside_standard_fields(self):
        definition = self._definition(
            self.company_a,
            self.action_a,
            "contract_probe",
        )
        runtime_env = self.env["res.partner"].with_user(self.user).with_company(
            self.company_a
        ).env
        runtime = ViewOrchestrator(runtime_env).compose(
            {"contract_version": "v2", "fields": {"name": {"type": "char"}}},
            model_name="res.partner",
            view_type="form",
            action_id=self.action_a.id,
        )
        self.assertEqual(
            [row["extension_id"] for row in runtime["tenant_extension_fields"]],
            [definition.id],
        )
        self.assertEqual(list(runtime["fields"]), ["name"])
        self.assertNotIn("contract_probe", runtime["fields"])

    def test_direct_model_acl_and_record_rules_do_not_leak_other_company(self):
        definition_a = self._definition(
            self.company_a, self.action_a, "admin_visible"
        )
        self._definition(self.company_b, self.action_b, "admin_hidden")
        with self.assertRaises(AccessError):
            self.env["ui.tenant.extension.value"].with_user(self.user).search([])
        definitions = self.env["ui.tenant.extension.field"].with_user(
            self.config_admin
        ).search([])
        self.assertIn(definition_a, definitions)
        self.assertFalse(definitions.filtered(lambda row: row.company_id == self.company_b))

    def test_contract_cache_is_invalidated_on_definition_change(self):
        service = self.env["ui.tenant.extension.field"].with_user(self.user).with_company(
            self.company_a
        )
        args = {
            "model_name": "res.partner",
            "view_type": "form",
            "action_id": self.action_a.id,
        }
        self.assertEqual(service.contract_for(**args), [])
        definition = self._definition(self.company_a, self.action_a, "cache_probe")
        self.assertEqual(
            [row["extension_id"] for row in service.contract_for(**args)],
            [definition.id],
        )
        definition.write({"active": False})
        self.assertEqual(service.contract_for(**args), [])

    def test_typed_values_preserve_null_false_zero_negative_and_precision(self):
        Value = self.env["ui.tenant.extension.value"].with_user(self.user).with_company(
            self.company_a
        )
        boolean = self._definition(self.company_a, self.action_a, "confirmed", "boolean")
        integer = self._definition(self.company_a, self.action_a, "crew_delta", "integer")
        decimal = self._definition(
            self.company_a,
            self.action_a,
            "measured_ratio",
            "float",
            precision=8,
            scale=3,
        )
        Value.set_typed_value(boolean, self.partner_a.id, False)
        Value.set_typed_value(integer, self.partner_a.id, 0)
        Value.set_typed_value(decimal, self.partner_a.id, -12.345)
        self.assertIs(Value.read_for_record(boolean, self.partner_a.id), False)
        self.assertEqual(Value.read_for_record(integer, self.partner_a.id), 0)
        self.assertEqual(Value.read_for_record(decimal, self.partner_a.id), -12.345)
        Value.set_typed_value(boolean, self.partner_a.id, None)
        self.assertIsNone(Value.read_for_record(boolean, self.partner_a.id))
        with self.assertRaises(ValidationError):
            Value.set_typed_value(decimal, self.partner_a.id, 1.2345)

    def test_monetary_selection_and_relation_semantics(self):
        Value = self.env["ui.tenant.extension.value"].with_user(self.user).with_company(
            self.company_a
        )
        monetary = self._definition(
            self.company_a,
            self.action_a,
            "insured_amount",
            "monetary",
            precision=16,
            scale=2,
            currency_strategy="company",
        )
        selection = self._definition(
            self.company_a,
            self.action_a,
            "risk_level",
            "selection",
            selection_definition=[
                {"key": "low", "label": "Low"},
                {"key": "high", "label": "High"},
            ],
        )
        relation = self._definition(
            self.company_a,
            self.action_a,
            "local_contact",
            "many2one",
            relation_model_id=self.partner_model.id,
        )
        Value.set_typed_value(monetary, self.partner_a.id, -8.5)
        self.assertEqual(
            Value.read_for_record(monetary, self.partner_a.id),
            {"amount": -8.5, "currency_id": self.company_a.currency_id.id},
        )
        Value.set_typed_value(selection, self.partner_a.id, "high")
        self.assertEqual(Value.read_for_record(selection, self.partner_a.id), "high")
        with self.assertRaises(ValidationError):
            Value.set_typed_value(selection, self.partner_a.id, "unknown")
        Value.set_typed_value(relation, self.partner_a.id, self.partner_a.id)
        self.assertEqual(
            Value.read_for_record(relation, self.partner_a.id),
            {"model": "res.partner", "id": self.partner_a.id},
        )
        with self.assertRaises(AccessError):
            Value.set_typed_value(relation, self.partner_a.id, self.partner_b.id)

    def test_cross_company_values_and_exports_fail_closed(self):
        definition = self._definition(self.company_a, self.action_a, "private_note")
        Value = self.env["ui.tenant.extension.value"].with_user(self.user).with_company(
            self.company_a
        )
        Value.set_typed_value(definition, self.partner_a.id, "A only")
        with self.assertRaises(AccessError):
            Value.read_for_record(definition, self.partner_b.id)
        service_b = Value.with_company(self.company_b)
        with self.assertRaises(AccessError):
            service_b.read_for_record(definition, self.partner_a.id)
        self.assertEqual(
            Value.export_for_records(definition, [self.partner_a.id]),
            [
                {
                    "extension_id": definition.id,
                    "extension_key": "private_note",
                    "record_id": self.partner_a.id,
                    "value": "A only",
                }
            ],
        )

    def test_keys_and_slots_are_stable_and_product_fields_cannot_be_overridden(self):
        for key in ("x_customer_note", "legacy_note", "p1_visible_deadbeef0000"):
            with self.assertRaises(ValidationError):
                self._definition(self.company_a, self.action_a, key)
        with self.assertRaises(ValidationError):
            self._definition(self.company_a, self.action_a, "name")
        with self.assertRaises(ValidationError):
            self._definition(
                self.company_a,
                self.action_a,
                "invalid_slot",
                slot_key="客户扩展",
            )

    def test_migration_service_defaults_to_dry_run_and_is_idempotent(self):
        definition = self._definition(self.company_a, self.action_a, "migration_probe")
        Service = self.env[
            "ui.tenant.extension.migration.service"
        ].with_user(self.user).with_company(self.company_a)
        rows = [{"record_id": self.partner_a.id, "value": "fixture"}]
        dry_run = Service.migrate_rows(definition, rows)
        self.assertTrue(dry_run["dry_run"])
        self.assertEqual(dry_run["old_columns_deleted"], 0)
        self.assertEqual(
            self.env["ui.tenant.extension.value"].search_count(
                [("field_definition_id", "=", definition.id)]
            ),
            0,
        )
        with self.assertRaises(AccessError):
            Service.migrate_rows(definition, rows, dry_run=False)
        executable = Service.with_context(
            tenant_extension_isolated_migration=True
        )
        first = executable.migrate_rows(definition, rows, dry_run=False)
        second = executable.migrate_rows(definition, rows, dry_run=False)
        self.assertEqual(first["checksum"], second["checksum"])
        self.assertEqual(
            self.env["ui.tenant.extension.value"].search_count(
                [("field_definition_id", "=", definition.id)]
            ),
            1,
        )

    def test_company_extension_cleanup_requires_retire_and_explicit_purge(self):
        company = self.env["res.company"].create({"name": "Extension cleanup fixture"})
        action = self.env["ir.actions.act_window"].create(
            {"name": "Cleanup fixture", "res_model": "res.partner", "view_mode": "form"}
        )
        partner = self.env["res.partner"].create(
            {"name": "Cleanup fixture record", "company_id": company.id}
        )
        definition = self._definition(company, action, "cleanup_probe")
        Value = self.env["ui.tenant.extension.value"].with_company(company)
        Value.set_typed_value(definition, partner.id, "fixture")
        Definition = self.env["ui.tenant.extension.field"]
        with self.assertRaises(ValidationError):
            Definition.purge_retired_company_extensions(company)
        Definition.retire_company_extensions(company)
        report = Definition.purge_retired_company_extensions(company)
        self.assertTrue(report["dry_run"])
        self.assertEqual(report["definition_count"], 1)
        with self.assertRaises(AccessError):
            Definition.purge_retired_company_extensions(company, dry_run=False)
        Definition.with_context(
            tenant_extension_company_purge=True
        ).purge_retired_company_extensions(company, dry_run=False)
        self.assertFalse(definition.exists())
