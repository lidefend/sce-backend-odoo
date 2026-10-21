#!/usr/bin/env python3
from __future__ import annotations

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError
from odoo.addons.smart_core.core.intent_surface_builder import IntentSurfaceBuilder

from odoo.addons.smart_construction_core.handlers.product_system_parameter_change import (
    ProductSystemParameterPublishHandler,
    ProductSystemParameterRollbackHandler,
)
from odoo.addons.smart_construction_core.handlers.product_system_parameter_catalog import (
    ProductSystemParameterPreviewHandler,
    ProductSystemParameterCatalogHandler,
)
from odoo.addons.smart_construction_core.services.default_payment_terms import (
    resolve_default_payment_term,
)


@tagged("post_install", "-at_install", "sc_gate", "product_system_parameter_change")
class TestProductSystemParameterChange(TransactionCase):
    def _publish(self, parameter_key, proposed_value):
        handler = ProductSystemParameterPublishHandler(self.env)
        return handler.run(
            {
                "parameter_key": parameter_key,
                "proposed_value": proposed_value,
                "change_reason": "test",
            }
        )

    def _rollback(self, change_id):
        handler = ProductSystemParameterRollbackHandler(self.env)
        return handler.run({"change_id": change_id})

    def test_publish_writes_company_authority_and_records_snapshot(self):
        self.env.company.write(
            {
                "sc_cost_from_account_move": True,
                "sc_cost_from_purchase": False,
                "sc_cost_from_stock": False,
            }
        )
        result = self._publish("cost_ledger_source", "purchase_order")
        self.assertTrue(result["ok"])
        self.assertFalse(self.env.company.sc_cost_from_account_move)
        self.assertTrue(self.env.company.sc_cost_from_purchase)
        self.assertFalse(self.env.company.sc_cost_from_stock)
        change = self.env["sc.product.system.parameter.change"].browse(result["data"]["change"]["id"])
        self.assertEqual(change.state, "published")
        self.assertEqual(change.previous_value, "account_move")
        self.assertEqual(change.parameter_key, "cost_ledger_source")

    def test_rollback_restores_previous_value(self):
        self.env.company.write(
            {
                "sc_cost_from_account_move": True,
                "sc_cost_from_purchase": False,
                "sc_cost_from_stock": False,
            }
        )
        published = self._publish("cost_ledger_source", "stock_move")
        self.assertTrue(published["ok"])
        change_id = published["data"]["change"]["id"]
        result = self._rollback(change_id)
        self.assertTrue(result["ok"])
        self.assertTrue(self.env.company.sc_cost_from_account_move)
        self.assertFalse(self.env.company.sc_cost_from_stock)
        change = self.env["sc.product.system.parameter.change"].browse(change_id)
        self.assertEqual(change.state, "rolled_back")
        self.assertEqual(result["data"]["restored_value"], "account_move")

    def test_publish_rejects_value_outside_allowed_set(self):
        before_ids = self.env["sc.product.system.parameter.change"].search([]).ids
        self.env.company.write(
            {
                "sc_cost_from_account_move": True,
                "sc_cost_from_purchase": False,
                "sc_cost_from_stock": False,
            }
        )
        result = self._publish("cost_ledger_source", "not-a-source")
        self.assertFalse(result["ok"])
        self.assertEqual(result["data"]["reason_code"], "VALUE_NOT_ALLOWED")
        self.assertTrue(self.env.company.sc_cost_from_account_move)
        self.assertEqual(self.env["sc.product.system.parameter.change"].search([]).ids, before_ids)

    def test_publish_rejects_planned_parameter(self):
        result = self._publish("tax_rate", 0.13)
        self.assertFalse(result["ok"])
        self.assertEqual(result["data"]["reason_code"], "NOT_IMPLEMENTED")

    def test_publish_and_rollback_approval_mode(self):
        Policy = self.env["sc.approval.policy"].sudo()
        policy = Policy.get_active_policy(
            "payment.request", company=self.env.company
        )
        self.assertTrue(policy)
        policy.write({"approval_required": True, "mode": "single"})
        published = self._publish("approval_mode", "multi")
        self.assertTrue(published["ok"])
        self.assertEqual(policy.mode, "linear")
        self.assertTrue(policy.approval_required)
        change = self.env["sc.product.system.parameter.change"].browse(
            published["data"]["change"]["id"]
        )
        self.assertEqual(change.state, "published")
        self.assertEqual(change.previous_value, "single")
        rolled_back = self._rollback(change.id)
        self.assertTrue(rolled_back["ok"])
        self.assertEqual(policy.mode, "single")

    def test_publish_and_rollback_default_payment_terms(self):
        self.env.company.write({"sc_default_payment_terms": "net30"})
        published = self._publish("default_payment_terms", "advance")
        self.assertTrue(published["ok"])
        self.assertEqual(self.env.company.sc_default_payment_terms, "advance")
        change = self.env["sc.product.system.parameter.change"].browse(
            published["data"]["change"]["id"]
        )
        self.assertEqual(change.state, "published")
        self.assertEqual(change.previous_value, "net30")
        rolled_back = self._rollback(change.id)
        self.assertTrue(rolled_back["ok"])
        self.assertEqual(self.env.company.sc_default_payment_terms, "net30")

    def test_publish_rejects_approval_mode_outside_domain(self):
        before_ids = self.env["sc.product.system.parameter.change"].search([]).ids
        result = self._publish("approval_mode", "parallel")
        self.assertFalse(result["ok"])
        self.assertEqual(result["data"]["reason_code"], "VALUE_NOT_ALLOWED")
        self.assertEqual(
            self.env["sc.product.system.parameter.change"].search([]).ids, before_ids
        )

    def test_publish_rejects_default_payment_terms_outside_domain(self):
        before_ids = self.env["sc.product.system.parameter.change"].search([]).ids
        result = self._publish("default_payment_terms", "net120")
        self.assertFalse(result["ok"])
        self.assertEqual(result["data"]["reason_code"], "VALUE_NOT_ALLOWED")
        self.assertEqual(
            self.env["sc.product.system.parameter.change"].search([]).ids, before_ids
        )

    def test_default_payment_terms_resolve_to_account_payment_term(self):
        for code, xmlid in (
            ("net30", "account.account_payment_term_30days"),
            ("net60", "smart_construction_core.account_payment_term_60days"),
            ("advance", "account.account_payment_term_immediate"),
        ):
            self.env.company.write({"sc_default_payment_terms": code})
            term = resolve_default_payment_term(self.env)
            self.assertEqual(term, self.env.ref(xmlid))
        self.env.company.write({"sc_default_payment_terms": "custom"})
        self.assertFalse(resolve_default_payment_term(self.env))

    def test_purchase_order_default_payment_term_from_company(self):
        self.env.company.write({"sc_default_payment_terms": "net60"})
        values = self.env["purchase.order"].default_get(["payment_term_id"])
        term = self.env.ref("smart_construction_core.account_payment_term_60days")
        self.assertEqual(values.get("payment_term_id"), term.id)

    def test_rollback_rejects_non_published_change(self):
        change = self.env["sc.product.system.parameter.change"].sudo().create(
            {
                "parameter_key": "cost_ledger_source",
                "proposed_value": "disabled",
                "previous_value": "account_move",
                "state": "draft",
                "company_id": self.env.company.id,
            }
        )
        result = self._rollback(change.id)
        self.assertFalse(result["ok"])
        self.assertEqual(result["data"]["reason_code"], "CHANGE_NOT_ROLLBACKABLE")

    def test_rollback_rejects_superseded_change_even_when_value_matches(self):
        self.env.company.write({"sc_default_payment_terms": "net30"})
        first = self._publish("default_payment_terms", "advance")["data"]["change"]
        second = self._publish("default_payment_terms", "advance")["data"]["change"]
        result = self._rollback(first["id"])
        self.assertFalse(result["ok"])
        self.assertEqual(result["data"]["reason_code"], "CHANGE_SUPERSEDED")
        self.assertEqual(self.env.company.sc_default_payment_terms, "advance")
        Change = self.env["sc.product.system.parameter.change"]
        self.assertEqual(Change.browse(first["id"]).state, "published")
        self.assertTrue(self._rollback(second["id"])["ok"])
        self.assertTrue(self._rollback(first["id"])["ok"])
        self.assertEqual(self.env.company.sc_default_payment_terms, "net30")

    def test_rollback_rejects_authority_drift_without_changing_audit(self):
        self.env.company.write({"sc_default_payment_terms": "net30"})
        change = self._publish("default_payment_terms", "advance")["data"]["change"]
        self.env.company.write({"sc_default_payment_terms": "net60"})
        result = self._rollback(change["id"])
        self.assertFalse(result["ok"])
        self.assertEqual(result["data"]["reason_code"], "PARAMETER_VALUE_CHANGED")
        self.assertEqual(self.env.company.sc_default_payment_terms, "net60")
        record = self.env["sc.product.system.parameter.change"].browse(change["id"])
        self.assertEqual(record.state, "published")
        self.assertFalse(record.rolled_back_at)

    def test_other_parameter_does_not_block_rollback(self):
        self.env.company.write({"sc_default_payment_terms": "net30"})
        change = self._publish("default_payment_terms", "advance")["data"]["change"]
        self.assertTrue(self._publish("cost_ledger_source", "purchase_order")["ok"])
        self.assertTrue(self._rollback(change["id"])["ok"])
        self.assertEqual(self.env.company.sc_default_payment_terms, "net30")
        self.assertTrue(self.env.company.sc_cost_from_purchase)

    def test_unauthorized_user_cannot_publish_or_rollback(self):
        self.env.company.write({"sc_default_payment_terms": "net30"})
        change = self._publish("default_payment_terms", "advance")["data"]["change"]
        user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Parameter reader", "login": "parameter_reader_test",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            "company_id": self.env.company.id,
            "company_ids": [(6, 0, [self.env.company.id])],
        })
        env = self.env(user=user)
        visible, _ = IntentSurfaceBuilder().collect(env, user)
        for intent in ("catalog", "preview", "publish", "rollback"):
            self.assertNotIn("sc.product.system_parameter." + intent, visible)
        for handler_type in (ProductSystemParameterCatalogHandler, ProductSystemParameterPreviewHandler):
            handler = handler_type(env)
            with self.assertRaises(AccessError):
                handler.run({"intent": handler.INTENT_TYPE, "params": {
                    "parameter_key": "default_payment_terms", "proposed_value": "net60",
                }})
        for handler, payload in (
            (ProductSystemParameterPublishHandler(env), {
                "parameter_key": "default_payment_terms", "proposed_value": "net60",
            }),
            (ProductSystemParameterRollbackHandler(env), {"change_id": change["id"]}),
        ):
            with self.assertRaises(AccessError):
                handler.run(payload)
        self.assertEqual(self.env.company.sc_default_payment_terms, "advance")
        self.assertEqual(self.env["sc.product.system.parameter.change"].browse(change["id"]).state, "published")

    def _config_actor_env(self):
        user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Parameter configuration boundary", "login": "parameter_config_boundary",
            "groups_id": [(6, 0, [
                self.env.ref("smart_construction_core.group_sc_cap_business_config_admin").id,
                self.env.ref("smart_core.group_smart_core_non_customer_data_user").id,
            ])],
            "company_id": self.env.company.id, "company_ids": [(6, 0, [self.env.company.id])],
        })
        return self.env(user=user, su=False)

    def test_config_admin_cannot_write_parameter_authority_directly(self):
        env = self._config_actor_env()
        before = env.company.sc_default_payment_terms
        for vals in ({"sc_default_payment_terms": "advance"}, {"sc_cost_from_stock": True}):
            with self.assertRaises(AccessError):
                env.company.with_context(sudo=True, parameter_change_set=True).write(vals)
        self.assertEqual(env.company.sc_default_payment_terms, before)

    def test_payment_policy_raw_identity_and_mode_mutations_are_rejected(self):
        env = self._config_actor_env()
        policy = env["sc.approval.policy"].get_active_policy("payment.request", company=env.company)
        self.assertTrue(policy)
        for vals in ({"approval_required": False}, {"mode": "none"}, {"active": False},
                     {"company_id": False}, {"target_model": "purchase.order"}):
            with self.assertRaises(AccessError):
                policy.with_context(sudo=True, parameter_change_set=True).write(vals)
        with self.assertRaises(AccessError):
            policy.unlink()
        with self.assertRaises(AccessError):
            env["sc.approval.policy"].create({"name": "Bypass", "target_model": "payment.request"})
        with self.assertRaises(AccessError):
            env["sc.approval.policy"].with_context(default_target_model="payment.request").create({
                "name": "Default bypass", "code": "default_parameter_bypass",
            })
        # Unrelated step/label maintenance remains governed by ordinary ACLs.
        policy.write({"name": policy.name})

    def test_config_admin_managed_publish_and_rollback_still_work(self):
        env = self._config_actor_env()
        for key, proposed in (("default_payment_terms", "advance"), ("approval_mode", "disabled")):
            published = ProductSystemParameterPublishHandler(env).run({
                "parameter_key": key, "proposed_value": proposed, "change_reason": "boundary test",
            })
            self.assertTrue(published["ok"], published)
            change = published["data"]["change"]
            restored = ProductSystemParameterRollbackHandler(env).run({"change_id": change["id"]})
            self.assertTrue(restored["ok"], restored)
            self.assertEqual(restored["data"]["change"]["state"], "rolled_back")

    def test_intent_envelope_preview_publish_business_default_and_rollback(self):
        self.env.company.write({"sc_default_payment_terms": "net30"})
        params = {"parameter_key": "default_payment_terms", "proposed_value": "advance"}
        preview_handler = ProductSystemParameterPreviewHandler(self.env)
        preview = preview_handler.run({"intent": preview_handler.INTENT_TYPE, "params": params})
        self.assertTrue(preview["data"]["ok"], preview)
        visible, _ = IntentSurfaceBuilder().collect(self.env, self.env.user)
        for intent in ("catalog", "preview", "publish", "rollback"):
            self.assertIn("sc.product.system_parameter." + intent, visible)
        catalog = ProductSystemParameterCatalogHandler(self.env).run()
        self.assertTrue(catalog["ok"])
        self.assertTrue(catalog["data"]["parameters"])
        publish_handler = ProductSystemParameterPublishHandler(self.env)
        published = publish_handler.run({"intent": publish_handler.INTENT_TYPE, "params": params})
        self.assertTrue(published["ok"], published)
        self.assertEqual(self.env["purchase.order"].default_get(["payment_term_id"])["payment_term_id"],
                         self.env.ref("account.account_payment_term_immediate").id)
        rollback_handler = ProductSystemParameterRollbackHandler(self.env)
        restored = rollback_handler.run({"intent": rollback_handler.INTENT_TYPE,
                                         "params": {"change_id": published["data"]["change"]["id"]}})
        self.assertTrue(restored["ok"], restored)
        self.assertEqual(self.env["purchase.order"].default_get(["payment_term_id"])["payment_term_id"],
                         self.env.ref("account.account_payment_term_30days").id)
