# -*- coding: utf-8 -*-
import json

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import (
    PageAssembler,
)


@tagged("post_install", "-at_install", "smart_core", "relation_entry_override")
class TestRelationEntryOverrideFailClosed(TransactionCase):
    def setUp(self):
        super().setUp()
        self.assembler = PageAssembler(
            self.env,
            self.env["ir.model"].sudo().env,
        )

    def test_consistent_form_occurrences_project_one_override(self):
        override = {"create_mode": "dialog", "action_id": 10, "menu_id": 20}
        views = {
            "form": {"children": [
                {"type": "field", "name": "project_id", "fieldInfo": {"widget_options": {"relation_entry": override}}},
                {"type": "field", "name": "project_id", "fieldInfo": {"widget_options": {"relation_entry": dict(override)}}},
            ]},
            "tree": {"children": [
                {"type": "field", "name": "project_id", "fieldInfo": {}},
            ]},
        }
        resolved, errors = self.assembler._relation_entry_overrides_from_views(views)
        self.assertEqual(resolved, {"project_id": override})
        self.assertEqual(errors, {})

    def test_field_without_override_keeps_generic_relation_path(self):
        resolved, errors = self.assembler._relation_entry_overrides_from_views({
            "form": {"children": [
                {"type": "field", "name": "partner_id", "fieldInfo": {}},
            ]},
        })
        self.assertEqual(resolved, {})
        self.assertEqual(errors, {})

    def test_conflicting_occurrences_fail_closed(self):
        views = {"form": {"children": [
            {"type": "field", "name": "project_id", "fieldInfo": {"widget_options": {"relation_entry": {"action_id": 10, "menu_id": 20}}}},
            {"type": "field", "name": "project_id", "fieldInfo": {"widget_options": {"relation_entry": {"action_id": 11, "menu_id": 20}}}},
        ]}}
        resolved, errors = self.assembler._relation_entry_overrides_from_views(views)
        self.assertEqual(resolved, {})
        self.assertEqual(errors["project_id"], "RELATION_ENTRY_OVERRIDE_OCCURRENCE_CONFLICT")

    def test_missing_or_half_pair_occurrence_fails_closed(self):
        missing = {"form": {"children": [
            {"type": "field", "name": "project_id", "fieldInfo": {"widget_options": {"relation_entry": {"action_id": 10, "menu_id": 20}}}},
            {"type": "field", "name": "project_id", "fieldInfo": {}},
        ]}}
        _, missing_errors = self.assembler._relation_entry_overrides_from_views(missing)
        self.assertEqual(missing_errors["project_id"], "RELATION_ENTRY_OVERRIDE_OCCURRENCE_CONFLICT")
        half_pair = {"form": {"children": [
            {"type": "field", "name": "project_id", "fieldInfo": {"widget_options": {"relation_entry": {"action_id": 10}}}},
        ]}}
        _, half_pair_errors = self.assembler._relation_entry_overrides_from_views(half_pair)
        self.assertEqual(
            half_pair_errors["project_id"],
            "RELATION_ENTRY_OVERRIDE_AUTHORITY_PAIR_INCOMPLETE",
        )
        invalid = {"form": {"children": [
            {"type": "field", "name": "project_id", "fieldInfo": {"widget_options": {"relation_entry": "invalid"}}},
        ]}}
        _, invalid_errors = self.assembler._relation_entry_overrides_from_views(invalid)
        self.assertEqual(
            invalid_errors["project_id"],
            "RELATION_ENTRY_OVERRIDE_INVALID",
        )

    def test_override_cannot_expand_runtime_create_acl(self):
        entry = self.assembler._build_relation_entry_for_field(
            "parent_id",
            {
                "relation": "res.partner",
                "widget_options": {"relation_entry": {"can_create": True}},
            },
            {
                "model": "res.partner",
                "action_id": None,
                "menu_id": None,
                "can_read": True,
                "can_create": False,
            },
        )
        self.assertFalse(entry["can_create"])
        self.assertEqual(entry["create_mode"], "disabled")

    def test_dialog_mode_requires_managed_action_menu_authority(self):
        entry = self.assembler._build_relation_entry_for_field(
            "parent_id",
            {
                "relation": "res.partner",
                "widget_options": {"relation_entry": {"create_mode": "dialog"}},
            },
            {
                "model": "res.partner",
                "action_id": None,
                "menu_id": None,
                "can_read": True,
                "can_create": True,
            },
        )
        self.assertEqual(entry["create_mode"], "disabled")
        self.assertEqual(
            entry["reason_code"],
            "RELATION_ENTRY_OVERRIDE_CREATE_MODE_AUTHORITY_REQUIRED",
        )

    def test_field_authority_is_projected_to_every_native_occurrence(self):
        views = {
            "form": {"children": [
                {"type": "field", "name": "project_id", "fieldInfo": {}},
                {"type": "group", "children": [
                    {"type": "field", "name": "project_id", "fieldInfo": {}},
                ]},
            ]},
        }
        entry = {
            "create_mode": "dialog",
            "action_id": 10,
            "menu_id": 20,
            "can_create": True,
        }
        self.assembler._project_relation_entries_into_views(
            views,
            {"project_id": entry},
        )
        first = views["form"]["children"][0]
        second = views["form"]["children"][1]["children"][0]
        self.assertEqual(first["relation_entry"], entry)
        self.assertEqual(first["fieldInfo"]["relation_entry"], entry)
        self.assertEqual(second["relation_entry"], entry)
        self.assertEqual(second["fieldInfo"]["relation_entry"], entry)


@tagged("post_install", "-at_install", "smart_core", "runtime_view_contract")
class TestRuntimeViewContractFailClosed(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.view = cls.env["ir.ui.view"].create({
            "name": "runtime.contract.partner.tree",
            "model": "res.partner",
            "type": "tree",
            "arch": "<tree><field name='name' string='单位名称'/><field name='email' string='邮箱'/></tree>",
        })
        cls.action = cls.env["ir.actions.act_window"].create({
            "name": "Runtime contract partners",
            "res_model": "res.partner",
            "view_mode": "tree,form",
            "view_id": cls.view.id,
        })
        cls.Contract = cls.env["ui.business.config.contract"].sudo().with_context(active_test=False)

    def _payload(self, columns):
        return {"view_orchestration": {"views": {"tree": {"columns": columns}}}}

    def _sql_publish(self, record, payload):
        self.env.cr.execute(
            "UPDATE ui_business_config_contract SET active=true, status=%s, contract_json=%s WHERE id=%s",
            ["published", json.dumps(payload, ensure_ascii=False), record.id],
        )
        self.env.invalidate_all()
        return self.Contract.browse(record.id)

    def test_valid_action_subset_is_effective(self):
        record = self.Contract.create({
            "name": "runtime.contract.valid.subset",
            "model": "res.partner",
            "view_type": "tree",
            "action_id": self.action.id,
            "status": "published",
            "contract_json": self._payload([
                {"name": "name", "label": "单位名称"},
                {"name": "email", "label": "邮箱"},
            ]),
        })
        effective = self.Contract._effective_view_orchestration_contracts(
            "res.partner", view_type="tree", action_id=self.action.id,
        )
        self.assertIn(record.id, [row.id for row in effective])

    def test_unknown_or_transition_alias_is_rejected_atomically(self):
        record = self.Contract.create({
            "name": "runtime.contract.invalid.alias",
            "model": "res.partner",
            "view_type": "tree",
            "action_id": self.action.id,
            "active": False,
            "status": "draft",
            "contract_json": self._payload([{"name": "name", "label": "单位名称"}]),
        })
        record = self._sql_publish(record, self._payload([
            {"name": "name", "label": "单位名称"},
            {"name": "p1_visible_negative", "label": "过渡字段"},
        ]))
        validation = record._runtime_contract_validation(
            record, requested_view_type="tree", action_id=self.action.id, model_name="res.partner",
        )
        self.assertIn("historical_stale_alias", validation["reason_codes"])
        self.assertIn("runtime_unknown_columns", validation["reason_codes"])
        effective = self.Contract._effective_view_orchestration_contracts(
            "res.partner", view_type="tree", action_id=self.action.id,
        )
        self.assertNotIn(record.id, [row.id for row in effective])

    def test_known_nonmember_cannot_be_published_or_partially_applied(self):
        with self.assertRaises(ValidationError):
            self.Contract.create({
                "name": "runtime.contract.invalid.nonmember",
                "model": "res.partner",
                "view_type": "tree",
                "action_id": self.action.id,
                "status": "published",
                "contract_json": self._payload([
                    {"name": "name", "label": "单位名称"},
                    {"name": "phone", "label": "电话"},
                ]),
            })

    def test_global_contract_is_revalidated_for_each_action_authority(self):
        alternate_view = self.env["ir.ui.view"].create({
            "name": "runtime.contract.partner.alternate.tree",
            "model": "res.partner",
            "type": "tree",
            "arch": "<tree><field name='name' string='单位名称'/></tree>",
        })
        alternate_action = self.env["ir.actions.act_window"].create({
            "name": "Runtime contract alternate partners",
            "res_model": "res.partner",
            "view_mode": "tree,form",
            "view_id": alternate_view.id,
        })
        record = self.Contract.create({
            "name": "runtime.contract.global.action.revalidation",
            "model": "res.partner",
            "view_type": "tree",
            "status": "published",
            "contract_json": self._payload([
                {"name": "name", "label": "单位名称"},
                {"name": "email", "label": "邮箱"},
            ]),
        })
        accepted = self.Contract._effective_view_orchestration_contracts(
            "res.partner", view_type="tree", action_id=self.action.id,
        )
        rejected = self.Contract._effective_view_orchestration_contracts(
            "res.partner", view_type="tree", action_id=alternate_action.id,
        )
        self.assertIn(record.id, [row.id for row in accepted])
        self.assertNotIn(record.id, [row.id for row in rejected])
