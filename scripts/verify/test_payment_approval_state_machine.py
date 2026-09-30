#!/usr/bin/env python3
"""Execute production approval methods with isolated collaborators, without an ORM."""
import ast
import copy
import sys
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / 'addons/smart_construction_core/models/core/payment_request.py'
POLICY = ROOT / 'addons/smart_construction_core/models/support/approval_policy.py'
STATE = ROOT / 'addons/smart_construction_core/models/support/state_machine.py'


def guard(*args, **kwargs):
    raise ValueError(args[0])


def load_methods():
    package = types.ModuleType('payment_approval_probe')
    package.__path__ = []
    sys.modules[package.__name__] = package
    helper = types.ModuleType('payment_approval_probe.state_guard')
    helper.raise_guard = guard
    sys.modules[helper.__name__] = helper
    namespace = {'_': lambda x: x, 'UserError': ValueError, 'AccessError': PermissionError,
                 'raise_guard': guard, '_AUTOMATIC_APPROVAL_TOKEN': object(),
                 '__package__': package.__name__}
    state_class = next(n for n in ast.parse(STATE.read_text()).body if isinstance(n, ast.ClassDef))
    exec(compile(ast.Module(body=[state_class], type_ignores=[]), str(STATE), 'exec'), namespace)
    names = {'_route_submitted_approval', '_complete_payment_approval',
             '_check_approval_state_transition', 'action_approval_decision',
             'action_approve', 'action_set_approved', 'action_on_tier_approved',
             'action_approval_reject', 'action_on_tier_rejected'}
    tree = ast.parse(MODEL.read_text())
    methods = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(methods) == len(names)
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(MODEL), 'exec'), namespace)
    for name in ('_start_submission_review', '_approve_submission_review', '_assert_submission_approved', '_reject_submission_review'):
        route = next(n for n in ast.walk(ast.parse(POLICY.read_text())) if isinstance(n, ast.FunctionDef) and n.name == name)
        route.decorator_list = []
        exec(compile(ast.Module(body=[route], type_ignores=[]), str(POLICY), 'exec'), namespace)
    return namespace, names


PRODUCTION, METHODS = load_methods()


class Reviews(list):
    def filtered(self, predicate):
        return Reviews(row for row in self if predicate(row))

    def write(self, values):
        for row in self:
            for key, value in values.items():
                setattr(row, key, value)


class Record:
    _name = 'payment.request'
    display_name = 'approval probe'

    def __init__(self, *, required=True, reviews=None, status='no', state='submit', matching=True):
        self.data = dict(state=state, review_ids=Reviews(reviews or []), validation_status=status,
                         can_review=True, audits=[], messages=[], requests=0, restarts=0,
                         next_status='validated', authorized=True)
        self.company_id = types.SimpleNamespace(id=7)
        self.policy = types.SimpleNamespace(is_approval_required=self.requirement)
        self.policy._start_submission_review = lambda record: PRODUCTION['_start_submission_review'](self.policy, record)
        self.policy._approve_submission_review = lambda record: PRODUCTION['_approve_submission_review'](self.policy, record)
        self.policy._reject_submission_review = lambda record, reason=None: PRODUCTION['_reject_submission_review'](self.policy, record, reason=reason)
        self.required = required
        self.matching = matching
        self.env = types.SimpleNamespace(context={}, company=self.company_id)

    def requirement(self, model, company):
        assert model == self._name and company.id == 7
        return self.required

    def __getattr__(self, key):
        if key in self.__dict__.get("data", {}):
            return self.__dict__["data"][key]
        raise AttributeError(key)

    def __iter__(self):
        yield self

    def ensure_one(self):
        pass

    def with_company(self, company):
        assert company.id == 7
        return self

    def with_context(self, **values):
        clone = copy.copy(self)
        clone.env = types.SimpleNamespace(context={**self.env.context, **values}, company=self.company_id)
        return clone

    def restart_validation(self):
        self.data['restarts'] += 1
        self.data.update(review_ids=[], validation_status='no')

    def request_validation(self):
        self.data['requests'] += 1
        self.data.update(review_ids=['real-tier'] if self.matching else [],
                         validation_status='pending' if self.matching else 'no')
        return self.review_ids

    def _assert_finance_approve_access(self):
        if not self.authorized:
            raise PermissionError('finance denied')

    def validate_tier(self):
        self.data['validation_status'] = self.next_status

    def _get_sequences_to_approve(self, user):
        return [1]

    def _rejected_tier(self, reviews):
        reviews.write({'status': 'rejected'})
        self.data['validation_status'] = 'rejected'
        self.action_on_tier_rejected()

    def _update_counter(self, values):
        pass

    def _get_tier_reject_reason(self):
        return next((row.comment for row in self.review_ids if row.status == 'rejected'), None)

    def _check_detail_amount_consistency(self):
        pass

    def _check_material_settlement_remaining_amount(self):
        pass

    def _collect_payment_advisories(self, *args):
        return []

    def _handle_payment_advisories(self, *args):
        return {}

    def _snapshot_audit_payload(self):
        return {'state': self.state}

    def _audit_transition(self, event, before, after, **kw):
        self.audits.append((event, before, after, kw))

    def _message_post_non_blocking(self, message):
        self.messages.append(message)

    def write(self, vals):
        if 'state' in vals:
            self._check_approval_state_transition(vals['state'])
        self.data.update(vals)


# Preserve the production method's env lookup while retaining immutable context clones.
class Env(types.SimpleNamespace):
    def __getitem__(self, name):
        if name == 'ir.sequence':
            return types.SimpleNamespace(next_by_code=lambda code: 'PLAN-TEST')
        if name == 'sc.data.validator':
            return self.validator
        assert name == 'sc.approval.policy'
        return self.policy


original_context = Record.with_context

def with_context(self, **values):
    clone = original_context(self, **values)
    clone.env = Env(context=clone.env.context, company=self.company_id, policy=self.policy)
    return clone

Record.with_context = with_context
for name in METHODS:
    setattr(Record, name, PRODUCTION[name])


class PaymentApprovalStateMachineTests(unittest.TestCase):
    def record(self, **kwargs):
        rec = Record(**kwargs)
        rec.env = Env(context={}, company=rec.company_id, policy=rec.policy, user=42)
        return rec

    def test_shared_submission_route_has_no_model_specific_policy_branch(self):
        for model in ('payment.request', 'sc.expense.claim', 'sc.settlement.order', 'another.business.document'):
            for required in (False, True):
                with self.subTest(model=model, required=required):
                    rec = self.record(required=required)
                    rec._name = model
                    self.assertEqual(rec.policy._start_submission_review(rec), required)
                    self.assertEqual(rec.requests, int(required))
                    self.assertEqual(rec.state, 'submit')

    def test_shared_route_preserves_inflight_instance_despite_policy_change(self):
        for status in ('waiting', 'pending'):
            rec = self.record(required=False, reviews=['existing'], status=status)
            with self.assertRaisesRegex(ValueError, '仍在审批中'):
                rec.policy._start_submission_review(rec)
            self.assertEqual(rec.review_ids, ['existing'])
            self.assertEqual(rec.restarts, 0)
            self.assertEqual(rec.requests, 0)

    def test_shared_route_refuses_failed_native_restart(self):
        rec = self.record(required=False, reviews=['old'], status='rejected')
        rec.restart_validation = lambda: None
        with self.assertRaisesRegex(ValueError, '未能重置'):
            rec.policy._start_submission_review(rec)

    def test_expense_submission_executes_shared_route_and_preserves_audit(self):
        path = MODEL.with_name('expense_claim.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'action_submit')
        namespace = {'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        for required in (False, True):
            rec = self.record(required=required, state='draft')
            rec._name = 'sc.expense.claim'
            checks = []
            rec._check_business_ready = lambda: checks.append('checked')
            rec.write = lambda values: rec.data.update(values)
            rec._audit_transition = lambda *values: rec.audits.append(values)
            namespace['action_submit'](rec)
            self.assertEqual(checks, ['checked'])
            self.assertEqual(rec.state, 'submit' if required else 'approved')
            self.assertEqual(rec.requests, int(required))
            self.assertEqual(len(rec.audits), 1)
            self.assertEqual(rec.audits[0][1]['state'], 'draft')
            self.assertEqual(rec.audits[0][2]['state'], rec.state)

    def test_settlement_submission_preserves_checks_before_shared_route(self):
        path = MODEL.with_name('settlement_order.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'action_submit')
        namespace = {'raise_guard': guard, '_': lambda text: text}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        for required in (False, True):
            rec = self.record(required=required, state='draft')
            rec._name = 'sc.settlement.order'
            rec.ids = [23]
            calls = []
            rec._assert_lifecycle_role = lambda role: calls.append(role)
            rec._lock_lifecycle_rows = lambda: calls.append('lock')
            rec._check_business_anchor_or_raise = lambda: calls.append('anchor')
            rec._check_line_contracts_or_raise = lambda: calls.append('lines')
            rec._check_contract_consistency_or_raise = lambda **kw: calls.append(('contract', kw))
            rec._check_purchase_orders_or_raise = lambda **kw: calls.append(('purchase', kw))
            rec.env.validator = types.SimpleNamespace(validate_or_raise=lambda **kw: calls.append(('validate', kw)))
            rec.policy.sudo = lambda: rec.policy
            def transition(state):
                calls.append(('state', state))
                rec.data['state'] = state
            rec._write_lifecycle = transition
            namespace['action_submit'](rec)
            self.assertEqual(calls[:4], ['submit', 'lock', 'anchor', 'lines'])
            self.assertEqual(calls[6], ('validate', {'scope': {'res_model': rec._name, 'res_ids': [23]}}))
            self.assertEqual(calls[7], ('state', 'submit'))
            self.assertEqual(rec.state, 'submit' if required else 'approve')
            self.assertEqual(rec.requests, int(required))

    def test_shared_decision_never_reads_changed_policy(self):
        for required in (False, True):
            rec = self.record(required=required, reviews=['tier'], status='pending')
            rec.policy.is_approval_required = lambda *a, **kw: self.fail('in-flight policy read')
            rec.policy._approve_submission_review(rec)
            self.assertEqual(rec.validation_status, 'validated')
            self.assertEqual(rec.state, 'submit')

    def test_shared_decision_denies_missing_rejected_and_wrong_reviewer(self):
        for reviews, status, can_review in (([], 'validated', True), (['tier'], 'rejected', True), (['tier'], 'pending', False)):
            rec = self.record(reviews=reviews, status=status)
            rec.data['can_review'] = can_review
            with self.assertRaises(ValueError if can_review else PermissionError):
                rec.policy._approve_submission_review(rec)
            self.assertEqual(rec.state, 'submit')

    def test_shared_decision_preserves_comment_wizard_result(self):
        rec = self.record(reviews=['tier'], status='pending')
        wizard = {'type': 'ir.actions.act_window', 'res_model': 'comment.wizard'}
        rec.validate_tier = lambda: wizard
        self.assertIs(rec.policy._approve_submission_review(rec), wizard)
        self.assertEqual(rec.validation_status, 'pending')

    def test_expense_compatibility_approval_uses_instance_and_is_idempotent(self):
        path = MODEL.with_name('expense_claim.py')
        names = {'action_approve', 'action_on_tier_approved', 'action_on_tier_rejected'}
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in names]
        namespace = {'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
        for status in ('pending', 'validated'):
            rec = self.record(required=False, reviews=['tier'], status=status)
            rec._name = 'sc.expense.claim'
            rec._check_business_ready = lambda: None
            rec.write = lambda values: rec.data.update(values)
            rec._audit_transition = lambda *values: rec.audits.append(values)
            rec.action_on_tier_approved = lambda: namespace['action_on_tier_approved'](rec)
            namespace['action_approve'](rec)
            namespace['action_approve'](rec)
            rec.action_on_tier_approved()
            self.assertEqual(rec.state, 'approved')
            self.assertEqual(len(rec.audits), 1)
        rec = self.record(required=False, state='submit')
        with self.assertRaises(ValueError):
            namespace['action_on_tier_rejected'](rec)
        self.assertEqual(rec.state, 'submit')

    def test_settlement_compatibility_approval_keeps_partial_chain_and_blocks_draft(self):
        path = MODEL.with_name('settlement_order.py')
        names = {'action_approve', 'action_on_tier_approved'}
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in names]
        namespace = {'UserError': ValueError, 'raise_guard': guard, '_': lambda text: text}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
        for final_status in ('pending', 'validated'):
            rec = self.record(required=False, reviews=['tier'], status='pending')
            rec._name = 'sc.settlement.order'
            rec.ids = [23]
            rec.data['next_status'] = final_status
            rec._assert_lifecycle_role = lambda role: None
            rec._lock_lifecycle_rows = lambda: None
            rec._check_business_anchor_or_raise = lambda: None
            rec._check_line_contracts_or_raise = lambda: None
            rec._check_contract_consistency_or_raise = lambda **kw: None
            rec._check_purchase_orders_or_raise = lambda **kw: None
            rec.env.validator = types.SimpleNamespace(validate_or_raise=lambda **kw: None)
            rec._write_lifecycle = lambda state: rec.data.update(state=state)
            rec.action_on_tier_approved = lambda: namespace['action_on_tier_approved'](rec)
            namespace['action_approve'](rec)
            self.assertEqual(rec.state, 'approve' if final_status == 'validated' else 'submit')
            rec.data['state'] = 'draft'
            with self.assertRaises(ValueError):
                namespace['action_approve'](rec)

    def test_finance_document_family_confirms_through_shared_submission(self):
        for filename in ('receipt_income', 'payment_execution', 'invoice_registration', 'financing_loan',
                         'self_funding_registration', 'treasury_reconciliation', 'settlement_adjustment'):
            path = MODEL.with_name(filename + '.py')
            method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'action_confirm')
            namespace = {'UserError': ValueError, 'raise_guard': guard, '_': lambda text: text}
            exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
            for required, retry in ((False, False), (True, False), (True, True)):
                with self.subTest(model=filename, required=required, retry=retry):
                    rec = self.record(required=required, state='draft', reviews=['old'] if retry else [], status='rejected' if retry else 'no')
                    rec._name = 'sc.' + filename.replace('_', '.')
                    checks = []
                    for check in ('_assert_finance_handling_access', '_check_business_anchor', '_check_business_anchor_or_raise', '_check_payment_request_scope_or_raise',
                                  '_check_company_contractor_payment_responsibility_or_raise', '_check_done_ready', '_check_reconcile_ready'):
                        setattr(rec, check, lambda name=check: checks.append(name))
                    rec.invalidate_recordset = lambda: None
                    rec.write = lambda values: rec.data.update(values)
                    rec._audit_transition = lambda *args, **kw: rec.audits.append((args, kw))
                    namespace['action_confirm'](rec)
                    self.assertTrue(checks)
                    if filename == 'payment_execution':
                        self.assertEqual(checks[0], '_assert_finance_handling_access')
                    self.assertEqual(rec.state, 'draft' if required else 'confirmed')
                    self.assertEqual(rec.requests, int(required))
                    self.assertEqual(rec.restarts, int(retry))
                    self.assertEqual(rec.validation_status, 'pending' if required else 'no')
                    if required:
                        rec.required = False
                        with self.assertRaisesRegex(ValueError, '仍在审批中'):
                            namespace['action_confirm'](rec)
                        self.assertEqual(rec.state, 'draft')
                        self.assertEqual(rec.requests, 1)

    def test_execution_requires_completed_submission_not_current_configuration(self):
        for state, reviews, status, allowed in (
            ('draft', [], 'no', False), ('draft', ['tier'], 'validated', False),
            ('confirmed', [], 'no', True), ('confirmed', ['tier'], 'validated', True),
            ('confirmed', ['tier'], 'pending', False), ('confirmed', ['tier'], 'rejected', False),
        ):
            for required in (False, True):
                rec = self.record(state=state, reviews=reviews, status=status, required=required)
                call = lambda: PRODUCTION['_assert_submission_approved'](rec.policy, rec, ('confirmed',))
                if allowed:
                    self.assertTrue(call())
                else:
                    with self.assertRaises(ValueError):
                        call()

    def test_finance_family_callbacks_require_real_review_outcomes(self):
        for filename in ('receipt_income', 'payment_execution', 'invoice_registration', 'financing_loan',
                         'self_funding_registration', 'treasury_reconciliation', 'settlement_adjustment'):
            path = MODEL.with_name(filename + '.py')
            methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef)
                       and n.name in {'action_on_tier_approved', 'action_on_tier_rejected'}]
            namespace = {'UserError': ValueError, '_': lambda text: text}
            exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
            for method, expected in (('action_on_tier_approved', 'validated'), ('action_on_tier_rejected', 'rejected')):
                for reviews, status in (([], expected), (['tier'], 'pending'), (['tier'], expected)):
                    with self.subTest(model=filename, method=method, status=status, reviews=reviews):
                        rec = self.record(state='draft', reviews=reviews, status=status)
                        rec.write = lambda values: rec.data.update(values)
                        rec._audit_transition = lambda *args, **kw: rec.audits.append((args, kw))
                        rec._check_business_anchor = lambda: None
                        rec._get_tier_reject_reason = lambda: 'real rejection'
                        namespace[method](rec)
                        effective = bool(reviews) and status == expected
                        self.assertEqual(rec.state, 'confirmed' if effective and expected == 'validated' else 'draft')
                        if not effective:
                            self.assertEqual(rec.audits, [])
                            self.assertNotIn('reject_reason', rec.data)

    def test_contract_family_shared_submission_and_non_recursive_callbacks(self):
        for path, model in ((MODEL.with_name('general_contract.py'), 'sc.general.contract'),
                            (MODEL.parents[1] / 'support/contract_center.py', 'construction.contract')):
            methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef)
                       and n.name in {'action_confirm', 'action_on_tier_approved', 'action_on_tier_rejected'}]
            namespace = {'UserError': ValueError, '_': lambda text: text}
            exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
            for required, retry in ((False, False), (True, False), (True, True)):
                with self.subTest(model=model, required=required, retry=retry):
                    rec = self.record(required=required, state='draft', reviews=['old'] if retry else [], status='rejected' if retry else 'no')
                    rec._name = model
                    rec.write = lambda values: rec.data.update(values)
                    rec._check_business_anchor = lambda: None
                    rec._post_contract_state_message = lambda message: rec.messages.append(message)
                    rec.action_on_tier_approved = lambda: namespace['action_on_tier_approved'](rec)
                    namespace['action_confirm'](rec)
                    self.assertEqual(rec.state, 'draft' if required else 'confirmed')
                    self.assertEqual(rec.requests, int(required))
                    self.assertEqual(rec.restarts, int(retry))
                    if required:
                        rec.required = False
                        rec.action_on_tier_approved()
                        self.assertEqual(rec.requests, 1)
                        self.assertEqual(rec.state, 'draft')
                        with self.assertRaises(ValueError):
                            namespace['action_confirm'](rec)
                        rec.data['validation_status'] = 'validated'
                        rec.action_on_tier_approved()
                        rec.action_on_tier_approved()
                        self.assertEqual(rec.state, 'confirmed')
                        self.assertEqual(rec.requests, 1)
                    rec.data.update(state='draft', review_ids=[], validation_status='validated')
                    rec.action_on_tier_approved()
                    self.assertEqual(rec.state, 'draft')
                    rec.data['validation_status'] = 'rejected'
                    namespace['action_on_tier_rejected'](rec)
                    self.assertEqual(rec.state, 'draft')

    def test_purchase_confirmation_only_executes_eligible_records(self):
        path = MODEL.with_name('purchase_extend.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'button_confirm')
        class Orders(list):
            def __init__(self, records=()):
                super().__init__(records)
                self.env = Env(policy=types.SimpleNamespace(_start_submission_review=lambda record: record.policy._start_submission_review(record)))
                self.ledger_calls = 0
            def browse(self):
                return Orders()
            def __ior__(self, record):
                self.append(record)
                return self
            def _create_enabled_cost_ledger_entries(self):
                for record in self:
                    record.data['ledger_calls'] += 1
        def parent_confirm(records):
            for record in records:
                record.data['state'] = 'purchase'
            return True
        namespace = {'_': lambda text: text, 'PurchaseOrder': object,
                     'super': lambda cls, records: types.SimpleNamespace(button_confirm=lambda: parent_confirm(records))}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        for required, status, reviews, expected in (
            (False, 'no', [], 'purchase'), (True, 'no', [], 'draft'),
            (True, 'rejected', ['old'], 'draft'), (True, 'validated', ['tier'], 'purchase'),
        ):
            rec = self.record(required=required, state='draft', status=status, reviews=reviews)
            rec._name = 'purchase.order'
            rec.project_id = False
            rec.data['ledger_calls'] = 0
            rec.write = lambda values: rec.data.update(values)
            result = namespace['button_confirm'](Orders([rec]))
            self.assertEqual(rec.state, expected)
            self.assertEqual(rec.ledger_calls, int(expected == 'purchase'))
            if expected == 'purchase':
                self.assertTrue(namespace['button_confirm'](Orders([rec])))
                self.assertEqual(rec.ledger_calls, 1)
            if expected == 'draft':
                self.assertEqual(result['tag'], 'display_notification')
                self.assertEqual(rec.requests, 1)
                rec.required = False
                with self.assertRaises(ValueError):
                    namespace['button_confirm'](Orders([rec]))
                self.assertEqual(rec.ledger_calls, 0)

    def test_material_plan_submission_and_decision_use_real_approval(self):
        path = MODEL.with_name('material_plan.py')
        names = {'action_submit', 'action_approve', 'action_on_tier_approved', 'action_on_tier_rejected'}
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in names]
        namespace = {'UserError': ValueError, '_': lambda text: text,
                     'fields': types.SimpleNamespace(Datetime=types.SimpleNamespace(now=lambda: 'now'))}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
        for required in (False, True):
            rec = self.record(required=required, state='draft')
            rec._name = 'project.material.plan'
            rec.env.user = types.SimpleNamespace(id=42, has_group=lambda name: True)
            rec.name = '新建'
            rec._check_business_anchor = lambda: None
            rec._normalize_lines_uom = lambda: None
            rec.invalidate_recordset = lambda: None
            rec.activity_unlink = lambda kinds: None
            rec.write = lambda values: rec.data.update(values)
            rec.action_on_tier_approved = lambda: namespace['action_on_tier_approved'](rec)
            namespace['action_submit'](rec)
            self.assertEqual(rec.state, 'submit' if required else 'approved')
            self.assertEqual(rec.requests, int(required))
            if not required:
                self.assertFalse(rec.approved_by)
            else:
                rec.required = False
                rec.data['next_status'] = 'pending'
                namespace['action_approve'](rec)
                self.assertEqual(rec.state, 'submit')
                rec.data['next_status'] = 'validated'
                namespace['action_approve'](rec)
                self.assertEqual(rec.state, 'approved')
                count = len(rec.audits)
                rec.action_on_tier_approved()
                self.assertEqual(len(rec.audits), count)
            rec.data.update(state='submit', review_ids=[], validation_status='rejected')
            namespace['action_on_tier_rejected'](rec)
            self.assertEqual(rec.state, 'submit')

    def test_shared_rejection_records_actual_reviewer_comment(self):
        rec = self.rejecting_record()
        PRODUCTION['_reject_submission_review'](rec.policy, rec, reason=' wrong amount ')
        self.assertEqual(rec.review_ids[0].comment, 'wrong amount')
        self.assertEqual(rec.review_ids[0].status, 'rejected')
        rec = self.rejecting_record(reviewer=99)
        with self.assertRaises(PermissionError):
            PRODUCTION['_reject_submission_review'](rec.policy, rec, reason='wrong')
        self.assertEqual(rec.validation_status, 'pending')
        rec = self.rejecting_record()
        wizard = {'type': 'ir.actions.act_window'}
        rec.reject_tier = lambda: wizard
        self.assertIs(PRODUCTION['_reject_submission_review'](rec.policy, rec), wizard)

    def test_payment_shared_approval_preserves_native_comment_wizard(self):
        rec = self.record(reviews=['tier'], status='pending')
        wizard = {'type': 'ir.actions.act_window', 'res_model': 'comment.wizard'}
        rec.validate_tier = lambda: wizard
        self.assertIs(rec.action_approval_decision(), wizard)
        self.assertEqual(rec.state, 'submit')
        self.assertEqual(rec.audits, [])

    def test_outbound_approval_never_executes_stock_or_cost_operations(self):
        path = MODEL.with_name('material_acceptance.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScMaterialOutbound')
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in {'action_submit', 'action_issue', 'action_on_tier_approved', 'action_on_tier_rejected'}]
        namespace = {'ValidationError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
        for required in (False, True):
            for kind in ('issue', 'return', 'transfer', 'loss'):
                rec = self.record(required=required, state='draft')
                rec._name = 'sc.material.outbound'
                rec.id = 23
                rec.outbound_type = kind
                rec.dest_warehouse_id = True
                rec.purpose = 'material use'
                rec.line_ids = types.SimpleNamespace(_check_qty=lambda: None)
                rec._sc_require_material_user = lambda label: None
                rec._sc_require_material_manager = lambda label: None
                def require_state(states, label):
                    if rec.state not in states:
                        raise ValueError('wrong state')
                rec._sc_require_state = require_state
                rec._validate_return_authority = lambda **kw: None
                rec._sc_material_audit_payload = lambda: {'state': rec.state}
                rec._sc_warn_system_defaults_on_action = lambda label: None
                rec._write_cost_source_state = lambda values: rec.data.update(values)
                rec._sc_audit_material_transition = lambda *args, **kw: rec.audits.append((args, kw))
                rec.policy._assert_submission_approved = lambda record, states: PRODUCTION['_assert_submission_approved'](rec.policy, record, states)
                executed = []
                rec._complete_issue = lambda: executed.append('issue')
                namespace['action_submit'](rec)
                self.assertEqual(rec.state, 'submitted' if required else 'approved')
                self.assertEqual(executed, [])
                if required:
                    with self.assertRaises(ValueError):
                        namespace['action_issue'](rec)
                    namespace['action_on_tier_approved'](rec)
                    self.assertEqual(rec.state, 'submitted')
                    rec.data['validation_status'] = 'validated'
                    namespace['action_on_tier_approved'](rec)
                    self.assertEqual(rec.state, 'approved')
                    self.assertEqual(executed, [])
                namespace['action_issue'](rec)
                self.assertEqual(executed, ['issue'])

    def test_contract_execution_requires_established_approval(self):
        path = MODEL.parents[1] / 'support/contract_center.py'
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef)
                   and n.name in {'action_set_running', 'action_close'}]
        namespace = {'UserError': ValueError}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
        for state, reviews, status, allowed in (
            ('draft', [], 'no', False), ('draft', ['tier'], 'validated', False),
            ('confirmed', [], 'no', True), ('confirmed', ['tier'], 'pending', False),
            ('confirmed', ['tier'], 'validated', True),
        ):
            for required in (False, True):
                rec = self.record(state=state, reviews=reviews, status=status, required=required)
                rec.policy._assert_submission_approved = lambda record, states: PRODUCTION['_assert_submission_approved'](rec.policy, record, states)
                rec._post_contract_state_message = lambda message: rec.messages.append(message)
                if allowed:
                    namespace['action_set_running'](rec)
                    self.assertEqual(rec.state, 'running')
                    rec.line_ids = []
                    with self.assertRaises(ValueError):
                        namespace['action_close'](rec)
                    self.assertEqual(rec.state, 'running')
                    rec.line_ids = [23]
                    namespace['action_close'](rec)
                    self.assertEqual(rec.state, 'closed')
                else:
                    with self.assertRaises(ValueError):
                        namespace['action_set_running'](rec)
                    self.assertEqual(rec.state, state)

    def test_policy_step_order_maps_to_native_descending_priority(self):
        method = next(n for n in ast.walk(ast.parse(POLICY.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_tier_definition_vals')
        namespace = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(POLICY), 'exec'), namespace)
        class Steps(list):
            def sorted(self, key): return Steps(sorted(self, key=key))
            @property
            def ids(self): return [step.id for step in self]
        steps = Steps(types.SimpleNamespace(id=i, sequence=seq, name=str(i), active=True,
                      approve_group_id=types.SimpleNamespace(id=7))
                      for i, seq in [(5, 20), (4, 10), (3, 10), (2, 0), (1, -10)])
        model = types.SimpleNamespace(id=12)
        company = types.SimpleNamespace(id=7)
        class Env(dict): pass
        env = Env({'ir.model': types.SimpleNamespace(sudo=lambda: types.SimpleNamespace(_get=lambda name: model))})
        env.company = company
        policy = types.SimpleNamespace(ensure_one=lambda: None, env=env, target_model='test.document',
            _tier_server_actions=lambda: (False, False), name='policy', company_id=company,
            active=True, approval_required=True, mode='linear', step_ids=steps,
            _tier_definition_domain=lambda step: '[]')
        priorities = [(step.id, namespace['_tier_definition_vals'](policy, step)['sequence']) for step in steps]
        self.assertEqual([identity for identity, priority in sorted(priorities, key=lambda row: row[1], reverse=True)], [1, 2, 3, 4, 5])

    def test_policy_sync_includes_disabled_steps_to_revoke_stale_definitions(self):
        method = next(n for n in ast.walk(ast.parse(POLICY.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'sync_tier_definitions')
        namespace = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(POLICY), 'exec'), namespace)
        updates = []
        definition = types.SimpleNamespace(sudo=lambda: types.SimpleNamespace(write=lambda values: updates.append(values)))
        disabled = types.SimpleNamespace(active=False, approve_group_id=True, tier_definition_id=definition)
        class Synced:
            def __ior__(self, other):
                return self
        class Policy:
            runtime_state = 'tier_validation'
            def __init__(self):
                self.context = {}
                self.env = {'tier.definition': types.SimpleNamespace(sudo=lambda: types.SimpleNamespace(browse=lambda: Synced()))}
            def sudo(self): return self
            def with_context(self, **values):
                self.context.update(values)
                return self
            def __iter__(self): return iter([self])
            @property
            def step_ids(self): return [disabled] if self.context.get('active_test') is False else []
            def _tier_sync_supported(self): return True
            def _tier_definition_vals(self, step): return {'active': step.active}
            def mapped(self, name): return ['test.document']
            def _sync_tier_server_action_groups(self, models): pass
        namespace['sync_tier_definitions'](Policy())
        self.assertEqual(updates, [{'active': False}])

    def test_unconfigured_submission_auto_approves_without_fabricating_reviews(self):
        rec = self.record(required=False)
        rec._route_submitted_approval()
        self.assertEqual(rec.state, 'approved')
        self.assertEqual(rec.validation_status, 'no')
        self.assertEqual(rec.requests, 0)
        self.assertEqual(rec.audits[0][3]['action_name'], 'action_submit')

    def test_configured_submission_creates_real_reviews_and_waits(self):
        rec = self.record()
        rec._route_submitted_approval()
        self.assertEqual((rec.state, rec.validation_status, rec.requests), ('submit', 'pending', 1))
        self.assertFalse(rec.audits)

    def test_enabled_policy_without_matching_rules_fails(self):
        rec = self.record(matching=False)
        with self.assertRaisesRegex(ValueError, '没有匹配'):
            rec._route_submitted_approval()
        self.assertEqual(rec.state, 'submit')

    def test_retry_restarts_previous_rejected_chain(self):
        rec = self.record(reviews=['old-tier'], status='rejected')
        rec._route_submitted_approval()
        self.assertEqual(rec.restarts, 1)
        self.assertEqual(rec.review_ids, ['real-tier'])

    def test_submission_router_cannot_run_on_an_approved_record(self):
        with self.assertRaises(ValueError):
            self.record(state='approved')._route_submitted_approval()

    def test_absent_review_never_grants_manual_approval(self):
        for method in ('action_approve', 'action_set_approved', 'action_approval_decision'):
            rec = self.record(required=False)
            with self.assertRaises(ValueError):
                getattr(rec, method)()
            self.assertEqual(rec.state, 'submit')

    def test_partial_approval_keeps_state_even_after_policy_disabled(self):
        rec = self.record(required=False, reviews=['tier1', 'tier2'], status='pending')
        rec.data['next_status'] = 'pending'
        rec.action_approval_decision()
        rec.action_on_tier_approved()
        self.assertEqual(rec.state, 'submit')

    def test_full_chain_finishes_once_through_all_compatibility_entries(self):
        rec = self.record(reviews=['tier'], status='pending')
        rec.action_approve()
        rec.action_set_approved()
        rec.action_on_tier_approved()
        self.assertEqual(rec.state, 'approved')
        self.assertEqual(len(rec.audits), 1)

    def test_wrong_reviewer_does_not_advance(self):
        rec = self.record(reviews=['tier'], status='pending')
        rec.data['can_review'] = False
        with self.assertRaises(PermissionError):
            rec.action_approval_decision()
        self.assertEqual(rec.state, 'submit')

    def test_finance_permission_still_required(self):
        rec = self.record(reviews=['tier'], status='validated')
        rec.data['authorized'] = False
        with self.assertRaises(PermissionError):
            rec.action_approval_decision()
        self.assertEqual(rec.state, 'submit')

    def test_automatic_completion_requires_private_submission_authority(self):
        rec = self.record(required=False)
        with self.assertRaises(PermissionError):
            rec._complete_payment_approval(automatic=True)
        with self.assertRaises(PermissionError):
            rec.with_context(_sc_automatic_approval_token=True)._complete_payment_approval(automatic=True)

    def test_callback_flag_does_not_bypass_incomplete_approval(self):
        rec = self.record(reviews=['tier'], status='pending')
        with self.assertRaisesRegex(ValueError, 'BYPASS_BLOCKED'):
            rec.with_context(tier_validation_callback=True).write({'state':'approved'})

    def test_approved_state_remains_authority_when_policy_changes(self):
        rec = self.record(required=False)
        rec._route_submitted_approval()
        rec.required = True
        rec.write({'state': 'done'})
        self.assertEqual(rec.state, 'done')

    def test_illegal_state_jump_is_rejected_by_existing_state_machine(self):
        with self.assertRaisesRegex(ValueError, 'ILLEGAL_TRANSITION'):
            self.record(state='draft', reviews=['tier'], status='validated').write({'state':'done'})

    def test_native_and_available_action_surfaces_share_one_approval_method(self):
        view = ROOT / 'addons/smart_construction_core/views/core/payment_request_views.xml'
        buttons = ET.parse(view).findall('.//button')
        names = [button.get('name') for button in buttons]
        self.assertEqual(names.count('action_approval_decision'), 1)
        self.assertFalse({'action_approve', 'action_set_approved', 'validate_tier'} & set(names))
        button = next(button for button in buttons if button.get('name') == 'action_approval_decision')
        self.assertIn('can_review', button.get('invisible'))
        self.assertEqual(button.get('groups'), 'smart_construction_core.group_sc_cap_finance_manager')
        source = ROOT / 'addons/smart_construction_core/handlers/payment_request_available_actions.py'
        tree = ast.parse(source.read_text())
        value = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                     and any(getattr(t, 'id', None) == '_ACTION_SPECS' for t in n.targets))
        spec = next(row for row in ast.literal_eval(value) if row['key'] == 'approve')
        self.assertEqual(spec['method'], 'action_approval_decision')
        self.assertEqual(spec['allowed_states'], {'submit', 'approve'})

    def test_completion_preserves_business_amount_guards(self):
        rec = self.record(reviews=['tier'], status='validated')
        rec._check_detail_amount_consistency = lambda: guard('AMOUNT_INVALID')
        with self.assertRaisesRegex(ValueError, 'AMOUNT_INVALID'):
            rec.action_on_tier_approved()
        self.assertEqual(rec.state, 'submit')
        self.assertFalse(rec.audits)

    def test_no_reviews_callback_does_not_approve_even_with_validated_scalar(self):
        rec = self.record(required=False, status='validated')
        rec.action_on_tier_approved()
        self.assertEqual(rec.state, 'submit')

    def producer(self):
        source = ROOT / 'addons/smart_construction_core/handlers/payment_request_available_actions.py'
        tree = ast.parse(source.read_text())
        names = {'_evaluate_prerequisites', '_authorization_for_action', '_next_state_hint'}
        methods = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in names]
        ns = {'REASON_OK': 'OK', 'REASON_BUSINESS_RULE_FAILED': 'FAILED', 'REASON_MISSING_PARAMS': 'MISSING'}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(source), 'exec'), ns)
        cls = type('Producer', (), {name: ns[name] for name in names})
        return cls()

    def test_producer_refuses_manual_approval_without_review_instance(self):
        rec = self.record(required=False)
        self.assertEqual(self.producer()._evaluate_prerequisites(rec, 'approve'), (False, 'FAILED'))

    def test_producer_requires_current_step_reviewer(self):
        rec = self.record(reviews=['tier'], status='pending')
        rec._has_finance_approve_access = lambda: True
        rec.data['can_review'] = False
        self.assertFalse(self.producer()._authorization_for_action(rec, 'approve'))
        rec.data['can_review'] = True
        self.assertTrue(self.producer()._authorization_for_action(rec, 'approve'))

    def test_submit_state_hint_consumes_company_policy(self):
        for required, expected in ((True, 'submit'), (False, 'approved')):
            rec = self.record(required=required)
            seen = []
            def next_state(model, submitted, approved, company):
                seen.append((model, company.id))
                return submitted if required else approved
            rec.policy.next_state_after_submit = next_state
            producer = self.producer()
            producer.env = rec.env
            self.assertEqual(producer._next_state_hint(rec, 'submit'), expected)
            self.assertEqual(seen, [('payment.request', 7)])

    def test_partial_review_hint_does_not_promise_final_approval(self):
        rec = self.record(reviews=['tier1', 'tier2'], status='pending')
        self.assertEqual(self.producer()._next_state_hint(rec, 'approve'), '')
        rec.data['validation_status'] = 'validated'
        self.assertEqual(self.producer()._next_state_hint(rec, 'approve'), 'approved')

    def rejecting_record(self, *, reviewer=42, sequence=1):
        review = types.SimpleNamespace(status='pending', sequence=sequence, reviewer_ids=[reviewer], comment='')
        return self.record(reviews=[review], status='pending')

    def test_rejection_records_review_reason_before_single_business_transition(self):
        rec = self.rejecting_record()
        rec.action_approval_reject(reason='  incorrect amount  ')
        self.assertEqual(rec.state, 'rejected')
        self.assertEqual(rec.review_ids[0].status, 'rejected')
        self.assertEqual(rec.review_ids[0].comment, 'incorrect amount')
        self.assertEqual(rec.audits[0][3]['reason'], 'incorrect amount')
        self.assertEqual(len(rec.audits), 1)

    def test_rejection_denies_wrong_user_or_step_even_with_stale_can_review(self):
        for kwargs in ({'reviewer': 99}, {'sequence': 2}):
            rec = self.rejecting_record(**kwargs)
            with self.assertRaises(PermissionError):
                rec.action_approval_reject(reason='denied')
            self.assertEqual(rec.review_ids[0].comment, '')
            self.assertEqual(rec.state, 'submit')

    def test_rejection_requires_reason_and_current_review_capability(self):
        rec = self.rejecting_record()
        with self.assertRaises(ValueError):
            rec.action_approval_reject(reason=' ')
        rec.data['can_review'] = False
        with self.assertRaises(PermissionError):
            rec.action_approval_reject(reason='denied')
        self.assertEqual(rec.state, 'submit')

    def test_reject_intent_targets_review_decision_instead_of_callback(self):
        path = ROOT / 'addons/smart_construction_core/handlers/payment_request_approval.py'
        cls = next(n for n in ast.parse(path.read_text()).body
                   if isinstance(n, ast.ClassDef) and n.name == 'PaymentRequestRejectHandler')
        method = next(ast.literal_eval(n.value) for n in cls.body if isinstance(n, ast.Assign)
                      and any(getattr(t, 'id', None) == 'ACTION_METHOD' for t in n.targets))
        self.assertEqual(method, 'action_approval_reject')

    def test_rejection_callback_without_rejected_chain_is_inert(self):
        rec = self.rejecting_record()
        rec.action_on_tier_rejected(reason='forged')
        self.assertEqual(rec.state, 'submit')
        self.assertFalse(rec.audits)

    def test_rejection_projection_requires_existing_pending_chain_and_reviewer(self):
        rec = self.record()
        self.assertEqual(self.producer()._evaluate_prerequisites(rec, 'reject'), (False, 'FAILED'))
        rec = self.rejecting_record()
        rec._has_finance_approve_access = lambda: True
        self.assertEqual(self.producer()._evaluate_prerequisites(rec, 'reject'), (True, 'OK'))
        rec.data['can_review'] = False
        self.assertFalse(self.producer()._authorization_for_action(rec, 'reject'))

    def test_legacy_approving_state_uses_same_completed_chain(self):
        rec = self.record(state='approve', reviews=['tier'], status='validated')
        rec.action_set_approved()
        self.assertEqual(rec.state, 'approved')


if __name__ == '__main__':
    unittest.main()
