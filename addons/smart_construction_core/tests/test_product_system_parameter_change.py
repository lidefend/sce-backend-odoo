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

    def _company_parameter_env(self, name):
        company = self.env["res.company"].sudo().create({"name": name})
        return self.env["res.company"].sudo().with_company(company).env

    def _publish_in_company(self, env, value):
        result = ProductSystemParameterPublishHandler(env).run({
            "parameter_key": "approval_mode", "proposed_value": value,
            "change_reason": "company isolation regression",
        })
        self.assertTrue(result["ok"], result)
        return result["data"]["change"]["id"]

    def test_shared_approval_policy_publish_and_rollback_are_company_isolated(self):
        first = self._company_parameter_env("Parameter isolation A")
        second = self._company_parameter_env("Parameter isolation B")
        Policy = self.env["sc.approval.policy"].sudo()
        Policy.search([("target_model", "=", "payment.request"), ("company_id", "=", False)]).write({"active": False})
        group = Policy._group_for_approval_scope("finance_manager")
        self.assertTrue(group)
        shared = Policy.create({
            "name": "Shared payment policy", "code": "test_shared_parameter_policy",
            "company_id": False, "target_model": "payment.request", "mode": "single",
            "manager_group_id": group.id,
            "step_ids": [(0, 0, {"name": "Shared approval", "sequence": 10, "approval_scope_key": "finance_manager", "approve_group_id": group.id})],
        })
        original_steps = shared.step_ids.ids
        change_id = self._publish_in_company(first, "disabled")
        local = Policy.get_active_policy("payment.request", company=first.company)
        self.assertEqual(local.company_id, first.company)
        self.assertNotEqual(local, shared)
        self.assertEqual(local.manager_group_id, group)
        self.assertEqual(local.step_ids.mapped("approve_group_id"), group)
        self.assertFalse(set(local.step_ids.ids) & set(original_steps))
        self.assertFalse(Policy.is_approval_required("payment.request", company=first.company))
        self.assertTrue(Policy.is_approval_required("payment.request", company=second.company))
        result = ProductSystemParameterRollbackHandler(first).run({"change_id": change_id})
        self.assertTrue(result["ok"], result)
        self.assertTrue(Policy.is_approval_required("payment.request", company=first.company))
        self.assertEqual(Policy.get_active_policy("payment.request", company=second.company), shared)
        self.assertEqual(shared.mode, "single")
        self.assertTrue(shared.approval_required)
        self.assertEqual(shared.step_ids.ids, original_steps)
        self.assertEqual(local.company_id, first.company)

    def test_two_companies_can_first_publish_and_rollback_approval(self):
        first = self._company_parameter_env("New parameter company A")
        second = self._company_parameter_env("New parameter company B")
        Policy = self.env["sc.approval.policy"].sudo()
        Policy.search([("target_model", "=", "payment.request"), ("company_id", "=", False)]).write({"active": False})
        first_change = self._publish_in_company(first, "single")
        second_change = self._publish_in_company(second, "multi")
        first_policy = Policy.get_active_policy("payment.request", company=first.company)
        second_policy = Policy.get_active_policy("payment.request", company=second.company)
        self.assertNotEqual(first_policy.code, second_policy.code)
        for env, change in ((first, first_change), (second, second_change)):
            result = ProductSystemParameterRollbackHandler(env).run({"change_id": change})
            self.assertTrue(result["ok"], result)
            self.assertFalse(Policy.is_approval_required("payment.request", company=env.company))
        first_policy.write({"active": False})
        self._publish_in_company(first, "single")
        self.assertEqual(Policy.get_active_policy("payment.request", company=first.company), first_policy)
        self.assertFalse(Policy.is_approval_required("payment.request", company=second.company))

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
        registration = self.env["sc.tenant.company.registration"].sudo()._create_non_customer_space(
            tenant_key="parameter-config-boundary-test", purpose="test",
            company_name="Parameter Configuration Test Space",
        )
        company = registration.company_id
        user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Parameter configuration boundary", "login": "parameter_config_boundary",
            "groups_id": [(6, 0, [
                self.env.ref("smart_construction_core.group_sc_cap_business_config_admin").id,
                self.env.ref("smart_core.group_smart_core_non_customer_data_user").id,
            ])],
            "company_id": company.id, "company_ids": [(6, 0, [company.id])],
        })
        return self.env(user=user, su=False)["res.company"].with_context(
            allowed_company_ids=[company.id],
        ).with_company(company).env

    def test_config_admin_cannot_write_parameter_authority_directly(self):
        env = self._config_actor_env()
        before = env.company.sc_default_payment_terms
        for vals in ({"sc_default_payment_terms": "advance"}, {"sc_cost_from_stock": True}):
            with self.assertRaises(AccessError):
                env.company.with_context(sudo=True, parameter_change_set=True).write(vals)
        self.assertEqual(env.company.sc_default_payment_terms, before)

    def test_payment_policy_raw_identity_and_mode_mutations_are_rejected(self):
        env = self._config_actor_env()
        # Establish this actor's policy through the managed authority path;
        # installed customer/demo policies need not be visible to a non-customer actor.
        published = ProductSystemParameterPublishHandler(env).run({
            "parameter_key": "approval_mode", "proposed_value": "multi",
            "change_reason": "prepare configuration boundary policy",
        })
        self.assertTrue(published["ok"], published)
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
