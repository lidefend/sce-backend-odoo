# -*- coding: utf-8 -*-
from lxml import etree

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_core import core_extension
from odoo.addons.smart_construction_core.models.support.workflow_contract_service import (
    _simple_approval_profiles,
)

# The delivered `退回草稿` rule: `reopen` maps to `action_reset_draft`, and each of
# these models accepts that method only on a cancelled record.  The map carries the
# native form that renders the same action, so the contract declaration and the arch
# header can be compared instead of drifting apart.
RESET_TO_DRAFT_ENTRIES = {
    "sc.equipment.settlement": "view_sc_equipment_settlement_form",
    "sc.equipment.usage": "view_sc_equipment_usage_form",
    "sc.labor.settlement": "view_sc_labor_settlement_form",
    "sc.labor.usage": "view_sc_labor_usage_form",
    "sc.material.settlement": "view_sc_material_settlement_form",
    "sc.subcontract.register": "view_sc_subcontract_register_form",
    "sc.subcontract.settlement": "view_sc_subcontract_settlement_form",
}


@tagged("post_install", "-at_install", "workflow_contract_backend")
class TestWorkflowContractBackend(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create({"name": "Workflow Contract Project"})
        self.partner = self.env["res.partner"].create({"name": "Workflow Contract Partner"})
        self.tax = self.env["account.tax"].create(
            {
                "name": "Workflow Contract VAT 9%",
                "amount": 9.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "price_include": False,
                "company_id": self.env.company.id,
            }
        )
        self.contract = self.env["construction.contract"].create(
            {
                "subject": "Workflow Contract",
                "type": "in",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "tax_id": self.tax.id,
            }
        )
        self.service = self.env["sc.workflow.contract.service"]

    def test_reset_to_draft_is_declared_where_the_model_accepts_it(self):
        """`声明了必然拒绝的动作` is a control that can only fail.

        `reopen` maps to `action_reset_draft`, and every model in the map refuses
        that method outside `已取消`, so a profile that declared it in
        `已提交`/`已登记` shipped a dead button while `已取消` - the only state the
        model accepts - declared no way back at all.  The Vue form reads the
        contract and the native form renders the arch header, so both surfaces are
        compared to the model's own precondition here; the entries that can build a
        record also run the declared action in the entry test file
        (`test_the_reset_to_draft_action_is_declared_where_it_runs`).
        """
        service = self.env["sc.workflow.contract.service"]
        self.assertEqual(
            set(RESET_TO_DRAFT_ENTRIES) - set(service.PROFILE_BY_MODEL), set(),
            "every listed model must be contract-governed",
        )
        for model_name, view_xmlid in sorted(RESET_TO_DRAFT_ENTRIES.items()):
            profile = service.PROFILE_BY_MODEL[model_name]
            declared = {
                state for state, actions in profile["state_actions"].items()
                if "reopen" in actions
            }
            with self.subTest(model=model_name, surface="contract"):
                self.assertEqual(
                    declared, {"cancel"},
                    "%s may declare 退回草稿 only where the model accepts it" % model_name,
                )
                self.assertEqual(
                    profile["method_by_action"].get("reopen"), "action_reset_draft",
                    "%s must keep the delivered method identity" % model_name,
                )
            with self.subTest(model=model_name, surface="arch"):
                view = self.env.ref("smart_construction_core.%s" % view_xmlid)
                buttons = etree.fromstring(view.arch.encode("utf-8")).xpath(
                    ".//button[@name='action_reset_draft']"
                )
                self.assertEqual(len(buttons), 1, view_xmlid)
                self.assertEqual(buttons[0].get("invisible"), "state != 'cancel'", view_xmlid)

    def test_the_subcontract_register_reopens_only_from_closed(self):
        """`已关闭` -> `已登记` is a declared transition with its own identity.

        `reopen` in this platform means 重置为草稿 (`cancel` -> `draft`) and its
        label is 退回草稿, so the register's closed transition needs a different
        target state, a different method and a different label: declaring it under
        `reopen` would have shipped one wrong label in one of the two states, and
        declaring it in a state the model refuses would have shipped a button that
        can only fail - the defect the sibling test pins.  The Vue form reads this
        contract through `describe_record()`, so the declaration, the arch header
        and the model's own precondition are compared here.
        """
        service = self.env["sc.workflow.contract.service"]
        profile = service.PROFILE_BY_MODEL["sc.subcontract.register"]
        with self.subTest(surface="contract declaration"):
            self.assertIn("reactivate", service.ACTIONS)
            self.assertEqual(
                {
                    state for state, actions in profile["state_actions"].items()
                    if "reactivate" in actions
                },
                {"closed"},
                "重新打开 belongs to 已关闭 only",
            )
            self.assertEqual(profile["method_by_action"].get("reactivate"), "action_reopen")
            self.assertEqual(profile["label_by_action"].get("reactivate"), "重新打开")
            # The delivered 退回草稿 identity is untouched.
            self.assertEqual(profile["method_by_action"].get("reopen"), "action_reset_draft")
            self.assertEqual(profile["label_by_action"].get("reopen"), "退回草稿")

        view = self.env.ref("smart_construction_core.view_sc_subcontract_register_form")
        buttons = etree.fromstring(view.arch.encode("utf-8")).xpath(
            ".//button[@name='action_reopen']"
        )
        with self.subTest(surface="arch"):
            self.assertEqual(len(buttons), 1, "the 重新打开 button is declared once")
            self.assertEqual(buttons[0].get("invisible"), "state != 'closed'")
            self.assertIn("group_sc_cap_project_manager", buttons[0].get("groups") or "")

        register = self.env["sc.subcontract.register"].create(
            {
                "project_id": self.project.id,
                "subcontractor_id": self.partner.id,
                "subcontract_scope": "关闭重开范围",
                "line_ids": [(0, 0, {"work_scope": "关闭重开工作范围"})],
            }
        )
        with self.subTest(surface="runtime"):
            def keys():
                register.invalidate_recordset()
                return {
                    row["key"]: row
                    for row in service.describe_record(register)["availableActions"]
                }

            self.assertNotIn(
                "reactivate", keys(), "草稿 must not advertise 重新打开"
            )
            register.action_register()
            self.assertEqual(register.state, "active")
            self.assertNotIn(
                "reactivate", keys(), "已登记 must not advertise 重新打开"
            )
            register.action_close()
            self.assertEqual(register.state, "closed")
            closed_keys = keys()
            self.assertIn("reactivate", closed_keys, "已关闭 must declare the way back")
            self.assertNotIn(
                "reopen", closed_keys,
                "已关闭 may not advertise 退回草稿: the model refuses it outside 已取消",
            )
            self.assertTrue(closed_keys["reactivate"]["enabled"])
            self.assertEqual(closed_keys["reactivate"]["method"], "action_reopen")
            # Declared, and actually runnable on the same record.
            register.action_reopen()
            self.assertEqual(register.state, "active")

    def test_expense_claim_draft_contract_is_editable_and_submittable(self):
        claim = self.env["sc.expense.claim"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "amount": 100.0,
                "summary": "workflow-contract-smoke",
            }
        )

        contract = self.service.describe_record(claim)

        self.assertEqual(contract["rawState"], "draft")
        self.assertEqual(contract["businessPhase"], "draft")
        self.assertEqual(contract["approvalPhase"], "none")
        self.assertEqual(contract["editability"], "editable")
        self.assertIn("submit", {row["key"] for row in contract["availableActions"]})

    def test_general_contract_legacy_confirmed_phase_is_declared(self):
        """`legacy_confirmed` is a real `sc.general.contract` state.

        The profile omitted the key, so `describe_record` answered with the raw
        token through its fallback.  That fallback happens to return the same
        string here - which is exactly why the omission survived: the statusbar
        and the editability verdict were right by accident, and the next value
        added to the Selection would not be.  The declaration is asserted
        directly so the fallback cannot stand in for it again.
        """
        profile = self.service.profile_by_model()["sc.general.contract"]
        self.assertEqual(profile["state_phase"].get("legacy_confirmed"), "legacy_confirmed")

        contract_record = self.env["sc.general.contract"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_name": "Workflow Contract Legacy Confirmed",
                "contract_type": "材料采购",
                "amount_total": 100.0,
                "state": "legacy_confirmed",
            }
        )
        contract = self.service.describe_record(contract_record)

        self.assertEqual(contract["rawState"], "legacy_confirmed")
        self.assertEqual(contract["businessPhase"], "legacy_confirmed")
        self.assertEqual(contract["editability"], "locked")
        self.assertEqual(contract["availableActions"], [])
        self.assertIn(
            {"value": "legacy_confirmed", "label": "历史确认"},
            contract["statusbar"]["states"],
        )

    def test_general_contract_signed_declares_no_transition(self):
        """A signed 一般合同（公司）must not advertise a transition it refuses.

        The profile published `cancel` on `signed`, but `action_cancel` accepts
        only `draft` / `confirmed` and
        `test_p0_state_closure.test_general_contract_blocks_invalid_anchor_or_terminal_cancel`
        locks that refusal, so the declared button's only outcome was a
        UserError. The terminal record is materialised the same way its
        `legacy_confirmed` sibling is, so the declaration is compared with the
        model's own precondition on one record and the check does not depend on
        whether the deployment carries an approval policy for the model; the P0
        test already owns proving the declared ladder reaches `signed`.
        """
        contract_record = self.env["sc.general.contract"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_name": "Workflow Contract Signed",
                "contract_type": "材料采购",
                "amount_total": 100.0,
                "state": "signed",
            }
        )
        self.assertEqual(contract_record.state, "signed")

        contract = self.service.describe_record(contract_record)

        self.assertEqual(contract["rawState"], "signed")
        self.assertEqual(contract["businessPhase"], "effective")
        self.assertEqual(
            contract["availableActions"], [],
            "signed must declare no transition: action_cancel refuses it",
        )
        # Declared-absent and actually-refused describe the same product truth.
        with self.assertRaises(UserError):
            contract_record.action_cancel()

    def test_the_shared_approval_family_declares_only_reachable_states(self):
        """The shared approval template must not carry states its members lack.

        The template shipped `submit`/`rejected` next to `submitted`.  No member's
        Selection can produce either token and none of them inherits
        `tier.validation`, so `describe_record`'s phase lookup never read those
        keys: pure copy residue that the dead-entry registry had to carry for ten
        models, which is how a registration set stops being informative.

        It also declared `reopen` in 已提交, where `action_reset_draft` refuses on
        eight of the ten members - a button whose only outcome is a UserError -
        while 已取消, the state the model accepts, published no way back at all.
        The member list is read from the helper itself so this check cannot be
        narrowed by editing a hand-written map.
        """
        template = _simple_approval_profiles(("probe.model",))["probe.model"]
        self.assertTrue(template, "the helper must return its profile for a probed model")

        profiles = self.service.profile_by_model()
        family = sorted(
            model for model, profile in profiles.items()
            if profile.get("state_actions") == template["state_actions"]
            and profile.get("state_phase") == template["state_phase"]
        )
        self.assertEqual(
            family,
            [
                "sc.equipment.plan",
                "sc.equipment.request",
                "sc.labor.plan",
                "sc.labor.request",
                "sc.material.purchase.request",
                "sc.material.rental.plan",
                "sc.safety.disclosure",
                "sc.safety.plan",
                "sc.subcontract.plan",
                "sc.subcontract.request",
            ],
        )

        self.assertEqual(
            sorted(template["state_phase"]), ["approved", "cancel", "draft", "submitted"],
            "the template must map exactly the states its members can hold",
        )
        for model_name in family:
            profile = profiles[model_name]
            with self.subTest(model=model_name):
                self.assertEqual(
                    sorted(profile["state_phase"]), ["approved", "cancel", "draft", "submitted"],
                )
                declared = {
                    state for state, actions in profile["state_actions"].items()
                    if "reopen" in actions
                }
                self.assertEqual(
                    declared, {"cancel"},
                    "%s may offer 退回草稿 only from 已取消, the state it accepts" % model_name,
                )
                self.assertEqual(profile["method_by_action"].get("reopen"), "action_reset_draft")
                selection = dict(
                    self.env[model_name].fields_get(["state"])["state"]["selection"]
                )
                self.assertEqual(
                    sorted(selection), ["approved", "cancel", "draft", "submitted"],
                    "%s declares phases for states its Selection does not hold" % model_name,
                )

        # The native header carried the same defect: eight of the ten forms
        # rendered 退回草稿 in 已提交, where `action_reset_draft` refuses, and hid
        # it in 已取消, the state it accepts.  The forms are read from the model,
        # so a new form cannot reintroduce the dead control unnoticed.  A form
        # without the button is left alone: the contract may be ahead of the
        # native header, it may never offer a control the model rejects.
        for model_name in family:
            forms = self.env["ir.ui.view"].search(
                [("model", "=", model_name), ("type", "=", "form")]
            )
            self.assertTrue(forms, "%s must have a form view" % model_name)
            gates = set()
            for view in forms:
                buttons = etree.fromstring(view.arch.encode("utf-8")).xpath(
                    ".//button[@name='action_reset_draft']"
                )
                gates |= {button.get("invisible") for button in buttons}
            with self.subTest(model=model_name, surface="arch"):
                self.assertLessEqual(
                    gates, {"state != 'cancel'"},
                    "%s renders 退回草稿 outside 已取消: %s" % (model_name, sorted(gates)),
                )

    def test_profile_methods_resolve_to_existing_model_methods(self):
        profiles = self.service.PROFILE_BY_MODEL
        self.assertTrue(profiles)
        for model_name, profile in profiles.items():
            self.assertIn(model_name, self.env.registry)
            model = self.env[model_name]
            for action_key in set(profile.get("method_by_action", {})):
                method_name = profile.get("method_by_action", {}).get(action_key)
                if not method_name:
                    continue
                self.assertTrue(
                    hasattr(model, method_name),
                    "%s workflow action %s points to missing method %s" % (model_name, action_key, method_name),
                )

    def test_industry_layer_owns_no_profile_for_a_foreign_model(self):
        """A user/product module publishes its own workflow projection.

        `sc.partner.import.review` is owned by a customer module, so the
        industry layer must not declare its states, actions or methods.  The
        owning module registers the profile through the P0 registry and this
        service merges it; a model that is absent from the current registry
        keeps its actions undeclared instead of being back-filled here.
        """
        service = self.env["sc.workflow.contract.service"]
        industry_models = set(service.PROFILE_BY_MODEL)
        external = service._external_profile_by_model()
        self.assertTrue(
            industry_models.isdisjoint(set(external)),
            "the industry layer must not declare a profile for a foreign model",
        )
        effective = service.profile_by_model()
        self.assertTrue(industry_models.issubset(set(effective)))
        for model_name in sorted(external):
            with self.subTest(model=model_name):
                if model_name in self.env.registry:
                    self.assertIn(model_name, effective)
                else:
                    self.assertNotIn(model_name, effective)
                    self.assertFalse(service.is_model_supported(model_name))

    def test_an_external_profile_whose_methods_do_not_resolve_stays_undeclared(self):
        """Registration alone must not publish an action the model cannot run."""
        from odoo.addons.smart_core.utils import contract_governance
        from odoo.addons.smart_core.utils import contract_governance_registry

        registered = contract_governance.register_workflow_contract_profile(
            "res.partner",
            {
                "state_field": "state",
                "state_phase": {"draft": "draft"},
                "state_actions": {"draft": ["submit"]},
                "method_by_action": {"submit": "action_that_does_not_exist"},
            },
            source="unit.test",
        )
        self.assertTrue(registered)
        try:
            service = self.env["sc.workflow.contract.service"]
            self.assertNotIn("res.partner", service.profile_by_model())
            self.assertFalse(service.is_model_supported("res.partner"))
        finally:
            contract_governance_registry._WORKFLOW_CONTRACT_PROFILE_REGISTRY.pop("res.partner", None)
            contract_governance_registry._WORKFLOW_CONTRACT_PROFILE_SOURCES.pop("res.partner", None)

    def test_supported_model_contract_schema_is_frontend_stable(self):
        expense_contract_wrapper = self.env["construction.contract.expense"].search(
            [("contract_id", "=", self.contract.id)],
            limit=1,
        )
        if not expense_contract_wrapper:
            expense_contract_wrapper = self.env["construction.contract.expense"].create({"contract_id": self.contract.id})
        income_contract = self.env["construction.contract"].create(
            {
                "subject": "Workflow Income Contract",
                "type": "out",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "tax_id": self.tax.id,
            }
        )
        income_contract_wrapper = self.env["construction.contract.income"].search(
            [("contract_id", "=", income_contract.id)],
            limit=1,
        )
        if not income_contract_wrapper:
            income_contract_wrapper = self.env["construction.contract.income"].create({"contract_id": income_contract.id})
        records = [
            self.env["payment.request"].create(
                {
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "amount": 10.0,
                }
            ),
            self.env["sc.settlement.order"].create(
                {
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                }
            ),
            self.env["sc.expense.claim"].create(
                {
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "amount": 10.0,
                    "summary": "workflow-contract-schema",
                }
            ),
            self.contract,
            expense_contract_wrapper,
            income_contract_wrapper,
            self.env["sc.payment.execution"].create(
                {
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "contract_id": self.contract.id,
                    "paid_amount": 10.0,
                    "payment_account_no": "payer-schema",
                    "receipt_account_no": "payee-schema",
                }
            ),
            self.env["sc.receipt.income"].create(
                {
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "contract_id": self.contract.id,
                    "amount": 10.0,
                    "receiving_account_no": "receiver-schema",
                }
            ),
            self.env["sc.invoice.registration"].create(
                {
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "contract_id": self.contract.id,
                    "amount_total": 10.0,
                }
            ),
            self.env["sc.self.funding.registration"].create(
                {
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "amount": 10.0,
                    "payment_account_name": "Company Account",
                    "partner_account_name": "Contractor Account",
                }
            ),
            self.env["sc.financing.loan"].create(
                {
                    "project_id": self.project.id,
                    "amount": 10.0,
                }
            ),
            self.env["sc.treasury.reconciliation"].create(
                {
                    "project_id": self.project.id,
                    "system_difference": 0.0,
                }
            ),
            self.env["sc.general.contract"].create(
                {
                    "project_id": self.project.id,
                    "partner_id": self.partner.id,
                    "contract_name": "Workflow General Contract",
                    "amount_total": 10.0,
                }
            ),
            self.env["sc.settlement.adjustment"].create(
                {
                    "project_id": self.project.id,
                    "contract_id": self.contract.id,
                    "partner_id": self.partner.id,
                    "item_name": "workflow adjustment",
                    "amount": 10.0,
                }
            ),
        ]

        self.assertTrue(
            {record._name for record in records}.issubset(set(self.service.PROFILE_BY_MODEL)),
        )
        for record in records:
            contract = self.service.describe_record(record)
            self._assert_workflow_contract_schema(contract, record)

    def test_deduction_bill_missing_lines_disables_submit(self):
        category = self.env["sc.business.category"].search([("code", "=", "finance.deduction.bill")], limit=1)
        self.assertTrue(category, "扣款单业务分类应已初始化。")
        claim = self.env["sc.expense.claim"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "business_category_id": category.id,
                "expense_type": "扣款单",
                "amount": 100.0,
                "summary": "workflow-deduction-gate",
            }
        )

        contract = self.service.describe_record(claim)
        submit = self._action(contract, "submit")

        self.assertIn("DEDUCTION_BILL_MISSING_LINES", {row["reasonCode"] for row in contract["evidenceGate"]})
        self.assertFalse(submit["enabled"])
        self.assertEqual(submit["reason_code"], "DEDUCTION_BILL_MISSING_LINES")

    def test_settlement_submit_contract_separates_business_and_approval_phase(self):
        settlement = self.env["sc.settlement.order"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
            }
        )
        settlement._write_lifecycle("submit")

        contract = self.service.describe_record(settlement)

        self.assertEqual(contract["rawState"], "submit")
        self.assertEqual(contract["businessPhase"], "under_review")
        self.assertIn(contract["approvalPhase"], {"waiting", "pending", "approved", "none"})
        self.assertEqual(contract["editability"], "readonly")

    def test_settlement_missing_lines_disables_submit(self):
        settlement = self.env["sc.settlement.order"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
            }
        )

        contract = self.service.describe_record(settlement)
        submit = self._action(contract, "submit")

        self.assertIn("SETTLEMENT_MISSING_LINES", {row["reasonCode"] for row in contract["evidenceGate"]})
        self.assertFalse(submit["enabled"])
        self.assertEqual(submit["reason_code"], "SETTLEMENT_MISSING_LINES")

    def test_settlement_invalid_line_gate_matches_backend_submit_guard(self):
        settlement = self.env["sc.settlement.order"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.contract.id,
                "line_ids": [
                    (0, 0, {"name": "valid-line", "contract_id": self.contract.id, "qty": 1.0, "price_unit": 100.0}),
                    (0, 0, {"name": "invalid-line", "contract_id": self.contract.id, "qty": 0.0, "price_unit": 1.0}),
                ],
            }
        )

        contract = self.service.describe_record(settlement)
        submit = self._action(contract, "submit")

        self.assertIn("SETTLEMENT_INVALID_LINE_QTY", {row["reasonCode"] for row in contract["evidenceGate"]})
        self.assertFalse(submit["enabled"])
        with self.assertRaises(UserError):
            settlement.action_submit()

    def test_payment_missing_basis_disables_submit(self):
        payment = self.env["payment.request"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "amount": 10.0,
            }
        )

        contract = self.service.describe_record(payment)
        submit = self._action(contract, "submit")

        self.assertIn("PAYMENT_MISSING_BASIS", {row["reasonCode"] for row in contract["evidenceGate"]})
        self.assertFalse(submit["enabled"])
        self.assertEqual(submit["reason_code"], "PAYMENT_MISSING_BASIS")

    def test_payment_done_contract_is_locked(self):
        payment = self.env["payment.request"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "amount": 10.0,
                "state": "done",
            }
        )

        contract = self.service.describe_record(payment)

        self.assertEqual(contract["businessPhase"], "done")
        self.assertEqual(contract["editability"], "locked")
        self.assertEqual(contract["availableActions"], [])

    def test_payment_rejected_contract_is_editable_for_correction(self):
        payment = self.env["payment.request"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "amount": 10.0,
                "state": "rejected",
                "reject_reason": "请修正付款依据",
            }
        )

        contract = self.service.describe_record(payment)

        self.assertEqual(contract["businessPhase"], "rejected")
        self.assertEqual(contract["editability"], "editable")
        self.assertIn("submit", {row["key"] for row in contract["availableActions"]})

    def test_workflow_editability_never_elevates_readonly_page_authority(self):
        payment = self.env["payment.request"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "amount": 10.0,
                "state": "rejected",
                "reject_reason": "只读调用者仍不可编辑",
            }
        )
        source_contract = {
            "model": "payment.request",
            "view_type": "form",
            "record_id": payment.id,
        }
        base_contract = {
            "statusContract": {"globalStatus": {"pageAuth": "read"}},
            "runtimeContract": {},
        }

        projected = core_extension.smart_core_finalize_unified_page_contract_v2(
            self.env,
            base_contract,
            {"source_contract": source_contract, "view_type": "form"},
        )

        self.assertEqual(projected["workflowContract"]["editability"], "editable")
        self.assertEqual(projected["statusContract"]["globalStatus"]["pageAuth"], "read")

    def test_workflow_readonly_narrows_effective_form_surface(self):
        payment = self.env["payment.request"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "amount": 10.0,
            }
        )
        payment.with_context(allow_transition=True).write({"state": "approved"})
        projected = core_extension.smart_core_finalize_unified_page_contract_v2(
            self.env,
            {
                "statusContract": {
                    "globalStatus": {
                        "pageAuth": "edit",
                        "effectiveRecordCapabilities": {"read": True, "write": True},
                        "effectiveRenderProfile": "edit",
                    }
                },
                "runtimeContract": {},
            },
            {
                "source_contract": {
                    "model": "payment.request",
                    "view_type": "form",
                    "record_id": payment.id,
                },
                "view_type": "form",
            },
        )
        global_status = projected["statusContract"]["globalStatus"]
        self.assertEqual(projected["workflowContract"]["editability"], "readonly")
        self.assertEqual(global_status["pageAuth"], "read")
        self.assertFalse(global_status["effectiveRecordCapabilities"]["write"])
        self.assertEqual(global_status["effectiveRenderProfile"], "readonly")

    def test_workflow_rejected_editability_preserves_existing_edit_authority(self):
        payment = self.env["payment.request"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "amount": 10.0,
                "state": "rejected",
                "reject_reason": "允许有能力经办人修正",
            }
        )
        source_contract = {
            "model": "payment.request",
            "view_type": "form",
            "record_id": payment.id,
        }
        base_contract = {
            "statusContract": {"globalStatus": {"pageAuth": "edit"}},
            "runtimeContract": {},
        }

        projected = core_extension.smart_core_finalize_unified_page_contract_v2(
            self.env,
            base_contract,
            {"source_contract": source_contract, "view_type": "form"},
        )

        self.assertEqual(projected["workflowContract"]["editability"], "editable")
        self.assertEqual(projected["statusContract"]["globalStatus"]["pageAuth"], "edit")

    def test_construction_contract_approval_in_progress_disables_duplicate_submit(self):
        self.env.cr.execute(
            "UPDATE construction_contract SET validation_status=%s WHERE id=%s",
            ("waiting", self.contract.id),
        )
        self.contract.invalidate_recordset()

        contract = self.service.describe_record(self.contract)
        submit = self._action(contract, "submit")

        self.assertEqual(contract["rawState"], "draft")
        self.assertEqual(contract["businessPhase"], "draft")
        self.assertIn(contract["approvalPhase"], {"waiting", "pending"})
        self.assertIn("CONTRACT_APPROVAL_IN_PROGRESS", {row["reasonCode"] for row in contract["evidenceGate"]})
        self.assertFalse(submit["enabled"])

    def test_construction_contract_missing_lines_disables_complete_and_backend_blocks_close(self):
        self.env.cr.execute(
            "UPDATE construction_contract SET state=%s, validation_status=%s WHERE id=%s",
            ("confirmed", "validated", self.contract.id),
        )
        self.contract.invalidate_recordset()

        contract = self.service.describe_record(self.contract)
        complete = self._action(contract, "complete")

        self.assertEqual(contract["rawState"], "confirmed")
        self.assertEqual(contract["businessPhase"], "approved")
        self.assertIn("CONTRACT_MISSING_LINES_FOR_CLOSE", {row["reasonCode"] for row in contract["evidenceGate"]})
        self.assertFalse(complete["enabled"])
        with self.assertRaises(UserError):
            self.contract.action_close()

    def test_construction_contract_cancel_does_not_depend_on_user_email(self):
        user = self.env["res.users"].create(
            {
                "name": "Workflow Contract User Without Email",
                "login": "workflow_contract_no_email",
                "groups_id": [
                    (6, 0, [
                        self.env.ref("base.group_user").id,
                        self.env.ref("smart_construction_core.group_sc_cap_contract_user").id,
                        self.env.ref("smart_construction_core.group_sc_cap_finance_read").id,
                    ])
                ],
            }
        )
        self.assertFalse(user.email)

        self.contract.with_user(user).action_cancel()

        self.assertEqual(self.contract.state, "cancel")

    def test_payment_execution_missing_request_disables_submit_and_backend_blocks_confirm(self):
        execution = self.env["sc.payment.execution"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.contract.id,
                "paid_amount": 100.0,
                "payment_account_no": "payer-001",
                "receipt_account_no": "payee-001",
            }
        )

        contract = self.service.describe_record(execution)
        submit = self._action(contract, "submit")

        self.assertEqual(contract["rawState"], "draft")
        self.assertEqual(contract["businessPhase"], "draft")
        self.assertIn("PAYMENT_EXECUTION_MISSING_REQUEST", {row["reasonCode"] for row in contract["evidenceGate"]})
        self.assertFalse(submit["enabled"])
        with self.assertRaises(UserError):
            execution.action_confirm()

    def test_paid_payment_execution_keeps_field_scoped_reversal_editability(self):
        execution = self.env["sc.payment.execution"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.contract.id,
                "paid_amount": 100.0,
                "payment_account_no": "payer-001",
                "receipt_account_no": "payee-001",
                "state": "paid",
            }
        )

        contract = self.service.describe_record(execution)

        self.assertEqual(contract["businessPhase"], "done")
        self.assertEqual(contract["editability"], "editable")
        self.assertIn("cancel", {row["key"] for row in contract["availableActions"]})

    def test_receipt_income_missing_request_disables_submit_and_backend_blocks_confirm(self):
        receipt = self.env["sc.receipt.income"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.contract.id,
                "amount": 100.0,
                "receiving_account_no": "receive-001",
            }
        )

        contract = self.service.describe_record(receipt)
        submit = self._action(contract, "submit")

        self.assertEqual(contract["rawState"], "draft")
        self.assertEqual(contract["businessPhase"], "draft")
        self.assertIn("RECEIPT_INCOME_MISSING_REQUEST", {row["reasonCode"] for row in contract["evidenceGate"]})
        self.assertFalse(submit["enabled"])
        with self.assertRaises(UserError):
            receipt.action_confirm()

    def test_invoice_registration_missing_invoice_no_disables_submit_and_backend_blocks_confirm(self):
        invoice = self.env["sc.invoice.registration"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.contract.id,
                "amount_total": 100.0,
            }
        )

        contract = self.service.describe_record(invoice)
        submit = self._action(contract, "submit")

        self.assertEqual(contract["rawState"], "draft")
        self.assertEqual(contract["businessPhase"], "draft")
        self.assertIn("INVOICE_REGISTRATION_MISSING_INVOICE_NO", {row["reasonCode"] for row in contract["evidenceGate"]})
        self.assertFalse(submit["enabled"])
        with self.assertRaises(UserError):
            invoice.action_confirm()

    def test_self_funding_missing_attachment_disables_submit_and_backend_blocks_confirm(self):
        funding = self.env["sc.self.funding.registration"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "amount": 100.0,
                "payment_account_name": "Company Account",
                "partner_account_name": "Contractor Account",
            }
        )

        contract = self.service.describe_record(funding)
        submit = self._action(contract, "submit")

        self.assertEqual(contract["rawState"], "draft")
        self.assertEqual(contract["businessPhase"], "draft")
        self.assertIn("SELF_FUNDING_ATTACHMENT_REQUIRED", {row["reasonCode"] for row in contract["evidenceGate"]})
        self.assertFalse(submit["enabled"])
        with self.assertRaises(UserError):
            funding.action_confirm()

    def test_financing_loan_missing_partner_disables_submit_and_backend_blocks_confirm(self):
        loan = self.env["sc.financing.loan"].create(
            {
                "project_id": self.project.id,
                "amount": 100.0,
            }
        )

        contract = self.service.describe_record(loan)
        submit = self._action(contract, "submit")

        self.assertEqual(contract["rawState"], "draft")
        self.assertEqual(contract["businessPhase"], "draft")
        self.assertIn("FINANCING_LOAN_MISSING_PARTNER", {row["reasonCode"] for row in contract["evidenceGate"]})
        self.assertFalse(submit["enabled"])
        with self.assertRaises(UserError):
            loan.action_confirm()

    def test_treasury_reconciliation_missing_ledger_disables_submit_and_backend_blocks_confirm(self):
        reconciliation = self.env["sc.treasury.reconciliation"].create(
            {
                "project_id": self.project.id,
                "system_difference": 0.0,
            }
        )

        contract = self.service.describe_record(reconciliation)
        submit = self._action(contract, "submit")

        self.assertEqual(contract["rawState"], "draft")
        self.assertEqual(contract["businessPhase"], "draft")
        self.assertIn("TREASURY_RECONCILIATION_MISSING_LEDGER", {row["reasonCode"] for row in contract["evidenceGate"]})
        self.assertFalse(submit["enabled"])
        with self.assertRaises(UserError):
            reconciliation.action_confirm()

    def test_v2_extension_hook_injects_workflow_contract_for_existing_form(self):
        claim = self.env["sc.expense.claim"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "amount": 50.0,
                "summary": "workflow-hook-smoke",
            }
        )
        source_contract = {
            "model": "sc.expense.claim",
            "view_type": "form",
            "record_id": claim.id,
        }
        base_contract = {
            "statusContract": {"globalStatus": {"pageAuth": "read"}},
            "runtimeContract": {},
        }

        projected = core_extension.smart_core_finalize_unified_page_contract_v2(
            self.env,
            base_contract,
            {"source_contract": source_contract, "view_type": "form"},
        )

        self.assertIsInstance(projected, dict)
        self.assertEqual(projected["workflowContract"]["model"], "sc.expense.claim")
        self.assertEqual(projected["workflowContract"]["businessPhase"], "draft")
        self.assertEqual(projected["workflowContract"]["rawState"], "draft")
        self.assertNotIn("workflowContract", projected["runtimeContract"])
        self.assertEqual(projected["statusContract"]["globalStatus"]["workflowPhase"], "draft")

    def _action(self, contract, key):
        for row in contract["availableActions"]:
            if row["key"] == key:
                return row
        self.fail("missing workflow action: %s" % key)

    def _assert_workflow_contract_schema(self, contract, record):
        self.assertEqual(contract["source"]["kind"], "sc_backend_workflow_contract")
        self.assertEqual(contract["model"], record._name)
        self.assertEqual(contract["record_id"], record.id)
        self.assertEqual(contract["stateField"], self.service.PROFILE_BY_MODEL[record._name]["state_field"])
        self.assertIsInstance(contract["rawState"], str)
        self.assertTrue(contract["businessPhase"])
        self.assertTrue(contract["approvalPhase"])
        self.assertIn(contract["editability"], {"editable", "readonly", "locked"})
        self.assertIsInstance(contract["statusbar"], dict)
        self.assertEqual(contract["statusbar"]["field"], "__workflow_phase")
        self.assertTrue(contract["statusbar"]["current"])
        self.assertTrue(contract["statusbar"]["readonly"])
        self.assertTrue(contract["statusbar"]["states"])
        self.assertIn(contract["statusbar"]["current"], {row["value"] for row in contract["statusbar"]["states"]})
        self.assertIsInstance(contract["evidenceGate"], list)
        self.assertIsInstance(contract["availableActions"], list)
        for gate in contract["evidenceGate"]:
            self.assertTrue(gate["reasonCode"])
            self.assertTrue(gate["message"])
            self.assertIsInstance(gate["actionKeys"], list)
            self.assertIn(gate["severity"], {"block", "warn", "info"})
        for action in contract["availableActions"]:
            self.assertTrue(action["key"])
            self.assertTrue(action["label"])
            self.assertIn(action["intent"], {"data.write", "server.object"})
            self.assertIn(action["kind"], {"save", "transition", "approval"})
            self.assertIn(action["enabled"], {True, False})
            self.assertEqual(action["target"]["model"], record._name)
            self.assertEqual(action["target"]["id"], record.id)
            self.assertEqual(action["target"]["method"], action["method"])
            if action["enabled"]:
                self.assertEqual(action["reason_code"], "")
                self.assertEqual(action["blocked_message"], "")
            else:
                self.assertTrue(action["reason_code"])
                self.assertTrue(action["blocked_message"])
