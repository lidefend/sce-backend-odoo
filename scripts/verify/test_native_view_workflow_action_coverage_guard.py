#!/usr/bin/env python3
"""Pin the native-button coverage guard to a two-way, fail-closed registry.

An uncovered native object button must be registered; a registration that has
outlived its gap (method declared, button gone) or that carries no meaningful
class/reason must not pass.  Each case below is a regression the guard exists
to catch, so the registry cannot quietly rot into a rubber stamp.
"""
from __future__ import annotations

import ast
import copy
import json
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path

from native_view_workflow_action_coverage_guard import REGISTRY, adopted_models, validate
from workflow_contract_profile_loader import DEFAULT_SERVICE, load_profiles


def _baseline() -> dict:
    return json.loads(Path(REGISTRY).read_text(encoding="utf-8"))


class NativeViewActionCoverageGuardTest(unittest.TestCase):
    def _assert_material_state_projection(self, class_name, model, method_name):
        # Compare the real projection against the business method's state guard,
        # so changes to business authority cannot leave copied expectations green.
        path = DEFAULT_SERVICE.parents[1] / "core/material_acceptance.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        owner = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
        method = next(n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name == method_name)
        guard = next(n for n in ast.walk(method) if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "_sc_require_state")
        allowed = ast.literal_eval(guard.args[0])
        profile = load_profiles()[model]
        for state in list(profile["state_phase"]) + ["unknown"]:
            with self.subTest(model=model, method=method_name, state=state):
                projected = self._general_contract_actions(state, model=model)
                self.assertEqual(method_name in [a["method"] for a in projected], state in allowed)

    def test_purchase_request_actions_follow_review_facts_and_business_sources(self):
        model = 'sc.material.purchase.request'
        for method in ('action_cancel', 'action_reset_draft'):
            self._assert_material_state_projection('ScMaterialPurchaseRequest', model, method)
        historical = self._general_contract_actions('submitted', model=model, record_fields={'validation_status': 'no'})
        self.assertEqual({row['method'] for row in historical}, {'action_submit', 'action_cancel'})
        for reviewer in (False, True):
            rows = self._general_contract_actions('submitted', model=model, approval_phase='pending', can_review=reviewer, record_fields={'validation_status': 'pending'})
            expected = {'action_cancel'} | ({'validate_tier', 'reject_tier'} if reviewer else set())
            self.assertEqual({row['method'] for row in rows}, expected)
            for row in rows:
                self.assertEqual(row['target']['model'], model)
                self.assertEqual(row['target']['method'], row['method'])
        self.assertEqual(self._general_contract_actions('approved', model=model), [])

    def test_material_inbound_reset_matches_business_sources(self):
        self._assert_material_state_projection("ScMaterialInbound", "sc.material.inbound", "action_reset_draft")

    def test_material_inbound_cancel_matches_business_sources(self):
        self._assert_material_state_projection("ScMaterialInbound", "sc.material.inbound", "action_cancel")

    def test_material_acceptance_reset_matches_business_sources(self):
        self._assert_material_state_projection("ScMaterialAcceptance", "sc.material.acceptance", "action_reset_draft")

    def test_acceptance_quality_actions_are_separate_from_tier_decisions(self):
        rows = self._general_contract_actions('approved', model='sc.material.acceptance')
        by_method = {row['method']: row for row in rows}
        for method in ('action_accept', 'action_reject'):
            self.assertEqual(by_method[method]['action_semantics']['purpose'], 'complete')
        self.assertNotIn('validate_tier', by_method)
        self.assertNotIn('reject_tier', by_method)
        pending = self._general_contract_actions('submitted', model='sc.material.acceptance', approval_phase='pending', can_review=True, record_fields={'validation_status': 'pending'})
        self.assertEqual({row['method'] for row in pending}, {'validate_tier', 'reject_tier', 'action_cancel'})

    def test_material_acceptance_cancel_matches_business_sources(self):
        self._assert_material_state_projection("ScMaterialAcceptance", "sc.material.acceptance", "action_cancel")

    def test_unavailable_actions_keep_meaning_without_becoming_execution_grants(self):
        tree = ast.parse(DEFAULT_SERVICE.read_text(encoding="utf-8"))
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_declared_actions")
        method.decorator_list = []
        assignment = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "ACTIONS" for t in n.targets))
        namespace = {}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[assignment, method], type_ignores=[])), str(DEFAULT_SERVICE), "exec"), namespace)
        service = SimpleNamespace(ACTIONS=namespace["ACTIONS"])
        profile = load_profiles()["project.project"]
        declarations = namespace["_declared_actions"](service, profile)
        meanings = {row["method"]: row["action_semantics"]["purpose"] for row in declarations}
        self.assertEqual(meanings["action_sc_start"], "start_execution")
        self.assertEqual(meanings["validate_tier"], "approve")
        self.assertEqual(meanings["reject_tier"], "reject")
        self.assertTrue(all("enabled" not in row and "target" not in row for row in declarations))
        available = self._general_contract_actions("draft", model="project.project", record_fields={"sc_approval_state": "draft", "validation_status": "no"})
        self.assertNotIn("action_sc_start", [row["method"] for row in available])
        self.assertNotIn("validate_tier", [row["method"] for row in available])
        self.assertEqual(namespace["_declared_actions"](service, {"method_by_action": {"undeclared": "action_guess"}}), [])

    def _general_contract_actions(self, state, *, approval_phase="none", can_review=False, model="sc.general.contract", record_fields=None):
        # Execute the shipped projection method, not a duplicate of its algorithm.
        tree = ast.parse(DEFAULT_SERVICE.read_text(encoding="utf-8"))
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_available_actions")
        method.decorator_list = []
        assignment = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "ACTIONS" for t in n.targets))
        namespace = {}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[assignment, method], type_ignores=[])), str(DEFAULT_SERVICE), "exec"), namespace)
        values = dict(record_fields or {})
        def matches(domain):
            return all(values.get(field) == value if operator == '=' else values.get(field) not in value
                       for field, operator, value in domain)
        record = SimpleNamespace(_name=model, id=23, can_review=can_review, filtered_domain=matches)
        service = SimpleNamespace(ACTIONS=namespace["ACTIONS"])
        return namespace["_available_actions"](service, record, load_profiles()[record._name], state, "", approval_phase, [])

    def test_general_contract_signing_binds_the_existing_business_method(self):
        for state in ("draft", "confirmed"):
            with self.subTest(state=state):
                action = next(a for a in self._general_contract_actions(state) if a["key"] == "complete")
                self.assertEqual(action["method"], "action_signed")
                self.assertEqual(action["label"], "已签署")
                self.assertEqual(action["target"], {"model": "sc.general.contract", "id": 23, "method": "action_signed"})
                self.assertEqual(action["action_semantics"]["executor"], "contract.action")
                self.assertEqual(action["action_semantics"]["purpose"], "complete")

    def test_general_contract_signing_is_not_declared_in_terminal_or_unknown_states(self):
        for state in ("signed", "cancel", "legacy_confirmed", "unknown"):
            with self.subTest(state=state):
                self.assertNotIn("action_signed", [a["method"] for a in self._general_contract_actions(state)])

    def test_signing_does_not_replace_approval_or_grant_reviewer_actions(self):
        actions = self._general_contract_actions("draft", approval_phase="pending", can_review=False)
        self.assertIn("action_confirm", [a["method"] for a in actions])
        self.assertIn("action_signed", [a["method"] for a in actions])
        self.assertNotIn("validate_tier", [a["method"] for a in actions])
        self.assertNotIn("reject_tier", [a["method"] for a in actions])
        reviewer = self._general_contract_actions("draft", approval_phase="pending", can_review=True)
        self.assertIn("validate_tier", [a["method"] for a in reviewer])

    def _sign_record(self, state, *, approval_completes=True, anchor_valid=True):
        path = DEFAULT_SERVICE.parents[1] / "core/general_contract.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "action_signed")
        namespace = {"UserError": ValueError, "_": lambda text: text}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(path), "exec"), namespace)
        record = SimpleNamespace(state=state, approval_calls=0)
        def confirm():
            record.approval_calls += 1
            if approval_completes:
                record.state = "confirmed"
        def check_anchor():
            if not anchor_valid:
                raise ValueError("missing business anchor")
        record.action_confirm = confirm
        record._check_business_anchor = check_anchor
        return record, lambda: namespace["action_signed"]([record])

    def test_signing_executes_the_existing_confirmation_before_draft_transition(self):
        record, execute = self._sign_record("draft")
        execute()
        self.assertEqual(record.approval_calls, 1)
        self.assertEqual(record.state, "signed")

    def test_pending_approval_does_not_become_signed(self):
        record, execute = self._sign_record("draft", approval_completes=False)
        execute()
        self.assertEqual(record.approval_calls, 1)
        self.assertEqual(record.state, "draft")

    def test_signing_preserves_business_anchor_validation(self):
        record, execute = self._sign_record("confirmed", anchor_valid=False)
        with self.assertRaises(ValueError):
            execute()
        self.assertEqual(record.state, "confirmed")

    def test_signing_rejects_states_outside_the_declared_sources(self):
        for state in ("signed", "cancel", "legacy_confirmed"):
            record, execute = self._sign_record(state)
            with self.assertRaises(ValueError):
                execute()
            self.assertEqual(record.state, state)

    def test_plan_start_is_published_only_after_confirmation(self):
        for state in ("draft", "confirmed", "in_progress", "done", "cancel"):
            actions = self._general_contract_actions(state, model="sc.plan")
            starts = [a for a in actions if a["method"] == "action_start"]
            self.assertEqual(bool(starts), state == "confirmed")
            if starts:
                self.assertEqual(starts[0]["action_semantics"]["purpose"], "start_execution")

    def test_plan_completion_and_reopening_follow_model_preconditions(self):
        for state in ("draft", "confirmed", "in_progress", "done", "cancel"):
            methods = [a["method"] for a in self._general_contract_actions(state, model="sc.plan")]
            self.assertEqual("action_done" in methods, state == "in_progress")
            self.assertEqual("action_reset_draft" in methods, state == "cancel")

    def test_document_reset_is_declared_for_existing_non_draft_states(self):
        for state in ("draft", "review", "done", "cancel", "unknown"):
            actions = self._general_contract_actions(state, model="sc.project.document")
            resets = [a for a in actions if a["method"] == "action_reset_to_draft"]
            self.assertEqual(bool(resets), state in ("review", "done", "cancel"))
            if resets:
                self.assertEqual(resets[0]["action_semantics"]["purpose"], "reopen")

    def test_plan_fix_does_not_add_start_to_other_shared_profile_consumers(self):
        profile = load_profiles()["sc.fund.account.operation"]
        self.assertNotIn("action_start", profile["method_by_action"].values())

    def test_same_named_method_on_another_model_does_not_cover_a_button(self):
        with patch("native_view_workflow_action_coverage_guard.adopted_models", return_value={"first", "second"}), patch(
            "native_view_workflow_action_coverage_guard.declared_methods", return_value={("first", "action_approve")}
        ), patch("native_view_workflow_action_coverage_guard.native_object_buttons", return_value={("second", "action_approve"): 1}):
            errors = validate({"entries": []})
            self.assertEqual(len(errors), 1)
            self.assertIn("second: native button 'action_approve'", errors[0])
            self.assertEqual(validate({"entries": [{"model": "second", "method": "action_approve", "class": "state_transition_undeclared", "reason": "Unresolved approval integration"}]}), [])

    def test_expense_and_settlement_native_approval_match_contract_without_second_confirmation(self):
        root = DEFAULT_SERVICE.parents[2]
        profiles = load_profiles()
        for filename, model, expected_forms in (
            ('expense_claim_views.xml', 'sc.expense.claim', 2),
            ('settlement_views.xml', 'sc.settlement.order', 1),
        ):
            tree = ET.parse(root / 'views/core' / filename)
            forms = [record for record in tree.findall('.//record')
                     if record.findtext("field[@name='model']") == model and record.find('.//form') is not None]
            self.assertEqual(len(forms), expected_forms)
            for form in forms:
                buttons = {button.get('name'): button for button in form.findall('.//header/button')}
                self.assertNotIn('action_approve', buttons)
                for action in ('approve', 'reject'):
                    method = profiles[model]['method_by_action'][action]
                    self.assertIn(method, buttons)
                    self.assertIn('can_review', buttons[method].get('invisible', ''))
                    self.assertIn('validation_status', buttons[method].get('invisible', ''))
                self.assertIn('action_done', buttons)

    def test_finance_execution_is_available_only_after_submission_confirmation(self):
        for filename, model, method in (
            ('receipt_income', 'sc.receipt.income', 'action_received'),
            ('self_funding_registration', 'sc.self.funding.registration', 'action_done'),
            ('financing_loan', 'sc.financing.loan', 'action_done'),
            ('treasury_reconciliation', 'sc.treasury.reconciliation', 'action_reconcile'),
        ):
            for state in ('draft', 'confirmed'):
                actions = self._general_contract_actions(state, model=model)
                self.assertEqual(method in [action['method'] for action in actions], state == 'confirmed')
            tree = ET.parse(DEFAULT_SERVICE.parents[2] / 'views/core' / (filename + '_views.xml'))
            buttons = tree.findall(".//button[@name='%s']" % method)
            self.assertTrue(buttons)
            for button in buttons:
                self.assertEqual(button.get('invisible'), "state != 'confirmed'")

    def test_contract_execution_native_and_projection_require_confirmation(self):
        tree = ET.parse(DEFAULT_SERVICE.parents[2] / 'views/core/contract_views.xml')
        buttons = tree.findall(".//button[@name='action_set_running']")
        self.assertEqual(len(buttons), 3)
        for button in buttons:
            self.assertEqual(button.get('invisible'), "state != 'confirmed'")
        for model in ('construction.contract', 'construction.contract.income', 'construction.contract.expense'):
            for state in ('draft', 'confirmed', 'running', 'closed'):
                actions = self._general_contract_actions(state, model=model)
                self.assertEqual('action_set_running' in [action['method'] for action in actions], state == 'confirmed')

    def test_payment_execution_actions_match_domain_and_native_state_boundaries(self):
        expected = {
            'draft': {'action_confirm', 'action_cancel'},
            'confirmed': {'action_paid', 'action_cancel'},
            'paid': {'action_reverse_payment'},
            'cancel': set(), 'legacy_confirmed': set(), 'unknown': set(),
        }
        for state, methods in expected.items():
            with self.subTest(state=state):
                actions = self._general_contract_actions(state, model='sc.payment.execution')
                self.assertEqual({action['method'] for action in actions}, methods)
                if state == 'paid':
                    self.assertEqual(actions[0]['label'], '撤销付款')
                    self.assertEqual(actions[0]['target'], {'model': 'sc.payment.execution', 'id': 23, 'method': 'action_reverse_payment'})
                    self.assertEqual(actions[0]['action_semantics']['purpose'], 'cancel_record')
        tree = ET.parse(DEFAULT_SERVICE.parents[2] / 'views/core/payment_execution_views.xml')
        for method, state in [('action_paid', 'confirmed'), ('action_reverse_payment', 'paid')]:
            buttons = tree.findall(".//button[@name='%s']" % method)
            self.assertTrue(buttons)
            for button in buttons:
                self.assertEqual(button.get('invisible'), "state != '%s'" % state)
                self.assertEqual(button.get('groups'), 'smart_construction_core.group_sc_cap_finance_manager')

    def test_payment_reversal_native_confirmation_projects_without_method_guessing(self):
        tree = ET.parse(DEFAULT_SERVICE.parents[2] / 'views/core/payment_execution_views.xml')
        button = tree.find(".//button[@name='action_reverse_payment']")
        self.assertIsNotNone(button)
        message = button.get('confirm')
        self.assertTrue(message)
        self.assertIn('付款台账', message)
        self.assertIn('已批准', message)
        parser = DEFAULT_SERVICE.parents[3] / 'smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py'
        method = next(n for n in ast.walk(ast.parse(parser.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_button_action_safety')
        namespace = {'_': lambda text: text}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(parser), 'exec'), namespace)
        safety = namespace['_button_action_safety'](None, btn_node=button, btype='object',
            method=button.get('name'), label=button.get('string'), classes=['btn-secondary'], confirm=message, level='header')
        self.assertEqual(safety['classification'], 'danger')
        self.assertTrue(safety['requires_confirm'])
        self.assertEqual(safety['confirm_message'], message)

    def test_contract_event_uses_real_reviewer_actions_and_resubmission(self):
        for state in ('draft', 'rejected'):
            self.assertEqual({a['method'] for a in self._general_contract_actions(state, model='sc.contract.event')}, {'action_submit', 'action_cancel'})
        for can_review in (True, False):
            actions = self._general_contract_actions('submitted', model='sc.contract.event', approval_phase='pending', can_review=can_review)
            self.assertEqual({a['method'] for a in actions}, {'action_cancel', 'validate_tier', 'reject_tier'} if can_review else {'action_cancel'})
        self.assertEqual({a['method'] for a in self._general_contract_actions('approved', model='sc.contract.event')}, {'action_done'})
        tree = ET.parse(DEFAULT_SERVICE.parents[2] / 'views/core/contract_event_views.xml')
        buttons = {b.get('name'): b for b in tree.findall('.//header/button')}
        self.assertNotIn('action_approve', buttons)
        self.assertNotIn('action_reject', buttons)
        for method in ('validate_tier', 'reject_tier'):
            self.assertIn('can_review', buttons[method].get('invisible'))

    def test_plan_native_and_contract_actions_match_executable_model_states(self):
        model = DEFAULT_SERVICE.parents[1] / 'core/plan_management.py'
        names = {'action_confirm', 'action_start', 'action_done', 'action_cancel', 'action_reset_draft'}
        methods = [node for node in ast.walk(ast.parse(model.read_text())) if isinstance(node, ast.FunctionDef) and node.name in names]
        namespace = {'UserError': ValueError, '_': lambda text: text,
                     'fields': SimpleNamespace(Date=SimpleNamespace(context_today=lambda record: '2026-09-30'))}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(model), 'exec'), namespace)
        tree = ET.parse(DEFAULT_SERVICE.parents[2] / 'views/core/plan_management_views.xml')
        buttons = {button.get('name'): button for button in tree.findall('.//header/button') if button.get('name') in names}
        self.assertEqual(set(buttons), names)
        class Plan:
            def __init__(self, state):
                self.state = state
                self.env = {'sc.approval.policy': SimpleNamespace(_start_submission_review=lambda rec: False, _assert_submission_approved=lambda rec, states: None)}
            def with_context(self, **kwargs): return self
            def __iter__(self): return iter([self])
            def _check_business_anchor(self, **kwargs): pass
            def write(self, values): self.__dict__.update(values)
        for state in ('draft', 'confirmed', 'in_progress', 'done', 'cancel', 'unknown'):
            with self.subTest(state=state):
                executable = set()
                for method in names:
                    try: namespace[method](Plan(state))
                    except ValueError: continue
                    executable.add(method)
                visible = {method for method, button in buttons.items()
                           if not eval(button.get('invisible'), {'__builtins__': {}}, {'state': state, 'validation_status': 'no'})}
                projected = {action['method'] for action in self._general_contract_actions(state, model='sc.plan')}
                self.assertEqual(visible, executable)
                self.assertEqual(projected, executable)

    def test_diary_completion_and_reviewer_actions_match_native_contract(self):
        for state in ('draft', 'confirmed', 'done', 'cancel', 'legacy_confirmed'):
            actions = self._general_contract_actions(state, model='sc.construction.diary')
            self.assertEqual('action_done' in {a['method'] for a in actions}, state == 'confirmed')
        for reviewer in (False, True):
            actions = self._general_contract_actions('draft', model='sc.construction.diary', approval_phase='pending', can_review=reviewer)
            self.assertEqual('validate_tier' in {a['method'] for a in actions}, reviewer)
            self.assertEqual('reject_tier' in {a['method'] for a in actions}, reviewer)
        tree = ET.parse(DEFAULT_SERVICE.parents[2] / 'views/core/construction_diary_views.xml')
        buttons = {b.get('name'): b for b in tree.findall('.//header/button')}
        self.assertEqual(buttons['action_done'].get('invisible'), "state != 'confirmed'")
        self.assertEqual(buttons['action_cancel'].get('invisible'), "state not in ('draft', 'confirmed')")
        for name in ('validate_tier', 'reject_tier'):
            self.assertIn('can_review', buttons[name].get('invisible'))

    def test_diary_finalizer_preserves_native_and_configured_field_structure(self):
        path = DEFAULT_SERVICE.parents[2] / 'core_extension.py'
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'smart_core_finalize_unified_page_contract_v2')
        def workflow(env, out, source, **kw):
            out['actionContract'] = {'reviewerActions': ['validate_tier', 'reject_tier']}
        namespace = {'deepcopy': copy.deepcopy, '_sc_text': lambda value: str(value or ''),
            '_sc_inject_workflow_contract': workflow, 'inject_financial_workspace_runtime': lambda *args: None,
            'smart_core_form_business_actions': None,
            '_contract_normalizers': SimpleNamespace(normalize_payment_settlement_detail_component=lambda *args, **kw: None)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        names = ['name', 'title', 'description', 'attachment_ids', 'reject_reason', 'configured_extension']
        contract = {'pageInfo': {'model': 'sc.construction.diary', 'viewType': 'form'},
            'layoutContract': {'containerTree': [{'type': 'field', 'name': name, 'fieldInfo': {'name': name}} for name in names]},
            'formStructureContract': {'slots': [{'fieldRefs': names}]},
            'runtimeContract': {}, 'meta': {}}
        baseline = copy.deepcopy(contract)
        result = namespace['smart_core_finalize_unified_page_contract_v2'](None, contract, {'source_contract': {'model': 'sc.construction.diary', 'view_type': 'form'}})
        self.assertEqual(result['layoutContract'], baseline['layoutContract'])
        self.assertEqual(result['formStructureContract'], baseline['formStructureContract'])
        self.assertEqual(result['runtimeContract'], {})
        self.assertEqual(result['meta'], {})
        self.assertEqual(result['actionContract']['reviewerActions'], ['validate_tier', 'reject_tier'])
        self.assertEqual(contract, baseline)

    def test_project_actions_keep_approval_and_lifecycle_separate(self):
        for approved, pending, reviewer, expected in (
            (False, False, False, {'action_sc_submit', 'action_sc_close'}),
            (True, False, False, {'action_sc_start', 'action_sc_close'}),
            (False, True, False, {'action_sc_close'}),
            (False, True, True, {'validate_tier', 'reject_tier', 'action_sc_close'}),
        ):
            actions = self._general_contract_actions('draft', model='project.project',
                approval_phase='pending' if pending else 'none', can_review=reviewer,
                record_fields={'sc_approval_state': 'approved' if approved else 'draft', 'validation_status': 'pending' if pending else 'no'})
            self.assertEqual({a['method'] for a in actions}, expected)
        for state, expected in (
            ('in_progress', {'action_sc_pause', 'action_sc_mark_done', 'action_sc_begin_closing', 'action_sc_close'}),
            ('paused', {'action_sc_resume', 'action_sc_close'}),
            ('done', {'action_sc_begin_closing', 'action_sc_start_warranty', 'action_sc_close'}),
            ('closing', {'action_sc_start_warranty', 'action_sc_close'}),
            ('warranty', {'action_sc_close'}), ('closed', set()),
        ):
            actions = self._general_contract_actions(state, model='project.project')
            self.assertEqual({a['method'] for a in actions}, expected)
            for action in actions:
                self.assertEqual(action['action_semantics']['executor'], 'contract.action')
                self.assertNotEqual(action['action_semantics']['purpose'], 'cancel_record')

    def test_task_actions_follow_construction_state_and_real_reviewer(self):
        for state, expected in (('draft', 'action_prepare_task'), ('ready', 'action_start_task'), ('in_progress', 'action_mark_done'), ('done', None), ('cancelled', None)):
            actions = self._general_contract_actions(state, model='project.task')
            methods = {a['method'] for a in actions}
            self.assertEqual(methods, {expected} if expected else set())
        for can_review in (False, True):
            methods = {a['method'] for a in self._general_contract_actions('draft', model='project.task', approval_phase='pending', can_review=can_review)}
            self.assertEqual('validate_tier' in methods, can_review)
            self.assertEqual('reject_tier' in methods, can_review)
        self.assertEqual(load_profiles()['project.task']['state_field'], 'sc_state')

    def test_tax_deduction_requires_confirmation_and_keeps_finance_checks(self):
        path = DEFAULT_SERVICE.parents[1] / 'core/tax_deduction_registration.py'
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'action_deduct')
        namespace = {'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        class Record:
            deduction_confirm_date = '2026-09-30'
            deduction_amount = 100
            deduction_tax_amount = 10
            def __init__(self, state):
                self.state, self.calls = state, []
                self.env = {'sc.approval.policy': SimpleNamespace(
                    _assert_submission_approved=lambda rec, states: self.calls.append('approval'))}
            def __iter__(self): return iter([self])
            def _assert_finance_deduct_access(self): self.calls.append('finance')
            def _snapshot_audit_payload(self): return {'state': self.state}
            def _check_deduct_ready(self): self.calls.append('ready')
            def _check_company_contractor_deduction_responsibility_or_raise(self): self.calls.append('responsibility')
            def _write_finance_authority(self, values):
                self.calls.append('authority')
                self.state = values['state']
            def _audit_transition(self, *args, **kwargs): self.calls.append('audit')
        for state in ('draft', 'confirmed', 'deducted', 'legacy_confirmed', 'cancel'):
            record = Record(state)
            if state == 'confirmed':
                namespace['action_deduct'](record)
                self.assertEqual(record.calls, ['finance', 'approval', 'ready', 'responsibility', 'authority', 'audit'])
                self.assertEqual(record.state, 'deducted')
            else:
                with self.assertRaises(ValueError): namespace['action_deduct'](record)
                self.assertEqual(record.calls, ['finance'])
                self.assertEqual(record.state, state)
            actions = self._general_contract_actions(state, model='sc.tax.deduction.registration')
            self.assertEqual('action_deduct' in {a['method'] for a in actions}, state == 'confirmed')
        tree = ET.parse(DEFAULT_SERVICE.parents[2] / 'views/core/tax_deduction_registration_views.xml')
        self.assertEqual(tree.find(".//button[@name='action_deduct']").get('invisible'), "state != 'confirmed'")

    def test_the_shipped_registry_is_consistent(self) -> None:
        self.assertEqual(validate(_baseline()), [])

    def test_an_unregistered_native_transition_fails(self) -> None:
        payload = _baseline()
        payload["entries"] = [e for e in payload["entries"] if e["method"] != "action_load_purchase_order_lines"]
        self.assertTrue(any("action_load_purchase_order_lines" in error for error in validate(payload)))

    def test_an_entry_with_no_native_button_is_stale(self) -> None:
        payload = _baseline()
        payload["entries"].append(
            {"model": "sc.nothing.here", "method": "action_ghost", "class": "navigation", "reason": "probe"}
        )
        errors = validate(payload)
        self.assertTrue(any("action_ghost" in error for error in errors))

    def test_an_entry_whose_method_is_now_declared_is_stale(self) -> None:
        payload = _baseline()
        payload["entries"].append(
            {"model": "payment.request", "method": "action_submit", "class": "navigation", "reason": "probe"}
        )
        errors = validate(payload)
        self.assertTrue(any("now declares it" in error for error in errors))

    def test_an_entry_without_a_reason_fails(self) -> None:
        payload = _baseline()
        for entry in payload["entries"]:
            if entry["method"] == "action_load_purchase_order_lines":
                entry.pop("reason", None)
        self.assertTrue(any("without a reason" in error for error in validate(payload)))

    def test_an_unknown_class_fails(self) -> None:
        payload = _baseline()
        for entry in payload["entries"]:
            if entry["method"] == "action_load_purchase_order_lines":
                entry["class"] = "not_a_class"
        self.assertTrue(any("expected one of" in error for error in validate(payload)))

    def test_every_shipped_entry_declares_a_meaningful_class(self) -> None:
        payload = _baseline()
        allowed = {"state_transition_undeclared", "navigation", "document_helper"}
        covered = {entry["class"] for entry in payload["entries"]}
        self.assertTrue(covered <= allowed)
        self.assertNotIn("state_transition_undeclared", covered)

    def test_validate_does_not_mutate_the_registry_payload(self) -> None:
        payload = _baseline()
        before = copy.deepcopy(payload)
        validate(payload)
        self.assertEqual(payload, before)

    def test_helper_built_profiles_are_scanned_too(self) -> None:
        # Regression for the coverage hole that hid seven buttons: a regex over
        # the source text only sees inline literals, so every model adopted
        # through a **_helper(...) call was silently left unscanned.
        models = adopted_models()
        for helper_built in (
            "sc.fund.account.operation",
            "sc.equipment.plan",
            "sc.quality.issue",
            "sc.material.settlement",
        ):
            self.assertIn(helper_built, models, "helper-built profile is missing from the scan")

    def test_a_helper_built_model_transition_must_be_registered(self) -> None:
        payload = _baseline()
        payload["entries"] = [e for e in payload["entries"] if e["method"] != "action_create_remaining_payment_request"]
        errors = validate(payload)
        self.assertTrue(any("action_create_remaining_payment_request" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
