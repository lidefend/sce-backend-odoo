#!/usr/bin/env python3
"""Execute production approval methods with isolated collaborators, without an ORM."""
import ast
import copy
import sys
import types
import unittest
from unittest.mock import patch
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

    def _write_document_state(self, values):
        return self.write(values)

    def _write_finance_authority(self, values):
        return self.write(values)

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
                    rec._write_invoice_state = lambda values: rec.data.update(values)
                    rec._write_document_state = lambda values: rec.data.update(values)
                    rec._write_finance_authority = lambda values: rec.data.update(values)
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

    def test_project_approval_does_not_start_lifecycle(self):
        path = MODEL.parent / 'project_initiation_approval.py'
        names = {'action_sc_submit', '_check_initiation_ready', '_complete_initiation_approval', 'action_on_tier_approved', '_assert_initiation_approved', 'action_sc_start'}
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in names]
        namespace = {'UserError': ValueError, '_INITIATION_APPROVAL_TOKEN': object()}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
        class Env(dict):
            user = types.SimpleNamespace(has_group=lambda group: True)
        class Project:
            name = 'Project'
            company_id = object()
            def __iter__(self): return iter([self])
            def ensure_one(self): pass
            def with_context(self, **kw): return self
            def write(self, values): self.__dict__.update(values)
            def message_post(self, **kw): self.messages.append(kw)
            def _sc_lifecycle_advisories(self, target): return []
            def action_set_lifecycle_state(self, target): self.lifecycle_state = target
        for name in names: setattr(Project, name, namespace[name])
        for configured in (True, False):
            project = Project()
            project.lifecycle_state, project.sc_approval_state = 'draft', 'draft'
            project.review_ids, project.validation_status, project.messages = [], 'no', []
            project._state_field = 'sc_approval_state'
            project.env = Env({'sc.approval.policy': types.SimpleNamespace(
                _start_submission_review=lambda rec: configured,
                _assert_submission_approved=lambda rec, states: PRODUCTION['_assert_submission_approved'](None, rec, states))})
            with self.assertRaises(ValueError): project.action_sc_start()
            project.action_sc_submit()
            self.assertEqual(project.lifecycle_state, 'draft')
            self.assertEqual(project.sc_approval_state, 'draft' if configured else 'approved')
            if configured:
                project.review_ids, project.validation_status = [1], 'pending'
                with self.assertRaises(ValueError): project.action_sc_start()
                project.action_on_tier_approved()
                self.assertEqual(project.sc_approval_state, 'draft')
                project.validation_status = 'validated'
                project.action_on_tier_approved()
            self.assertEqual(project.lifecycle_state, 'draft')
            self.assertEqual(project.sc_approval_state, 'approved')
            self.assertEqual(len(project.messages), 1)
            project.action_sc_start()
            self.assertEqual(project.lifecycle_state, 'in_progress')
            with self.assertRaises(ValueError): project.action_sc_submit()

    def test_project_document_approval_and_archival_are_separate(self):
        path = ROOT / 'addons/smart_construction_core/models/support/document_center.py'
        names = {'action_submit', 'action_on_tier_approved', 'action_archive', 'action_approve', 'action_reset_to_draft'}
        methods = [node for node in ast.walk(ast.parse(path.read_text())) if isinstance(node, ast.FunctionDef) and node.name in names]
        ns = {'UserError': ValueError}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        for configured in (False, True):
            rec = self.record(required=configured, state='draft')
            rec._name = 'sc.project.document'
            class Env(dict): context = {}
            rec.env = Env({'sc.approval.policy': rec.policy})
            rec.env.company = rec.company_id
            rec._write_approval_state = lambda values: rec.data.update(values)
            rec._check_document_operation = lambda label: None
            rec.policy._assert_submission_approved = lambda record, states: PRODUCTION['_assert_submission_approved'](rec.policy, record, states)
            rec.action_archive = lambda: ns['action_archive'](rec)
            with self.assertRaises(ValueError): ns['action_approve'](rec)
            ns['action_submit'](rec)
            self.assertEqual(rec.state, 'review' if configured else 'approved')
            if configured:
                with self.assertRaises(ValueError): ns['action_archive'](rec)
                with self.assertRaises(ValueError): ns['action_reset_to_draft'](rec)
                rec.policy._approve_submission_review(rec)
                ns['action_on_tier_approved'](rec)
                self.assertEqual(rec.state, 'approved')
            ns['action_archive'](rec)
            self.assertEqual(rec.state, 'done')
            with self.assertRaises(ValueError): ns['action_archive'](rec)
            ns['action_reset_to_draft'](rec)
            self.assertEqual(rec.state, 'draft')
            self.assertFalse(rec.review_ids)

    def test_project_document_external_state_and_reviewed_contents_are_protected(self):
        path = ROOT / 'addons/smart_construction_core/models/support/document_center.py'
        methods = [node for node in ast.walk(ast.parse(path.read_text())) if isinstance(node, ast.FunctionDef) and node.name in {'create', 'write', '_check_document_operation'}]
        for method in methods: method.decorator_list = []
        ns = {'UserError': ValueError, '_DOCUMENT_APPROVAL_TOKEN': object()}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list): pass
        rec = Rows([types.SimpleNamespace(state='approved')])
        rec.env = types.SimpleNamespace(context={'default_state': 'done'})
        with self.assertRaises(ValueError): ns['create'](rec, [{}])
        for values in ({'state': 'done'}, {'project_id': 9}, {'attachment_ids': []}, {'name': 'new content'}):
            with self.assertRaises(ValueError): ns['write'](rec, values)
        for same_company in (False, True):
            calls = []
            def project_gate(**kwargs):
                calls.append(kwargs)
                raise ValueError('project paused')
            document = types.SimpleNamespace(company_id=8, project_id=types.SimpleNamespace(company_id=8 if same_company else 9, _ensure_operation_allowed=project_gate))
            with self.assertRaises(ValueError): ns['_check_document_operation'](Rows([document]), 'Archive')
            self.assertEqual(len(calls), int(same_company))

    def test_reconciliation_adjustment_direct_state_and_origin_writes_denied(self):
        for filename in ('treasury_reconciliation', 'settlement_adjustment', 'financing_loan', 'payment_execution'):
            path = MODEL.with_name(filename + '.py')
            methods = [n for n in ast.walk(ast.parse(path.read_text()))
                       if isinstance(n, ast.FunctionDef) and n.name in {'create', 'write'}]
            for method in methods:
                method.decorator_list = []
            ns = {'UserError': ValueError, '_': lambda text: text, '_DOCUMENT_STATE_TOKEN': object()}
            exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
            class Rows(list):
                pass
            rows = Rows([types.SimpleNamespace(source_origin='manual', state='draft')])
            rows.env = types.SimpleNamespace(context={}, su=False)
            for state in ('confirmed', 'reconciled', 'cancel', 'legacy_confirmed', False):
                with self.subTest(model=filename, state=state):
                    rows.env.context = {}
                    with self.assertRaises(ValueError):
                        ns['create'](rows, [{'state': state}])
                    rows.env.context = {'default_state': state, 'sc_document_state_token': True}
                    with self.assertRaises(ValueError):
                        ns['create'](rows, [{}])
                    with self.assertRaises(ValueError):
                        ns['write'](rows, {'state': state})
            rows.env.context = {}
            with self.assertRaises(ValueError):
                ns['create'](rows, [{'source_origin': 'legacy'}])
            rows.env.context = {'default_source_origin': 'legacy'}
            with self.assertRaises(ValueError):
                ns['create'](rows, [{}])
            with self.assertRaises(ValueError):
                ns['write'](rows, {'source_origin': 'legacy'})

    def test_reconciliation_adjustment_private_state_and_import_boundary(self):
        for filename in ('treasury_reconciliation', 'settlement_adjustment', 'financing_loan', 'payment_execution'):
            path = MODEL.with_name(filename + '.py')
            methods = [n for n in ast.walk(ast.parse(path.read_text()))
                       if isinstance(n, ast.FunctionDef) and n.name in {'create', '_write_document_state'}]
            for method in methods:
                method.decorator_list = []
            token = object()
            ns = {'UserError': ValueError, '_': lambda text: text, '_DOCUMENT_STATE_TOKEN': token}
            exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
            writes = []
            def with_context(**context):
                self.assertIs(context['sc_document_state_token'], token)
                return types.SimpleNamespace(write=lambda values: writes.append(values) or True)
            record = types.SimpleNamespace(with_context=with_context)
            self.assertTrue(ns['_write_document_state'](record, {'state': 'confirmed'}))
            self.assertEqual(writes, [{'state': 'confirmed'}])
            class SequenceReached(Exception):
                pass
            class Environment:
                context = {}
                su = False
                def __getitem__(self, model):
                    if model != 'ir.sequence':
                        raise AssertionError(model)
                    raise SequenceReached()
            record.env = Environment()
            # Accepted envelopes reach ordinary creation; this is not ORM import proof.
            with self.assertRaises(SequenceReached):
                ns['create'](record, [{}])
            record.env.su = True
            with self.assertRaises(SequenceReached):
                ns['create'](record, [{'source_origin': 'legacy', 'state': 'legacy_confirmed'}])
            with self.assertRaises(ValueError):
                ns['create'](record, [{'state': 'confirmed'}])
            with self.assertRaises(ValueError):
                ns['create'](record, [{}, {'state': 'confirmed'}])

    def test_receipt_self_funding_approval_state_cannot_be_forged(self):
        for filename, context, token in (
            ('receipt_income', 'sc_receipt_fact_authority_token', '_RECEIPT_FACT_AUTHORITY_TOKEN'),
            ('self_funding_registration', 'sc_self_funding_authority_token', '_SELF_FUNDING_AUTHORITY_TOKEN'),
            ('expense_claim', 'sc_expense_fact_authority_token', '_EXPENSE_FACT_AUTHORITY_TOKEN'),
        ):
            path = MODEL.with_name(filename + '.py')
            document_class = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef))
            methods = [n for n in document_class.body
                       if isinstance(n, ast.FunctionDef) and n.name in {'create', 'write'}]
            for method in methods:
                method.decorator_list = []
            ns = {'UserError': ValueError, '_': lambda text: text, token: object()}
            exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
            record = types.SimpleNamespace(env=types.SimpleNamespace(context={}))
            for state in ('confirmed', 'received', 'done', 'cancel', 'legacy_confirmed', False):
                with self.subTest(model=filename, state=state):
                    record.env.context = {}
                    with self.assertRaises(ValueError):
                        ns['create'](record, [{'state': state}])
                    record.env.context = {'default_state': state, context: True}
                    with self.assertRaises(ValueError):
                        ns['create'](record, [{}])
                    with self.assertRaises(ValueError):
                        ns['write'](record, {'state': state})
            record.env.context = {'default_source_origin': 'legacy'}
            with self.assertRaises(ValueError):
                ns['create'](record, [{}])
            record.env.context = {}
            for values in ({'source_origin': 'legacy'}, {'finance_identity_state': 'legacy_observed_identity'}):
                with self.assertRaises(ValueError):
                    ns['write'](record, values)

    def test_self_funding_reviewed_business_content_is_frozen(self):
        path = MODEL.with_name('self_funding_registration.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'write')
        ns = {'UserError': ValueError, '_': lambda text: text, '_SELF_FUNDING_AUTHORITY_TOKEN': object()}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list):
            pass
        for state, status in (('draft', 'waiting'), ('draft', 'pending'), ('draft', 'validated'), ('confirmed', 'no'), ('confirmed', 'validated')):
            rows = Rows([types.SimpleNamespace(state=state, validation_status=status)])
            rows.env = types.SimpleNamespace(context={'sc_self_funding_authority_token': True})
            for values in ({'amount': 200}, {'project_id': 9}, {'partner_id': 9}, {'currency_id': 9},
                           {'funding_type': 'refund'}, {'payment_account_name': 'changed'},
                           {'partner_account_name': 'changed'}, {'attachment_ids': [(5, 0, 0)]}, {'active': False}):
                with self.subTest(state=state, status=status, values=values), self.assertRaises(ValueError):
                    ns['write'](rows, values)

    def test_workflow_evidence_only_describes_current_actions(self):
        path = MODEL.parents[1] / 'support/workflow_contract_service.py'
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'describe_record')
        method.decorator_list = []
        ns = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        class Row:
            _name = 'test.document'
            id = 1
            state = 'done'
            def __len__(self): return 1
        gates = [
            {'reasonCode': 'PREPARE_REQUIRED', 'actionKeys': ['submit', 'complete'], 'blocking': True},
            {'reasonCode': 'REVERSAL_REQUIRED', 'actionKeys': ['reverse'], 'blocking': True},
            {'reasonCode': 'GLOBAL_NOTICE', 'blocking': False},
        ]
        actions = [{'key': 'reverse', 'enabled': False}]
        observed = []
        service = types.SimpleNamespace(
            profile_by_model=lambda: {'test.document': {'state_field': 'state', 'state_phase': {'done': 'done'}}},
            _approval_phase=lambda *args, **kwargs: 'none', _editability=lambda *args: 'locked',
            _evidence_gate=lambda record: gates,
            _available_actions=lambda *args: observed.append(args[-1]) or actions,
            source_authority_contract=lambda: {}, _statusbar_projection=lambda *args: {},
            _declared_actions=lambda profile: [],
        )
        result = ns['describe_record'](service, Row())
        self.assertEqual(result['evidenceGate'], gates[1:])
        self.assertEqual(result['availableActions'], actions)
        self.assertIs(observed[-1], gates)  # Availability still sees all authoritative gates.
        actions[:] = [{'key': 'submit', 'enabled': False}]
        self.assertEqual(ns['describe_record'](service, Row())['evidenceGate'], [gates[0], gates[2]])
        actions.clear()
        self.assertEqual(ns['describe_record'](service, Row())['evidenceGate'], [gates[2]])

    def test_reconciliation_reviewed_and_terminal_content_is_protected(self):
        path = MODEL.with_name('treasury_reconciliation.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'write')
        token = object()
        writes = []
        ns = {'UserError': ValueError, '_': lambda text: text, '_DOCUMENT_STATE_TOKEN': token,
              'super': lambda: types.SimpleNamespace(write=lambda vals: writes.append(dict(vals)) or True)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list):
            pass
        for state, status in (('draft', 'waiting'), ('draft', 'pending'), ('draft', 'validated'), ('confirmed', 'no'), ('reconciled', 'validated')):
            rows = Rows([types.SimpleNamespace(source_origin='manual', state=state, validation_status=status)])
            rows.env = types.SimpleNamespace(context={'sc_document_state_token': True})
            for values in ({'account_balance': 200}, {'system_difference': 1}, {'treasury_ledger_id': 9},
                           {'project_id': 9}, {'currency_id': 9}, {'confirmation_amount': 200},
                           {'attachment_ids': [(5, 0, 0)]}, {'active': False}):
                with self.subTest(state=state, status=status, values=values), self.assertRaises(ValueError):
                    ns['write'](rows, values)
            self.assertTrue(ns['write'](rows, {'note': 'supplement'}))
        rows[0].state, rows[0].validation_status = 'draft', 'rejected'
        self.assertTrue(ns['write'](rows, {'system_difference': 0}))
        rows[0].state = 'confirmed'
        rows.env.context = {'sc_document_state_token': token}
        self.assertTrue(ns['write'](rows, {'state': 'reconciled'}))
        self.assertEqual(writes[-1], {'state': 'reconciled'})

    def test_reconciliation_source_errors_are_shared_with_contract(self):
        path = MODEL.with_name('treasury_reconciliation.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_reconcile_readiness_errors')
        service = MODEL.parents[1] / 'support/workflow_contract_service.py'
        gate = next(n for n in ast.walk(ast.parse(service.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_treasury_reconciliation_evidence_gate')
        gate.decorator_list = []
        ns = {'_': lambda text: text, 'float_is_zero': lambda value, precision_rounding: abs(value) < precision_rounding / 2}
        exec(compile(ast.Module(body=[method, gate], type_ignores=[]), str(path), 'exec'), ns)
        currency = types.SimpleNamespace(id=2, rounding=0.01)
        ledger = types.SimpleNamespace(state='posted', project_id=1, company_id=3, currency_id=currency)
        record = types.SimpleNamespace(ensure_one=lambda: None, project_id=1, company_id=3, currency_id=currency,
            treasury_ledger_id=ledger, system_difference=0, source_origin='manual', state='draft', validation_status='no')
        record._reconcile_readiness_errors = lambda: ns['_reconcile_readiness_errors'](record)
        presenter = types.SimpleNamespace(_gate=lambda code, message: {'code': code})
        self.assertEqual(record._reconcile_readiness_errors(), [])
        for field, bad, code in (('state', 'draft', 'NOT_POSTED'), ('project_id', 9, 'PROJECT_MISMATCH'),
                                 ('company_id', 9, 'COMPANY_MISMATCH'), ('currency_id', False, 'CURRENCY_MISMATCH')):
            old = getattr(ledger, field)
            setattr(ledger, field, bad)
            expected = 'TREASURY_RECONCILIATION_LEDGER_' + code
            self.assertIn(expected, [row[0] for row in record._reconcile_readiness_errors()])
            self.assertIn({'code': expected}, ns['_treasury_reconciliation_evidence_gate'](presenter, record))
            setattr(ledger, field, old)
        record.system_difference = 1
        self.assertIn('TREASURY_RECONCILIATION_DIFFERENCE_NOT_ZERO', [row[0] for row in record._reconcile_readiness_errors()])

    def test_settlement_adjustment_source_identity_and_contract_gate_share_errors(self):
        path = MODEL.with_name('settlement_adjustment.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_business_anchor_errors')
        service = MODEL.parents[1] / 'support/workflow_contract_service.py'
        gate = next(n for n in ast.walk(ast.parse(service.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_settlement_adjustment_evidence_gate')
        gate.decorator_list = []
        ns = {'_': lambda text: text}
        exec(compile(ast.Module(body=[method, gate], type_ignores=[]), str(path), 'exec'), ns)
        source = types.SimpleNamespace(project_id=1, currency_id=2, partner_id=3)
        settlement = types.SimpleNamespace(project_id=1, currency_id=2, partner_id=3, contract_id=source)
        record = types.SimpleNamespace(ensure_one=lambda: None, item_name='Adjustment', amount=100,
            project_id=1, currency_id=2, partner_id=3, contract_id=source, settlement_id=settlement,
            source_origin='manual', state='draft', validation_status='no')
        record._business_anchor_errors = lambda: ns['_business_anchor_errors'](record)
        presenter = types.SimpleNamespace(_gate=lambda code, message, **kw: {'code': code, **kw})
        self.assertEqual(record._business_anchor_errors(), [])
        for field, bad, code in (
            ('project_id', 9, 'PROJECT_MISMATCH'), ('currency_id', 9, 'CURRENCY_MISMATCH'),
            ('partner_id', 9, 'PARTNER_MISMATCH'),
            ('contract_id', types.SimpleNamespace(project_id=1, currency_id=2, partner_id=3, id=9), 'CONTRACT_MISMATCH'),
        ):
            old = getattr(record, field)
            setattr(record, field, bad)
            expected = 'SETTLEMENT_ADJUSTMENT_' + code
            self.assertIn(expected, [row[0] for row in record._business_anchor_errors()])
            gates = ns['_settlement_adjustment_evidence_gate'](presenter, record)
            self.assertTrue(any(row['code'] == expected and row['action_keys'] == ['submit', 'approve'] for row in gates))
            setattr(record, field, old)
        record.partner_id = False
        self.assertEqual(record._business_anchor_errors(), [])

    def test_settlement_adjustment_reviewed_economic_content_is_frozen(self):
        path = MODEL.with_name('settlement_adjustment.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'write')
        writes = []
        token = object()
        ns = {'UserError': ValueError, '_': lambda text: text, '_DOCUMENT_STATE_TOKEN': token,
              'super': lambda: types.SimpleNamespace(write=lambda vals: writes.append(dict(vals)) or True)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list):
            pass
        for state, status in (('draft', 'waiting'), ('draft', 'pending'), ('draft', 'validated'), ('confirmed', 'no')):
            rows = Rows([types.SimpleNamespace(source_origin='manual', state=state, validation_status=status)])
            rows.env = types.SimpleNamespace(context={'sc_document_state_token': True})
            for values in ({'amount': 200}, {'adjustment_type': 'addition'}, {'contract_id': 9},
                           {'settlement_id': 9}, {'project_id': 9}, {'currency_id': 9}, {'active': False}):
                with self.subTest(state=state, status=status, values=values), self.assertRaises(ValueError):
                    ns['write'](rows, values)
            self.assertTrue(ns['write'](rows, {'note': 'supplement'}))
        rows[0].state, rows[0].validation_status = 'draft', 'rejected'
        self.assertTrue(ns['write'](rows, {'amount': 200}))
        rows[0].state = 'confirmed'
        rows.env.context = {'sc_document_state_token': token}
        self.assertTrue(ns['write'](rows, {'state': 'cancel'}))
        self.assertEqual(writes[-1], {'state': 'cancel'})

    def test_unsaved_workflow_catalog_declares_meaning_without_execution_grants(self):
        path = ROOT / 'addons/smart_construction_core/models/support/workflow_contract_service.py'
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'describe_model_actions')
        method.decorator_list = []
        ns = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        declaration = {'key': 'submit', 'method': 'action_submit', 'action_semantics': {'purpose': 'submit'}}
        service = types.SimpleNamespace(profile_by_model=lambda: {'sc.expense.claim': {'state_field': 'state'}},
            _declared_actions=lambda profile: [declaration])
        catalog = ns['describe_model_actions'](service, 'sc.expense.claim')
        self.assertEqual(catalog['actions'], [declaration])
        self.assertNotIn('availableActions', catalog)
        self.assertNotIn('editability', catalog)
        self.assertNotIn('rawState', catalog)
        self.assertEqual(ns['describe_model_actions'](service, 'unsupported'), {})

    def test_expense_submission_requirement_preserves_draft_optional_attachment(self):
        path = ROOT / 'addons/smart_construction_core/models/support/workflow_contract_service.py'
        tree = ast.parse(path.read_text())
        profile_node = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                            and any(isinstance(t, ast.Name) and t.id == 'PROFILE_BY_MODEL' for t in n.targets))
        expense_profile = next(value for key, value in zip(profile_node.keys, profile_node.values)
                               if isinstance(key, ast.Constant) and key.value == 'sc.expense.claim')
        requirement = ast.literal_eval(expense_profile)['submission_requirements'][0]
        self.assertEqual(requirement['field'], 'attachment_ids')
        self.assertEqual(requirement['requiredWhen'], {'field': 'submission_attachment_policy', 'equals': 'required'})
        self.assertEqual(requirement['pendingSource'], 'native_attachment')
        view = ET.parse(ROOT / 'addons/smart_construction_core/views/core/expense_claim_views.xml')
        for form in view.findall('.//form'):
            attachment = form.find('.//field[@name="attachment_ids"]')
            if attachment is not None:
                self.assertIsNone(attachment.get('required'), 'drafts must remain saveable without attachments')
                self.assertIsNotNone(form.find('.//field[@name="submission_attachment_policy"]'))

    def test_unsaved_workflow_injection_preserves_capabilities_and_does_not_browse(self):
        path = ROOT / 'addons/smart_construction_core/core_extension.py'
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_sc_inject_workflow_contract')
        ns = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        catalog = {'model': 'sc.expense.claim', 'actions': [{'method': 'action_submit'}]}
        class Env:
            registry = {'sc.expense.claim': True}
            def __getitem__(self, name):
                self.assert_service(name)
                return types.SimpleNamespace(describe_model_actions=lambda model: catalog)
            def assert_service(self, name):
                assert name == 'sc.workflow.contract.service', 'unsaved injection must not browse or invent a record'
        status = {'globalStatus': {'effectiveRecordCapabilities': {'create': True, 'write': False}}}
        contract = {'statusContract': copy.deepcopy(status)}
        ns['_sc_inject_workflow_contract'](Env(), contract, {}, model='sc.expense.claim', view_type='form')
        self.assertEqual(contract['workflowContract'], catalog)
        self.assertEqual(contract['statusContract'], status)

    def test_expense_relation_direction_uses_execution_authority(self):
        path = MODEL.with_name('expense_claim.py')
        names = {'_expected_payment_request_type', '_compute_payment_request_types'}
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in names]
        for method in methods:
            method.decorator_list = []
        ns = {}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        for flow, expected in [('cash_out', ['pay']), ('cash_in', ['receive']),
                               ('noncash', ['pay', 'receive']), ('interfund', ['pay', 'receive']),
                               ('reference', ['pay', 'receive'])]:
            row = types.SimpleNamespace(financial_flow=flow, ensure_one=lambda: None)
            row._expected_payment_request_type = lambda: ns['_expected_payment_request_type'](row)
            ns['_compute_payment_request_types']([row])
            self.assertEqual(row.payment_request_types, expected, flow)

    def test_expense_relation_domain_exposes_native_dependency(self):
        path = MODEL.with_name('expense_claim.py')
        tree = ast.parse(path.read_text())
        field = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'payment_request_id' for t in n.targets))
        domain = next(ast.literal_eval(k.value) for k in field.keywords if k.arg == 'domain')
        self.assertEqual(eval(domain, {'__builtins__': {}}, {'project_id': 10, 'payment_request_types': ['pay'], 'submission_attachment_policy': 'required'}),
                         [('project_id', '=', 10), ('type', 'in', ['pay'])])
        root = ET.parse(ROOT / 'addons/smart_construction_core/views/core/expense_claim_views.xml')
        forms = [form for form in root.findall('.//form') if form.find('.//field[@name="payment_request_id"]') is not None]
        self.assertTrue(forms)
        for form in forms:
            dependency = form.find('.//field[@name="payment_request_types"]')
            self.assertIsNotNone(dependency)
            self.assertEqual(dependency.get('invisible'), '1')

    def test_expense_create_defaults_resolve_category_and_model_semantics(self):
        path = MODEL.with_name('expense_claim.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'default_get')
        method.decorator_list = []
        defaults = {'claim_type': 'expense', 'financial_flow': 'stale'}
        candidates = []
        ns = {'super': lambda: types.SimpleNamespace(default_get=lambda fields: dict(defaults))}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        row = types.SimpleNamespace(_context_project_id=lambda: False, _context_partner_id=lambda: False,
            _resolve_business_category_id=lambda vals: 31,
            new=lambda vals: candidates.append(vals) or {'financial_flow': 'cash_out', 'payment_anchor_policy': 'pay_request_required', 'payment_request_types': ['pay'], 'submission_attachment_policy': 'required'})
        result = ns['default_get'](row, ['business_category_id', 'financial_flow', 'payment_anchor_policy', 'payment_request_types', 'submission_attachment_policy'])
        self.assertEqual(result['business_category_id'], 31)
        self.assertEqual(result['financial_flow'], 'cash_out')
        self.assertEqual(result['payment_anchor_policy'], 'pay_request_required')
        self.assertEqual(result['payment_request_types'], ['pay'])
        self.assertEqual(result['submission_attachment_policy'], 'required')
        self.assertNotIn('financial_flow', candidates[0])
        defaults.clear()
        defaults['business_category_id'] = 42
        result = ns['default_get'](row, ['business_category_id'])
        self.assertEqual(result, {'business_category_id': 42})
        self.assertEqual(len(candidates), 1, 'no unrelated compute for a category-only default request')

    def test_expense_readiness_is_shared_by_contract_and_execution(self):
        path = MODEL.with_name('expense_claim.py')
        names = {'_business_readiness_errors', '_check_business_ready', '_check_attachment_policy_or_raise'}
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in names]
        ns = {'UserError': ValueError, '_': lambda text: text, 'float_compare': lambda a, b, **kw: (a > b) - (a < b)}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        service_path = ROOT / 'addons/smart_construction_core/models/support/workflow_contract_service.py'
        projection = next(n for n in ast.walk(ast.parse(service_path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_expense_claim_evidence_gate')
        projection.decorator_list = []
        exec(compile(ast.Module(body=[projection], type_ignores=[]), str(service_path), 'exec'), ns)
        class Record:
            ensure_one = lambda self: None
            _is_noncash_deduction_bill = lambda self: False
            _is_interfund_repayment = lambda self: False
            _business_readiness_errors = ns['_business_readiness_errors']
            _check_deposit_refund_balance_or_raise = lambda self: None
            _check_payment_request_scope_or_raise = lambda self: None
        def record(**overrides):
            row = Record()
            row.__dict__.update(dict(source_origin='manual', state='draft', finance_identity_state='normalized',
                project_id=types.SimpleNamespace(company_id=8), company_id=8, partner_id=1,
                amount=100, approved_amount=100, paid_amount=0, payment_anchor_policy='pay_request_required',
                payment_request_id=9, financial_flow='cash_out', payee_account='receiver',
                receipt_account_name='', payee='', payer_account='payer', payment_account_name='',
                business_category_id=types.SimpleNamespace(attachment_policy='required'), attachment_ids=[1]))
            row.__dict__.update(overrides)
            return row
        projection_owner = types.SimpleNamespace(_gate=lambda code, message: {'reasonCode': code, 'message': message})
        cases = [({'payment_request_id': False}, 'EXPENSE_MISSING_PAYMENT_REQUEST'),
                 ({'partner_id': False}, 'EXPENSE_MISSING_PARTNER'),
                 ({'payee_account': ''}, 'EXPENSE_MISSING_PAYEE_ACCOUNT'),
                 ({'payer_account': ''}, 'EXPENSE_MISSING_PAYER_ACCOUNT'),
                 ({'financial_flow': 'cash_in', 'payer_account': ''}, 'EXPENSE_MISSING_RECEIVING_ACCOUNT'),
                 ({'attachment_ids': []}, 'EXPENSE_ATTACHMENT_REQUIRED')]
        for changes, code in cases:
            row = record(**changes)
            errors = row._business_readiness_errors()
            with self.subTest(code=code):
                self.assertEqual([c for c, _ in errors], [code])
                gates = ns['_expense_claim_evidence_gate'](projection_owner, row)
                self.assertEqual(gates, [{'reasonCode': c, 'message': m} for c, m in errors])
                with self.assertRaisesRegex(ValueError, errors[0][1]): ns['_check_business_ready']([row])
        good = record()
        self.assertEqual(good._business_readiness_errors(), [])
        ns['_check_business_ready']([good])
        with self.assertRaises(ValueError): ns['_check_attachment_policy_or_raise'](record(attachment_ids=[]))
        ns['_check_attachment_policy_or_raise'](good)
        optional = record(business_category_id=types.SimpleNamespace(attachment_policy='optional'), attachment_ids=[])
        self.assertEqual(optional._business_readiness_errors(), [])
        legacy = record(source_origin='legacy', state='legacy_confirmed', partner_id=False, attachment_ids=[])
        self.assertEqual(legacy._business_readiness_errors(), [])

    def test_expense_reviewed_content_and_draft_recovery(self):
        path = MODEL.with_name('expense_claim.py')
        tree = ast.parse(path.read_text())
        parent = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        methods = [n for n in parent.body if isinstance(n, ast.FunctionDef)
                   and n.name in ('write', '_reviewed_content_is_frozen')]
        writes, token = [], object()
        ns = {'UserError': ValueError, '_': lambda text: text, '_EXPENSE_FACT_AUTHORITY_TOKEN': token,
              'super': lambda: types.SimpleNamespace(write=lambda vals: writes.append(dict(vals)) or True)}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        class Record:
            source_origin = 'manual'
            ensure_one = lambda self: None
            _reviewed_content_is_frozen = ns['_reviewed_content_is_frozen']
        class Rows(list):
            pass
        rec = Record()
        rows = Rows([rec])
        rows.env = types.SimpleNamespace(context={'sc_expense_fact_authority_token': True})
        for state, status in [('submit', 'pending'), ('approved', 'no'), ('done', 'validated'),
                              ('draft', 'waiting'), ('draft', 'validated')]:
            rec.state, rec.validation_status = state, status
            for vals in [{'amount': 20}, {'approved_amount': 20}, {'payment_request_id': 9},
                         {'deduction_line_ids': [(5, 0, 0)]}, {'payee_account': 'changed'},
                         {'attachment_ids': [(5, 0, 0)]}, {'active': False}]:
                with self.subTest(state=state, vals=vals), self.assertRaises(ValueError):
                    ns['write'](rows, vals)
            self.assertTrue(ns['write'](rows, {'note': 'supplement'}))
        for status in ['no', 'rejected']:
            rec.state, rec.validation_status = 'draft', status
            self.assertTrue(ns['write'](rows, {'amount': 20}))
        rec.state = 'approved'
        rows.env.context = {'sc_expense_fact_authority_token': token}
        self.assertTrue(ns['write'](rows, {'state': 'done'}))
        rec.source_origin = 'legacy'
        self.assertFalse(rec._reviewed_content_is_frozen())
        rec.state = 'legacy_confirmed'
        self.assertTrue(rec._reviewed_content_is_frozen())

    def test_expense_detail_guards_check_source_destination_and_default_parent(self):
        path = MODEL.with_name('expense_claim.py')
        tree = ast.parse(path.read_text())
        line = next(n for n in tree.body if isinstance(n, ast.ClassDef) and any(
            isinstance(m, ast.FunctionDef) and m.name == 'create' and 'default_claim_id' in ast.unparse(m)
            for m in n.body))
        methods = [n for n in line.body if isinstance(n, ast.FunctionDef) and n.name in ('create', 'write', 'unlink')]
        for method in methods:
            method.decorator_list = []
        writes = []
        ns = {'UserError': ValueError, '_': lambda text: text,
              'super': lambda: types.SimpleNamespace(create=lambda vals: writes.append(vals) or True,
                  write=lambda vals: writes.append(vals) or True, unlink=lambda: True)}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        class Claims(list):
            def exists(self): return self
            def filtered(self, predicate): return Claims(row for row in self if predicate(row))
            def __or__(self, other): return Claims([*self, *other])
        claims = {1: types.SimpleNamespace(_reviewed_content_is_frozen=lambda: False),
                  2: types.SimpleNamespace(_reviewed_content_is_frozen=lambda: True)}
        browse = lambda ids: Claims(claims[i] for i in (ids if isinstance(ids, list) else [ids]))
        class Env:
            context = {}
            def __getitem__(self, key): return types.SimpleNamespace(browse=browse)
        obj = types.SimpleNamespace(env=Env(), mapped=lambda name: Claims([claims[2]]))
        for method, args in [('create', ([{'claim_id': 2}],)), ('write', ({'amount': 3},)),
                             ('write', ({'claim_id': 1},)), ('unlink', ())]:
            with self.subTest(method=method, args=args), self.assertRaises(ValueError):
                ns[method](obj, *args)
        obj.env.context = {'default_claim_id': 2}
        with self.assertRaises(ValueError): ns['create'](obj, [{}])
        obj.mapped = lambda name: Claims([claims[1]])
        with self.assertRaises(ValueError): ns['write'](obj, {'claim_id': 2})
        obj.env.context = {}
        self.assertTrue(ns['create'](obj, [{'claim_id': 1}]))
        self.assertTrue(ns['write'](obj, {'amount': 3}))
        self.assertTrue(ns['unlink'](obj))

    def test_receipt_reviewed_economic_content_is_frozen(self):
        path = MODEL.with_name('receipt_income.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'write')
        ns = {'UserError': ValueError, '_': lambda text: text, '_RECEIPT_FACT_AUTHORITY_TOKEN': object()}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list):
            pass
        for state, status in (('draft', 'waiting'), ('draft', 'pending'), ('draft', 'validated'), ('confirmed', 'no'), ('confirmed', 'validated')):
            rows = Rows([types.SimpleNamespace(source_origin='manual', state=state, validation_status=status)])
            rows.env = types.SimpleNamespace(context={'sc_receipt_fact_authority_token': True})
            for values in ({'amount': 200}, {'project_id': 9}, {'partner_id': 9}, {'currency_id': 9},
                           {'payment_request_id': 9}, {'contract_id': 9}, {'receiving_account_no': 'changed'},
                           {'deducted_tax_amount': 10}, {'settlement_amount': 200},
                           {'attachment_ids': [(5, 0, 0)]}, {'active': False}):
                with self.subTest(state=state, status=status, values=values), self.assertRaises(ValueError):
                    ns['write'](rows, values)

    def test_receipt_content_guard_preserves_draft_notes_and_private_execution(self):
        path = MODEL.with_name('receipt_income.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'write')
        writes = []
        token = object()
        ns = {'UserError': ValueError, '_': lambda text: text, '_RECEIPT_FACT_AUTHORITY_TOKEN': token,
              'super': lambda: types.SimpleNamespace(write=lambda vals: writes.append(dict(vals)) or True)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list):
            pass
        for state, status, values, context in (
            ('draft', 'no', {'amount': 200}, {}),
            ('draft', 'rejected', {'amount': 200}, {}),
            ('confirmed', 'validated', {'note': 'supplement'}, {}),
            ('confirmed', 'validated', {'state': 'received'}, {'sc_receipt_fact_authority_token': token}),
        ):
            rows = Rows([types.SimpleNamespace(source_origin='manual', state=state, validation_status=status)])
            rows.env = types.SimpleNamespace(context=context)
            with self.subTest(state=state, status=status, values=values):
                self.assertTrue(ns['write'](rows, values))
                self.assertEqual(writes[-1], values)
        self.assertEqual(len(writes), 4)

    def test_financing_reviewed_and_completed_economic_content_is_frozen(self):
        path = MODEL.with_name('financing_loan.py')
        tree = ast.parse(path.read_text())
        constants = [n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(target, ast.Name) and target.id.startswith('FINANCING_LOAN_FORMAL_') for target in n.targets)]
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'write')
        ns = {'UserError': ValueError, '_': lambda text: text, '_DOCUMENT_STATE_TOKEN': object()}
        exec(compile(ast.Module(body=constants + [method], type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list):
            pass
        for state, status in (('draft', 'waiting'), ('draft', 'pending'), ('confirmed', 'no'), ('confirmed', 'validated'), ('done', 'no')):
            rows = Rows([types.SimpleNamespace(source_origin='manual', state=state, validation_status=status)])
            rows.env = types.SimpleNamespace(context={'sc_document_state_token': True, 'history_surface_sync': True})
            for values in ({'amount': 200}, {'financing_loan_approved_amount': '200'}, {'project_id': 9},
                           {'partner_id': 9}, {'currency_id': 9}, {'direction': 'borrowed_fund'},
                           {'loan_account': 'changed'}, {'loan_type': 'borrowing_request'}, {'active': False}):
                with self.subTest(state=state, status=status, values=values), self.assertRaises(ValueError):
                    ns['write'](rows, values)

    def test_invoice_external_terminal_state_and_red_flush_attribution_denied(self):
        path = MODEL.with_name('invoice_registration.py')
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in {'create', 'write'}]
        for method in methods: method.decorator_list = []
        ns = {'UserError': ValueError, '_': lambda value: value, '_INVOICE_STATE_TOKEN': object()}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list): pass
        rows = Rows([types.SimpleNamespace(source_origin='manual', state='confirmed', validation_status='no')])
        rows.env = types.SimpleNamespace(context={}, su=False)
        for state in ('confirmed', 'registered', 'legacy_confirmed', 'cancel', False):
            with self.assertRaises(ValueError): ns['create'](rows, [{'state': state}])
            rows.env.context = {'default_state': state, 'sc_invoice_state_token': True}
            with self.assertRaises(ValueError): ns['create'](rows, [{}])
        rows.env.context = {}
        with self.assertRaises(ValueError): ns['create'](rows, [{'source_origin': 'legacy', 'state': 'legacy_confirmed'}])
        for field in ('red_flush_adjustment_id', 'red_flush_origin_source_record_id'):
            with self.assertRaises(ValueError): ns['create'](rows, [{field: 7}])
            rows.env.context = {'default_' + field: 7}
            with self.assertRaises(ValueError): ns['create'](rows, [{}])
            rows.env.context = {}
        for values in ({'state': 'registered'}, {'source_origin': 'legacy'}, {'red_flush_adjustment_id': 4}, {'amount_total': 200}, {'invoice_no': 'replacement'}):
            with self.assertRaises(ValueError): ns['write'](rows, values)
        rows[0].state, rows[0].validation_status = 'draft', 'pending'
        with self.assertRaises(ValueError): ns['write'](rows, {'amount_total': 200})

    def test_invoice_registration_and_cancellation_keep_review_authority(self):
        path = MODEL.with_name('invoice_registration.py')
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in {'action_register', 'action_cancel'}]
        ns = {'UserError': ValueError, '_': lambda value: value}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        rec = self.record(state='draft', reviews=['actual'], status='pending')
        rec.source_origin = 'manual'
        with self.assertRaises(ValueError): ns['action_cancel'](rec)
        def denied(): raise ValueError('finance permission required')
        rec._assert_finance_register_access = denied
        with self.assertRaisesRegex(ValueError, 'finance permission required'): ns['action_register'](rec)

    def test_red_flush_generation_checks_finance_permission_before_create(self):
        path = MODEL.with_name('invoice_registration.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_create_registered_red_flush')
        method.decorator_list = []
        ns = {'UserError': ValueError, '_': lambda value: value, '_INVOICE_STATE_TOKEN': object()}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        calls = []
        def denied():
            calls.append('permission')
            raise ValueError('finance permission required')
        invoice = types.SimpleNamespace(env={'sc.approval.policy': types.SimpleNamespace(_assert_submission_approved=lambda *args: calls.append('approved'))}, _assert_finance_register_access=denied)
        adjustment = types.SimpleNamespace(ensure_one=lambda: None, _name='sc.output.invoice.adjustment', generated_invoice_id=False)
        with self.assertRaisesRegex(ValueError, 'finance permission required'):
            ns['_create_registered_red_flush'](invoice, adjustment, {})
        self.assertEqual(calls, ['approved', 'permission'])

    def test_red_flush_requires_eligible_original_invoice(self):
        path = ROOT / 'addons/smart_construction_core/models/core/output_invoice_adjustment.py'
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_original_invoice_eligibility_blocker')
        ns = {'_': lambda text: text}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        ledger = types.SimpleNamespace(active=True, adjustment_kind='normal', source_model='sc.invoice.registration')
        ledger.exists = lambda: ledger
        record = types.SimpleNamespace(ensure_one=lambda: None, original_ledger_id=ledger)
        for state in ('draft', 'confirmed', 'registered', 'legacy_confirmed', 'cancel', 'unknown', False):
            ledger.invoice_document_state = state
            blocker = ns['_original_invoice_eligibility_blocker'](record)
            self.assertEqual(blocker is None, state in ('registered', 'legacy_confirmed'))
        ledger.source_model = 'sc.receipt.invoice.line'
        self.assertIsNone(ns['_original_invoice_eligibility_blocker'](record))
        ledger.active = False
        self.assertEqual(ns['_original_invoice_eligibility_blocker'](record)['reason_code'], 'RED_FLUSH_SOURCE_UNAVAILABLE')
        ledger.active = True
        ledger.adjustment_kind = 'signed_adjustment'
        self.assertEqual(ns['_original_invoice_eligibility_blocker'](record)['reason_code'], 'RED_FLUSH_SOURCE_NOT_NORMAL')
        ledger.exists = lambda: False
        self.assertEqual(ns['_original_invoice_eligibility_blocker'](record)['reason_code'], 'RED_FLUSH_SOURCE_UNAVAILABLE')

    def test_legacy_workflow_context_requires_internal_authority(self):
        path = ROOT / 'addons/smart_construction_core/models/support/sc_workflow.py'
        tree = ast.parse(path.read_text())
        for class_name in ('ScWorkflowDef', 'ScWorkflowInstance'):
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
            method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_legacy_runtime_enabled')
            ns = {'LEGACY_WORKFLOW_RUNTIME_CONTEXT': 'allow_legacy_workflow_runtime', 'LEGACY_WORKFLOW_RUNTIME_PARAM': 'sc.workflow.legacy_runtime_enabled'}
            exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
            class Params:
                def sudo(self): return self
                def get_param(self, *args): return self.value
            params = Params()
            class Env(dict): pass
            env = Env({'ir.config_parameter': params})
            env.context = {'allow_legacy_workflow_runtime': True}
            for internal, configured in ((False, '0'), (True, '0'), (False, '1')):
                env.su, params.value = internal, configured
                self.assertEqual(ns['_legacy_runtime_enabled'](types.SimpleNamespace(env=env)), internal or configured == '1')

    def test_legacy_workflow_transitions_stop_before_mutation_when_disabled(self):
        path = ROOT / 'addons/smart_construction_core/models/support/sc_workflow.py'
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScWorkflowInstance')
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in {'action_submit', 'action_approve', 'action_reject'}]
        ns = {}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        def disabled(): raise ValueError('historical runtime disabled')
        record = types.SimpleNamespace(_require_legacy_runtime_enabled=disabled)
        for method in ('action_submit', 'action_approve', 'action_reject'):
            with self.assertRaisesRegex(ValueError, 'historical runtime disabled'): ns[method](record)

    def test_red_flush_approval_is_separate_from_generating_invoice(self):
        path = ROOT / 'addons/smart_construction_core/models/core/output_invoice_adjustment.py'
        names = {'action_submit', 'action_on_tier_approved', 'action_confirm', 'action_cancel'}
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in names]
        ns = {'UserError': ValueError, '_': lambda value: value}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        for configured in (False, True):
            rec = self.record(required=configured, state='draft')
            rec._name = 'sc.output.invoice.adjustment'
            class Env(dict): context = {}
            rec.env = Env({'sc.approval.policy': rec.policy})
            rec.env.company = rec.company_id
            rec._write_approval_state = lambda values: rec.data.update(values)
            rec._sync_original_invoice_snapshot = lambda: None
            rec._assert_original_snapshot_unchanged = lambda: None
            rec._validate_red_flush_ready = lambda: None
            rec.generated_invoice_id = False
            generated = []
            def generate():
                generated.append(rec.state)
                return types.SimpleNamespace(id=31)
            rec._create_red_flush_invoice_registration = generate
            rec.policy._assert_submission_approved = lambda record, states: PRODUCTION['_assert_submission_approved'](rec.policy, record, states)
            with self.assertRaises(ValueError): ns['action_confirm'](rec)
            ns['action_submit'](rec)
            self.assertEqual(rec.state, 'submitted' if configured else 'approved')
            self.assertEqual(generated, [])
            if configured:
                with self.assertRaises(ValueError): ns['action_confirm'](rec)
                with self.assertRaises(ValueError): ns['action_cancel'](rec)
                rec.policy._approve_submission_review(rec)
                ns['action_on_tier_approved'](rec)
            self.assertEqual(generated, [])
            ns['action_confirm'](rec)
            self.assertEqual(generated, ['approved'])
            self.assertEqual(rec.state, 'confirmed')
            for name in ('action_confirm', 'action_submit', 'action_cancel'):
                with self.assertRaises(ValueError): ns[name](rec)

    def test_red_flush_unique_identity_uses_source_record_only_after_execution(self):
        path = MODEL.with_name('output_invoice_adjustment.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_compute_confirmed_source_key')
        method.decorator_list = []
        ns = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        rows = [types.SimpleNamespace(state=state, original_source_model='sc.invoice.registration', original_source_record_id=17) for state in ('draft', 'approved', 'confirmed', 'cancel')]
        ns['_compute_confirmed_source_key'](rows)
        self.assertEqual([r.confirmed_source_key for r in rows], [False, False, 'sc.invoice.registration:17', False])
        rows[2].original_source_model = 'sc.receipt.invoice.line'
        ns['_compute_confirmed_source_key'](rows)
        self.assertEqual(rows[2].confirmed_source_key, 'sc.receipt.invoice.line:17')

    def test_red_flush_cancel_overrides_tier_review_deletion(self):
        path = MODEL.with_name('output_invoice_adjustment.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_allow_to_remove_reviews')
        ns = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        record = types.SimpleNamespace(ensure_one=lambda: None)
        self.assertFalse(ns['_allow_to_remove_reviews'](record, {'state': 'cancel'}))

    def test_red_flush_unexecuted_approval_can_cancel_without_erasing_review(self):
        path = MODEL.with_name('output_invoice_adjustment.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'action_cancel')
        ns = {'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        for status in ('validated', 'pending'):
            rec = self.record(state='approved', reviews=['approval history'], status=status)
            rec.generated_invoice_id = False
            rec._write_approval_state = lambda values: rec.data.update(values)
            if status == 'pending':
                with self.assertRaises(ValueError): ns['action_cancel'](rec)
                self.assertEqual(rec.state, 'approved')
            else:
                ns['action_cancel'](rec)
                self.assertEqual(rec.state, 'cancel')
                self.assertEqual(rec.review_ids, ['approval history'])
                self.assertEqual(rec.validation_status, 'validated')
                self.assertEqual(rec.restarts, 0)
                with self.assertRaises(ValueError): ns['action_cancel'](rec)
        rec = self.record(state='approved', reviews=['approval history'], status='validated')
        rec.generated_invoice_id = 31
        with self.assertRaises(ValueError): ns['action_cancel'](rec)

    def test_red_flush_reviewed_fields_and_external_state_are_protected(self):
        path = ROOT / 'addons/smart_construction_core/models/core/output_invoice_adjustment.py'
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in {'create', 'write'}]
        for method in methods: method.decorator_list = []
        ns = {'UserError': ValueError, '_': lambda value: value, '_RED_FLUSH_STATE_TOKEN': object()}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list): pass
        rows = Rows([types.SimpleNamespace(state='approved')])
        rows.env = types.SimpleNamespace(context={'default_state': 'confirmed'})
        with self.assertRaises(ValueError): ns['create'](rows, [{}])
        for values in ({'state': 'draft'}, {'original_invoice_amount': 99}, {'original_ledger_id': 4}, {'red_flush_invoice_no': 'changed'}, {'reason': 'changed'}):
            with self.assertRaises(ValueError): ns['write'](rows, values)

    def test_red_flush_source_change_rejects_old_approval(self):
        path = ROOT / 'addons/smart_construction_core/models/core/output_invoice_adjustment.py'
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_assert_original_snapshot_unchanged')
        ns = {'UserError': ValueError, '_': lambda value: value}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        class Snapshot(dict):
            def ensure_one(self): pass
            def __getattr__(self, key): return self[key]
        ledger = Snapshot(source_model='sc.invoice.registration', source_record_id=8, invoice_no='original', invoice_issue_company='company', invoice_party_name='partner', invoice_amount=100, amount_no_tax=90, tax_amount=10, surcharge_amount=0, project_id=1, partner_id=2, contract_id=3, currency_id=4)
        rec = Snapshot(original_source_model=ledger.source_model, original_source_record_id=8, invoice_no='original', invoice_issue_company='company', invoice_party_name='partner', original_invoice_amount=100, original_amount_no_tax=90, original_tax_amount=10, original_surcharge_amount=0, project_id=1, partner_id=2, contract_id=3, currency_id=4, original_ledger_id=ledger)
        rec['_original_source_record'] = lambda source: None
        ns['_assert_original_snapshot_unchanged'](rec)
        for field, value in (('invoice_amount', 200), ('project_id', 9), ('invoice_no', 'different')):
            old = ledger[field]
            ledger[field] = value
            with self.assertRaises(ValueError): ns['_assert_original_snapshot_unchanged'](rec)
            ledger[field] = old

    def test_guarantee_approval_never_posts_until_explicit_confirmation(self):
        path = ROOT / 'addons/smart_construction_core/models/support/tender.py'
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'TenderGuarantee')
        names = {'action_submit', 'action_on_tier_approved', 'action_confirm', 'action_cancel', 'action_reset_draft'}
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        ns = {'UserError': ValueError, '_': lambda value: value}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        for configured in (False, True):
            rec = self.record(required=configured, state='draft')
            rec._name = 'tender.guarantee'
            class Env(dict): context = {}
            rec.env = Env({'sc.approval.policy': rec.policy})
            rec.env.company = rec.company_id
            rec._write_finance_authority = lambda values: rec.data.update(values)
            rec._check_submission_identity = lambda: None
            posted = []
            rec._ensure_treasury_ledger = lambda: posted.append(rec.state)
            rec.policy._assert_submission_approved = lambda record, states: PRODUCTION['_assert_submission_approved'](rec.policy, record, states)
            with self.assertRaises(ValueError): ns['action_confirm'](rec)
            ns['action_submit'](rec)
            self.assertEqual(rec.state, 'submitted' if configured else 'approved')
            self.assertEqual(posted, [])
            if configured:
                for name in ('action_confirm', 'action_cancel', 'action_reset_draft'):
                    with self.assertRaises(ValueError): ns[name](rec)
                rec.policy._approve_submission_review(rec)
                ns['action_on_tier_approved'](rec)
            self.assertEqual(rec.state, 'approved')
            self.assertEqual(posted, [])
            ns['action_confirm'](rec)
            self.assertEqual(posted, ['confirmed'])
            for name in ('action_submit', 'action_confirm', 'action_cancel', 'action_reset_draft'):
                with self.assertRaises(ValueError): ns[name](rec)

    def test_guarantee_external_state_and_reviewed_cash_are_protected(self):
        path = ROOT / 'addons/smart_construction_core/models/support/tender.py'
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'TenderGuarantee')
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in {'create', 'write', '_check_submission_identity'}]
        for method in methods: method.decorator_list = []
        ns = {'UserError': ValueError, 'ValidationError': ValueError, '_': lambda value: value, '_TENDER_GUARANTEE_AUTHORITY_TOKEN': object()}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list): pass
        rows = Rows([types.SimpleNamespace(state='approved')])
        rows.env = types.SimpleNamespace(context={})
        for state in ('submitted', 'approved', 'confirmed', 'cancel', False):
            with self.assertRaises(ValueError): ns['create'](rows, [{'state': state}])
            rows.env.context = {'default_state': state}
            with self.assertRaises(ValueError): ns['create'](rows, [{}])
        rows.env.context = {'sc_tender_guarantee_authority_token': True}
        for state in ('submitted', 'approved', 'confirmed'):
            rows[0].state = state
            for values in ({'state': 'draft'}, {'amount': 999}, {'bid_id': 7}, {'bank_account_id': 3}):
                with self.assertRaises(ValueError): ns['write'](rows, values)
        for amount in (0, -1):
            with self.assertRaises(ValueError): ns['_check_submission_identity']([types.SimpleNamespace(date=True, amount=amount)])

    def test_tender_purchase_submission_uses_shared_approval(self):
        path = ROOT / 'addons/smart_construction_core/models/support/tender.py'
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'TenderDocPurchase')
        names = {'action_submit', 'action_approve', 'action_on_tier_approved', 'action_reset_draft'}
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        ns = {'UserError': ValueError}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        for configured in (False, True):
            rec = self.record(required=configured, state='draft')
            rec._name = 'tender.doc.purchase'
            class Env(dict):
                context = {}
            rec.env = Env({'sc.approval.policy': rec.policy})
            rec.env.company = rec.company_id
            rec._write_approval_state = lambda vals: rec.data.update(vals)
            rec._processing_notification = lambda title: True
            ns['action_submit'](rec)
            self.assertEqual(rec.state, 'submitted' if configured else 'approved')
            if configured:
                rec.policy.is_approval_required = lambda *args: self.fail('approval must use existing review')
                ns['action_approve'](rec)
                ns['action_on_tier_approved'](rec)
                self.assertEqual(rec.state, 'approved')
            with self.assertRaises(ValueError): ns['action_submit'](rec)
            with self.assertRaises(ValueError): ns['action_reset_draft'](rec)

    def test_tender_purchase_external_state_and_approved_amount_are_protected(self):
        path = ROOT / 'addons/smart_construction_core/models/support/tender.py'
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'TenderDocPurchase')
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in {'create', 'write'}]
        for method in methods: method.decorator_list = []
        ns = {'UserError': ValueError, '_TENDER_PURCHASE_APPROVAL_TOKEN': object()}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list): pass
        rec = Rows([types.SimpleNamespace(state='approved')])
        rec.env = types.SimpleNamespace(context={})
        with self.assertRaises(ValueError): ns['write'](rec, {'state': 'draft'})
        with self.assertRaises(ValueError): ns['write'](rec, {'amount': 1000})
        with self.assertRaises(ValueError): ns['write'](rec, {'bid_id': 7})
        with self.assertRaises(ValueError): ns['create'](rec, [{'state': 'approved'}])
        rec.env.context = {'default_state': 'approved'}
        with self.assertRaises(ValueError): ns['create'](rec, [{}])

    def test_project_approval_state_cannot_be_written_with_boolean_context(self):
        path = MODEL.parent / 'project_initiation_approval.py'
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in ('write', 'create')]
        for method in methods: method.decorator_list = []
        token = object()
        namespace = {'UserError': ValueError, '_INITIATION_APPROVAL_TOKEN': token}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
        for supplied in (None, True, 'true', object()):
            record = types.SimpleNamespace(env=types.SimpleNamespace(context={'sc_initiation_approval_token': supplied}))
            with self.assertRaises(ValueError): namespace['write'](record, {'sc_approval_state': 'approved'})
            with self.assertRaises(ValueError): namespace['create'](record, [{'sc_approval_state': 'approved'}])
        for default_state in ('approved', 'unknown', False):
            record = types.SimpleNamespace(env=types.SimpleNamespace(context={'default_sc_approval_state': default_state}))
            with self.assertRaises(ValueError): namespace['create'](record, [{'name': 'Unsubmitted project'}])
            with self.assertRaises(ValueError): namespace['create'](record, [{'sc_approval_state': 'draft'}, {'name': 'Unsubmitted project'}])

    def test_project_central_lifecycle_guard_prevents_draft_pause_bypass(self):
        path = MODEL.parent / 'project_core.py'
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_validate_lifecycle_transition')
        namespace = {'ScStateMachine': types.SimpleNamespace(PROJECT='project.project', assert_transition=lambda *a, **kw: None)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        checks = []
        class Project:
            display_name = 'project'
            def __iter__(self): return iter([self])
            def _assert_initiation_approved(self):
                checks.append(self.lifecycle_state)
                raise ValueError('approval required')
            def _guard_project_close_by_settlement(self, state): pass
            def _guard_project_close_by_payment(self, state): pass
        project = Project()
        for current, target, requires in [('draft', 'in_progress', True), ('draft', 'paused', True), ('draft', 'closed', False), ('paused', 'in_progress', False), ('in_progress', 'done', False)]:
            project.lifecycle_state = current
            if requires:
                with self.assertRaises(ValueError): namespace['_validate_lifecycle_transition'](project, target)
            else: namespace['_validate_lifecycle_transition'](project, target)
        self.assertEqual(checks, ['draft', 'draft'])

    def test_unmapped_approval_amount_constraints_are_not_ignored(self):
        method = next(n for n in ast.walk(ast.parse(POLICY.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_tier_definition_domain')
        namespace = {'ValidationError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(POLICY), 'exec'), namespace)
        policy = types.SimpleNamespace(target_model='project.project')
        for lower, upper in [(100, 0), (0, 100)]:
            with self.assertRaisesRegex(ValueError, '金额字段'):
                namespace['_tier_definition_domain'](policy, types.SimpleNamespace(amount_min=lower, amount_max=upper))
        self.assertEqual(namespace['_tier_definition_domain'](policy, types.SimpleNamespace(amount_min=0, amount_max=0)), '[]')

    def test_execution_approval_block_response_keeps_business_message(self):
        path = ROOT / 'addons/smart_construction_core/services/project_execution_response_builder.py'
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'blocked')
        method.decorator_list = []
        import typing
        namespace = {'Dict': typing.Dict, 'Any': typing.Any}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        cls = types.SimpleNamespace(_meta=lambda **kw: {})
        for code, phrase in [('EXECUTION_TASK_APPROVAL_REQUIRED', '提交'), ('EXECUTION_TASK_APPROVAL_PENDING', '审批进度')]:
            response = namespace['blocked'](cls, intent='project.execution.advance', ts0=0, trace_id='test',
                project_id=7, from_state='ready', to_state='ready', reason_code=code, extra_data={'task_id': 42})
            self.assertTrue(response['ok'])
            self.assertEqual(response['data']['result'], 'blocked')
            self.assertIn(phrase, response['data']['message'])
            self.assertEqual(response['data']['task_id'], 42)
            self.assertEqual(response['data']['from_state'], response['data']['to_state'])

    def test_task_configuration_routes_readiness_without_starting_execution(self):
        path = POLICY.parent / 'task_extend.py'
        names = {'action_prepare_task', '_complete_task_approval', 'action_on_tier_approved', '_execution_approval_block'}
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in names]
        namespace = {'raise_guard': guard}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
        class Task:
            _name = 'project.task'
            display_name = 'task'
            company_id = object()
            def __iter__(self): return iter([self])
            def ensure_one(self): pass
            def with_context(self, **kw): return self
            def write(self, values): self.__dict__.update(values)
            def _check_approval_readiness(self):
                if not self.ready: raise ValueError('not ready')
            def _audit_transition(self, *args, **kw): self.audits.append(args)
        for name in names: setattr(Task, name, namespace[name])
        for configured in (True, False):
            task = Task()
            task.sc_state, task.ready, task.audits = 'draft', True, []
            task.review_ids, task.validation_status = [], 'no'
            policy = types.SimpleNamespace(_start_submission_review=lambda rec: configured,
                is_approval_required=lambda *args, **kw: configured)
            task.env = {'sc.approval.policy': policy}
            self.assertEqual(task._execution_approval_block(), 'EXECUTION_TASK_APPROVAL_REQUIRED' if configured else False)
            task.action_prepare_task()
            self.assertEqual(task.sc_state, 'draft' if configured else 'ready')
            if configured:
                task.review_ids, task.validation_status = [1], 'pending'
                self.assertEqual(task._execution_approval_block(), 'EXECUTION_TASK_APPROVAL_PENDING')
                task.action_on_tier_approved()
                self.assertEqual(task.sc_state, 'draft')
                task.validation_status = 'validated'
                task.action_on_tier_approved()
            self.assertEqual(task.sc_state, 'ready')
            self.assertFalse(task._execution_approval_block())
            self.assertEqual(len(task.audits), 1)
            task.sc_state, task.ready = 'draft', False
            with self.assertRaises(ValueError): task.action_prepare_task()
            self.assertEqual(task.sc_state, 'draft')

    def test_task_execution_reports_actual_transitions_only(self):
        path = ROOT / 'addons/smart_construction_core/services/project_execution_task_transition_service.py'
        names = {'_prepare_task_for_execution', '_complete_task_for_execution', '_recover_task_for_ready'}
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in names]
        import typing
        namespace = {'Tuple': typing.Tuple, 'Dict': typing.Dict, 'Any': typing.Any,
                     'ProjectExecutionStateMachine': types.SimpleNamespace(normalize_task_state=lambda value: value),
                     'ProjectTaskStateSupport': types.SimpleNamespace(sync_kanban_state=lambda task: None)}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
        class Task:
            id = 42
            def __getitem__(self, key): return self
        for operation, initial, target, action in (
            ('_prepare_task_for_execution', 'draft', 'in_progress', 'action_start_task'),
            ('_complete_task_for_execution', 'in_progress', 'done', 'action_mark_done'),
            ('_recover_task_for_ready', 'draft', 'ready', 'action_prepare_task'),
        ):
            for advances in (True, False):
                task = Task()
                task.sc_state = initial
                calls = []
                task.action_prepare_task = lambda: setattr(task, 'sc_state', 'ready' if advances else initial)
                def transition():
                    calls.append(action)
                    if advances: task.sc_state = target
                if action != 'action_prepare_task': setattr(task, action, transition)
                service = types.SimpleNamespace(
                    _actionable_open_task=lambda *args, **kw: task,
                    _project_tasks=lambda *args, **kw: task,
                    _task_telemetry=lambda record, **kw: kw,
                    _log_exception=lambda *args, **kw: None)
                success, code, telemetry = namespace[operation](service, types.SimpleNamespace(id=7), task_id=42)
                self.assertEqual(success, advances, (operation, code))
                self.assertEqual(telemetry['after_state'], target if advances else initial)
                if not advances:
                    self.assertTrue(code.endswith('_FAILED'))
                    if operation == '_prepare_task_for_execution': self.assertEqual(calls, [])

    def test_execution_uses_declared_tier_state_field(self):
        # Odoo task.state is independent of the construction task sc_state.
        # A contradictory conventional state must never grant or deny execution.
        for field_name, approved in (('sc_state', 'ready'), ('lifecycle_state', 'approved')):
            for actual, conventional, reviews, status, allowed in (
                ('draft', 'confirmed', [], 'no', False),
                (approved, 'draft', [], 'no', True),
                (approved, 'draft', ['tier'], 'validated', True),
                (approved, 'confirmed', ['tier'], 'pending', False),
                (approved, 'confirmed', ['tier'], 'rejected', False),
            ):
                with self.subTest(field=field_name, actual=actual, status=status):
                    record = types.SimpleNamespace(
                        _state_field=field_name, state=conventional,
                        review_ids=reviews, validation_status=status, ensure_one=lambda: None)
                    setattr(record, field_name, actual)
                    call = lambda: PRODUCTION['_assert_submission_approved'](None, record, (approved,))
                    if allowed:
                        self.assertTrue(call())
                    else:
                        with self.assertRaises(ValueError): call()

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
                        rec._write_invoice_state = lambda values: rec.data.update(values)
                        rec._write_document_state = lambda values: rec.data.update(values)
                        rec._write_finance_authority = lambda values: rec.data.update(values)
                        rec._audit_transition = lambda *args, **kw: rec.audits.append((args, kw))
                        rec._check_business_anchor = lambda: None
                        rec._check_reconcile_ready = lambda: None
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

    def test_material_acceptance_approval_does_not_decide_quality_outcome(self):
        path = MODEL.with_name('material_acceptance.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScMaterialAcceptance')
        names = {'action_submit', 'action_accept', 'action_reject', 'action_on_tier_approved', 'action_on_tier_rejected', 'write'}
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        ns = {'ValidationError': ValueError, 'UserError': ValueError, '_': lambda text: text, '_ACCEPTANCE_STATE_TOKEN': object()}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        for required in (False, True):
            rec = self.record(required=required, state='draft')
            rec._name, rec.id = 'sc.material.acceptance', 23
            checks = []
            rec.line_ids = types.SimpleNamespace(_check_quantities=lambda: checks.append('quantities'))
            rec._sc_require_material_user = rec._sc_require_material_manager = lambda label: None
            def require_state(states, label):
                if rec.state not in states:
                    raise ValueError('wrong state')
            rec._sc_require_state = require_state
            rec._sc_material_audit_payload = lambda: {'state': rec.state}
            rec._sc_warn_system_defaults_on_action = lambda label: None
            rec._write_acceptance_state = lambda values: rec.data.update(values)
            rec._sc_audit_material_transition = lambda *args, **kw: rec.audits.append((args, kw))
            rec.policy._assert_submission_approved = lambda record, states: PRODUCTION['_assert_submission_approved'](rec.policy, record, states)
            for token in (None, True, 'trusted'):
                with self.assertRaises(ValueError):
                    ns['write'](rec.with_context(sc_acceptance_state_token=token), {'state': 'accepted'})
            ns['action_submit'](rec)
            self.assertEqual(rec.state, 'submitted' if required else 'approved')
            self.assertFalse(checks)
            if required:
                for method in ('action_accept', 'action_reject'):
                    with self.assertRaises(ValueError): ns[method](rec)
                rec.data['validation_status'] = 'validated'
                ns['action_on_tier_approved'](rec)
                self.assertEqual(rec.state, 'approved')
            ns['action_accept'](rec)
            self.assertEqual(rec.state, 'accepted')
            self.assertEqual(checks, ['quantities'])
            # Test the independent negative quality outcome from an approved
            # document; rejection still requires its own business reason.
            rec.data['state'] = 'approved'
            rec.rejection_reason = False
            with self.assertRaises(ValueError): ns['action_reject'](rec)
            rec.rejection_reason = 'quality mismatch'
            ns['action_reject'](rec)
            self.assertEqual(rec.state, 'rejected')
            self.assertFalse(rec.data.get('reject_reason'))

    def test_rfq_approval_is_separate_from_quote_selection(self):
        path = MODEL.with_name('material_acceptance.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScMaterialRfq')
        names = {'action_submit', 'action_select', 'action_on_tier_approved', 'write'}
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        ns = {'ValidationError': ValueError, 'UserError': ValueError, '_': lambda text: text, '_RFQ_STATE_TOKEN': object()}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        for required in (False, True):
            rec = self._purchase_request_record(required=required, state='draft')
            rec._name = 'sc.material.rfq'
            selected = []
            rec.line_ids = types.SimpleNamespace(_check_values=lambda: None, filtered=lambda field: selected)
            rec._sc_require_purchase_user = rec._sc_require_purchase_manager = lambda label: None
            rec._write_rfq_state = lambda values: rec.data.update(values)
            for token in (None, True, 'trusted'):
                with self.assertRaises(ValueError):
                    ns['write'](rec.with_context(sc_rfq_state_token=token), {'state': 'selected'})
            ns['action_submit'](rec)
            self.assertEqual(rec.state, 'submitted' if required else 'approved')
            if required:
                with self.assertRaises(ValueError): ns['action_select'](rec)
                ns['action_on_tier_approved'](rec)
                self.assertEqual(rec.state, 'submitted')
                rec.data['validation_status'] = 'validated'
                ns['action_on_tier_approved'](rec)
            self.assertEqual(rec.state, 'approved')
            with self.assertRaisesRegex(ValueError, '至少一条报价'): ns['action_select'](rec)
            selected.append(types.SimpleNamespace(supplier_id=types.SimpleNamespace(id=9)))
            ns['action_select'](rec)
            self.assertEqual(rec.state, 'selected')
            self.assertEqual(rec.selected_supplier_id, 9)

    def test_rfq_order_generation_requires_selection_and_review_facts(self):
        path = MODEL.with_name('material_acceptance.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScMaterialRfq')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'action_create_purchase_order')
        ns = {'ValidationError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        for state in ('draft', 'submitted', 'approved', 'selected'):
            rec = self._purchase_request_record(state=state, reviews=['pending-review'], status='pending')
            rec._name = 'sc.material.rfq'
            rec._sc_require_purchase_manager = lambda label: None
            rec.env = {'purchase.order': None, 'sc.approval.policy': rec.policy}
            # No downstream collaborator is provided: reaching generation would
            # fail for an unexpected reason instead of satisfying this assertion.
            with self.assertRaises(ValueError): ns['action_create_purchase_order'](rec)

    def test_material_settlement_approval_does_not_post_cost_or_create_payment(self):
        path = MODEL.with_name('material_acceptance.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScMaterialSettlement')
        names = {'action_submit', 'action_confirm', 'action_on_tier_approved'}
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        ns = {'ValidationError': ValueError, 'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        for required in (False, True):
            rec = self._purchase_request_record(required=required, state='draft')
            rec._name = 'sc.material.settlement'
            rec.line_ids = types.SimpleNamespace(_check_values=lambda: None)
            rec._sc_require_material_manager = lambda label: None
            rec._write_cost_source_state = lambda values: rec.data.update(values)
            downstream = []
            rec._sync_downstream_after_confirm = lambda: downstream.append('cost-and-payment')
            ns['action_submit'](rec)
            self.assertEqual(rec.state, 'submitted' if required else 'approved')
            self.assertFalse(downstream)
            if required:
                with self.assertRaises(ValueError): ns['action_confirm'](rec)
                ns['action_on_tier_approved'](rec)
                self.assertEqual(rec.state, 'submitted')
                rec.data['validation_status'] = 'validated'
                ns['action_on_tier_approved'](rec)
            self.assertEqual(rec.state, 'approved')
            self.assertFalse(downstream)
            ns['action_confirm'](rec)
            self.assertEqual(rec.state, 'confirmed')
            self.assertEqual(downstream, ['cost-and-payment'])

    def test_material_settlement_approved_facts_and_lines_remain_immutable(self):
        path = MODEL.with_name('material_acceptance.py')
        tree = ast.parse(path.read_text())
        for cls_name, field in [('ScMaterialSettlement', 'project_id'), ('ScMaterialSettlementLine', 'qty')]:
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls_name)
            methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('write', 'unlink')]
            ns = {'UserError': ValueError, '_': lambda text: text}
            exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
            for state in ('submitted', 'approved', 'confirmed'):
                rec = types.SimpleNamespace(state=state, settlement_id=types.SimpleNamespace(state=state), _FACT_IMMUTABLE_FIELDS={field})
                rec.filtered = lambda predicate: [rec] if predicate(rec) else []
                with self.assertRaises(ValueError): ns['write'](rec, {field: 99})
                with self.assertRaises(ValueError): ns['unlink'](rec)

    def test_equipment_plan_and_request_use_shared_review_decisions(self):
        path = MODEL.with_name('equipment_management.py')
        tree = ast.parse(path.read_text())
        for cls_name, model in [('ScEquipmentPlan', 'sc.equipment.plan'), ('ScEquipmentRequest', 'sc.equipment.request')]:
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls_name)
            names = {'action_submit', 'action_approve', 'action_on_tier_approved', 'write'}
            methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
            ns = {'ValidationError': ValueError, 'UserError': ValueError, '_': lambda text: text, '_EQUIPMENT_APPROVAL_STATE_TOKEN': object()}
            exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
            for required in (False, True):
                rec = self._purchase_request_record(required=required, state='draft')
                rec._name = model
                rec.line_ids = types.SimpleNamespace(_check_values=lambda: None)
                anchors = []
                rec._check_business_anchor = lambda: anchors.append('checked')
                rec._write_approval_state = lambda values: rec.data.update(values)
                for token in (None, True, 'trusted'):
                    with self.assertRaises(ValueError):
                        ns['write'](rec.with_context(sc_equipment_approval_state_token=token), {'state': 'approved'})
                ns['action_submit'](rec)
                self.assertEqual(rec.state, 'submitted' if required else 'approved')
                if model == 'sc.equipment.request': self.assertEqual(anchors, ['checked'])
                if required:
                    ns['action_on_tier_approved'](rec)
                    self.assertEqual(rec.state, 'submitted')
                    wizard = {'type': 'ir.actions.act_window'}
                    rec.validate_tier = lambda: wizard
                    self.assertIs(ns['action_approve'](rec), wizard)
                    self.assertEqual(rec.state, 'submitted')
                    rec.data['validation_status'] = 'validated'
                    ns['action_on_tier_approved'](rec)
                    self.assertEqual(rec.state, 'approved')

    def test_equipment_usage_and_settlement_approval_preserve_explicit_confirmation(self):
        path = MODEL.with_name('equipment_management.py')
        tree = ast.parse(path.read_text())
        for cls_name, model, writer in [('ScEquipmentUsage', 'sc.equipment.usage', '_write_cost_source_state'), ('ScEquipmentSettlement', 'sc.equipment.settlement', '_write_approval_state')]:
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls_name)
            names = {'action_submit', 'action_confirm', 'action_on_tier_approved'}
            methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
            ns = {'ValidationError': ValueError, 'UserError': ValueError, '_': lambda text: text}
            exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
            for required in (False, True):
                rec = self._purchase_request_record(required=required, state='draft')
                rec._name = model
                rec.line_ids = types.SimpleNamespace(_check_values=lambda: None)
                checks = []
                rec._check_business_anchor = lambda: checks.append('anchor')
                rec._check_values = lambda: checks.append('values')
                rec._check_project_operator = lambda: checks.append('operator')
                rec._check_project_manager = lambda: checks.append('manager')
                setattr(rec, writer, lambda values: rec.data.update(values))
                costs = []
                rec._sync_project_cost_ledger = lambda: costs.append('posted')
                ns['action_submit'](rec)
                self.assertEqual(rec.state, 'submitted' if required else 'approved')
                self.assertFalse(costs)
                if required:
                    with self.assertRaises(ValueError): ns['action_confirm'](rec)
                    ns['action_on_tier_approved'](rec)
                    self.assertEqual(rec.state, 'submitted')
                    rec.data['validation_status'] = 'validated'
                    ns['action_on_tier_approved'](rec)
                self.assertEqual(rec.state, 'approved')
                self.assertFalse(costs)
                ns['action_confirm'](rec)
                self.assertEqual(rec.state, 'confirmed')
                self.assertEqual(costs, ['posted'] if model.endswith('usage') else [])
                self.assertIn('anchor', checks)
                if model.endswith('usage'):
                    self.assertIn('operator', checks)
                    self.assertIn('manager', checks)

    def test_equipment_usage_approved_cancel_keeps_manager_gate(self):
        path = MODEL.with_name('equipment_management.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScEquipmentUsage')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'action_cancel')
        ns = {'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        rec = self._purchase_request_record(state='approved')
        rec._check_project_operator = lambda: None
        rec._check_project_manager = lambda: (_ for _ in ()).throw(PermissionError('manager required'))
        rec._write_cost_source_state = lambda values: rec.data.update(values)
        with self.assertRaises(PermissionError): ns['action_cancel'](rec)
        self.assertEqual(rec.state, 'approved')

    def test_labor_plan_and_request_review_and_transition_boundaries(self):
        path = MODEL.with_name('labor_management.py')
        tree = ast.parse(path.read_text())
        for cls_name, model in [('ScLaborPlan', 'sc.labor.plan'), ('ScLaborRequest', 'sc.labor.request'), ('ScMaterialRentalPlan', 'sc.material.rental.plan'), ('ScSafetyPlan', 'sc.safety.plan'), ('ScSafetyDisclosure', 'sc.safety.disclosure'), ('ScSubcontractPlan', 'sc.subcontract.plan'), ('ScSubcontractRequest', 'sc.subcontract.request')]:
            path = MODEL.with_name('subcontract_management.py' if model.startswith('sc.subcontract.') else 'safety_management.py' if model.startswith('sc.safety.') else 'material_rental.py' if model == 'sc.material.rental.plan' else 'labor_management.py')
            tree = ast.parse(path.read_text())
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls_name)
            names = {'action_submit', 'action_approve', 'action_cancel', 'action_reset_draft', 'action_on_tier_approved', 'write'}
            methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
            ns = {'ValidationError': ValueError, 'UserError': ValueError, '_': lambda text: text, '_LABOR_APPROVAL_STATE_TOKEN': object(), '_RENTAL_APPROVAL_STATE_TOKEN': object(), '_SAFETY_APPROVAL_STATE_TOKEN': object(), '_SUBCONTRACT_APPROVAL_STATE_TOKEN': object()}
            exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
            for required in (False, True):
                rec = self._purchase_request_record(required=required, state='draft')
                rec._name = model
                rec.line_ids = types.SimpleNamespace(_check_values=lambda: None)
                rec._check_business_anchor = lambda: None
                rec._write_approval_state = lambda values: rec.data.update(values)
                for token in (None, True, 'trusted'):
                    with self.assertRaises(ValueError):
                        ns['write'](rec.with_context(**{('sc_rental_approval_state_token' if model == 'sc.material.rental.plan' else 'sc_labor_approval_state_token'): token}), {'state': 'approved'})
                ns['action_submit'](rec)
                self.assertEqual(rec.state, 'submitted' if required else 'approved')
                if required:
                    ns['action_on_tier_approved'](rec)
                    self.assertEqual(rec.state, 'submitted')
                    wizard = {'type': 'ir.actions.act_window'}
                    rec.validate_tier = lambda: wizard
                    self.assertIs(ns['action_approve'](rec), wizard)
                    rec.data['validation_status'] = 'validated'
                    ns['action_on_tier_approved'](rec)
                self.assertEqual(rec.state, 'approved')
                for method in ('action_submit', 'action_cancel', 'action_reset_draft'):
                    with self.assertRaises(ValueError): ns[method](rec)
                self.assertEqual(rec.state, 'approved')
            rec = self._purchase_request_record(state='draft')
            rec._write_approval_state = lambda values: rec.data.update(values)
            ns['action_cancel'](rec)
            self.assertEqual(rec.state, 'cancel')
            ns['action_reset_draft'](rec)
            self.assertEqual(rec.state, 'draft')

    def _subcontract_payment_basis(self, **changes):
        tree = ast.parse(MODEL.read_text())
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_check_subcontract_settlement_consistency')
        method.decorator_list = []
        ns = {'ValidationError': ValueError, '_': lambda text: text}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(MODEL), 'exec'), ns)
        source = types.SimpleNamespace(state='confirmed', project_id=11, company_id=12, subcontractor_id=13, currency_id=14, contract_id=15)
        lines = changes.pop('lines', [])
        record = types.SimpleNamespace(subcontract_settlement_id=source, rental_settlement_id=False, type='pay', project_id=11, company_id=12, partner_id=13, currency_id=14, contract_id=15, settlement_id=False, material_settlement_id=False, outflow_line_ids=types.SimpleNamespace(filtered=lambda predicate: list(filter(predicate, lines))))
        record.__dict__.update(changes)
        return record, lambda: ns['_check_subcontract_settlement_consistency']([record])

    def test_subcontract_payment_basis_rejects_identity_mismatch(self):
        for field, value in [('type', 'receive'), ('project_id', 99), ('company_id', 99), ('partner_id', 99), ('currency_id', 99), ('contract_id', 99), ('partner_id', False), ('currency_id', False)]:
            with self.subTest(field=field, value=value):
                record, validate = self._subcontract_payment_basis(**{field: value})
                with self.assertRaises(ValueError): validate()
        for state in ('draft', 'submitted', 'approved', 'cancel'):
            record, validate = self._subcontract_payment_basis()
            record.subcontract_settlement_id.state = state
            with self.assertRaises(ValueError): validate()

    def test_subcontract_payment_basis_prevents_duplicate_obligation_claim(self):
        for field in ('settlement_id', 'material_settlement_id', 'rental_settlement_id'):
            record, validate = self._subcontract_payment_basis(**{field: 17})
            with self.assertRaises(ValueError): validate()
        for line in [types.SimpleNamespace(settlement_id=17, settlement_line_id=False, contract_id=15), types.SimpleNamespace(settlement_id=False, settlement_line_id=18, contract_id=15), types.SimpleNamespace(settlement_id=False, settlement_line_id=False, contract_id=99)]:
            record, validate = self._subcontract_payment_basis(lines=[line])
            with self.assertRaises(ValueError): validate()

    def test_subcontract_payment_basis_accepts_same_source_multiple_requests(self):
        record, validate = self._subcontract_payment_basis(lines=[types.SimpleNamespace(settlement_id=False, settlement_line_id=False, contract_id=15)])
        validate()
        other, validate_other = self._subcontract_payment_basis(subcontract_settlement_id=record.subcontract_settlement_id)
        validate_other()
        record.subcontract_settlement_id.state = 'paid'
        with self.assertRaises(ValueError): validate()  # Subcontract has no paid lifecycle state.
        record, validate = self._subcontract_payment_basis(contract_id=False)
        record.subcontract_settlement_id.contract_id = False
        validate()
        record, validate = self._subcontract_payment_basis(subcontract_settlement_id=False)
        validate()  # Existing non-subcontract request paths are unaffected.

    def _subcontract_reservation_check(self, *, amount=40, reserved=60, state='approved', has_source=True):
        method = next(n for n in ast.walk(ast.parse(MODEL.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_check_subcontract_settlement_remaining_amount')
        method.decorator_list = []
        def compare(a, b, precision_rounding):
            left, right = round(a / precision_rounding), round(b / precision_rounding)
            return (left > right) - (left < right)
        ns = {'ValidationError': ValueError, '_': lambda text: text, 'float_compare': compare}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(MODEL), 'exec'), ns)
        events = []
        source = types.SimpleNamespace(id=7, amount_total=100, currency_id=types.SimpleNamespace(rounding=0.01))
        record = types.SimpleNamespace(id=23, subcontract_settlement_id=source if has_source else False, amount=amount, state=state)
        source.ensure_one = lambda: None
        source_path = MODEL.with_name('subcontract_management.py')
        reserve = next(n for n in ast.walk(ast.parse(source_path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_payment_reserved_amount')
        exec(compile(ast.Module(body=[reserve], type_ignores=[]), str(source_path), 'exec'), ns)
        source._payment_reserved_amount = lambda **kw: ns['_payment_reserved_amount'](source, **kw)
        class Requests(list):
            def filtered(self, predicate): return Requests(filter(predicate, self))
            def mapped(self, field): return types.SimpleNamespace(_serialize_payment_reservation=lambda: events.append('serialize'))
            def _check_subcontract_settlement_consistency(self): events.append('identity')
            def sudo(self): return self
            def read_group(self, domain, fields, groupby):
                events.append(domain)
                return [{'amount': reserved}]
        source.env = {'payment.request': Requests([record])}
        return lambda: ns['_check_subcontract_settlement_remaining_amount'](Requests([record])), events

    def test_subcontract_basis_defaults_preserve_zero_remaining_amount(self):
        method = next(n for n in ast.walk(ast.parse(MODEL.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_basis_payment_request_values')
        method.decorator_list = []
        ns = {}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(MODEL), 'exec'), ns)
        source = types.SimpleNamespace(project_id=types.SimpleNamespace(id=11), contract_id=types.SimpleNamespace(id=False), subcontractor_id=types.SimpleNamespace(id=13), currency_id=types.SimpleNamespace(id=14))
        source.exists = lambda: source
        class Env(dict): context = {}
        record = types.SimpleNamespace(env=Env({'sc.subcontract.settlement': types.SimpleNamespace(browse=lambda value: source)}), _partner_payment_defaults=lambda partner, request_type: {'payment_account_no': 'existing-authority'})
        for amount in (0, 40):
            source._payment_unreserved_amount = lambda: amount
            values = ns['_basis_payment_request_values'](record, {'subcontract_settlement_id': 7})
            self.assertEqual(values['amount'], amount)
            self.assertEqual(values['project_id'], 11)
            self.assertEqual(values['partner_id'], 13)
            self.assertEqual(values['currency_id'], 14)
            self.assertEqual(values['payment_account_no'], 'existing-authority')

    def test_subcontract_reservation_allows_split_payments_but_not_overbooking(self):
        validate, events = self._subcontract_reservation_check()
        validate()
        self.assertEqual(events[:2], ['serialize', 'identity'])
        self.assertIn(('id', '!=', 23), events[2])
        self.assertIn(('subcontract_settlement_id', '=', 7), events[2])
        self.assertIn(('state', 'not in', ('draft', 'rejected', 'cancel')), events[2])
        for amount, reserved in ((40.01, 60), (1, 100), (0, 0), (-1, 0)):
            validate, _ = self._subcontract_reservation_check(amount=amount, reserved=reserved)
            with self.assertRaises(ValueError): validate()

    def test_subcontract_reservation_does_not_charge_inactive_or_unrelated_requests(self):
        for state in ('draft', 'rejected', 'cancel'):
            validate, events = self._subcontract_reservation_check(state=state, amount=999)
            validate()
            self.assertEqual(events, [])
        validate, events = self._subcontract_reservation_check(has_source=False, amount=999)
        validate()
        self.assertEqual(events, [])

    def test_subcontract_reservation_touches_source_version_after_lock(self):
        path = MODEL.with_name('subcontract_management.py')
        tree = ast.parse(path.read_text())
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_serialize_payment_reservation')
        ns = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        rec = self._purchase_request_record(state='confirmed')
        rec.payment_allocation_revision = 8
        rec.sudo = lambda: rec
        events = []
        rec._lock_payment_basis = lambda: events.append('lock')
        rec._write_approval_state = lambda vals: events.append(vals)
        ns['_serialize_payment_reservation'](rec)
        self.assertEqual(events, ['lock', {'payment_allocation_revision': 9}])
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScSubcontractSettlement')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'write')
        ns = {'_SUBCONTRACT_APPROVAL_STATE_TOKEN': object(), 'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        with self.assertRaises(ValueError): ns['write'](rec, {'payment_allocation_revision': 100})

    def test_subcontract_payment_summary_uses_attributed_canonical_cash_and_active_requests(self):
        ns, records, record, paid_map, _ambiguous, _events = self._rental_paid_methods()
        path = MODEL.with_name('subcontract_management.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScSubcontractSettlement')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_compute_payment_boundary_amounts')
        method.decorator_list = []
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        record.payment_request_ids[0].amount = 60
        record.payment_request_ids[1].amount = 40
        ns['_compute_payment_boundary_amounts'](records)
        self.assertEqual((record.payment_paid_amount, record.payment_unpaid_amount), (100, 0))
        self.assertEqual((record.payment_requested_amount, record.payment_unrequested_amount), (40, 60))
        paid_map[1], paid_map[2] = 0, 20
        ns['_compute_payment_boundary_amounts'](records)
        self.assertEqual((record.payment_paid_amount, record.payment_unpaid_amount), (20, 80))
        record.payment_request_ids[1].state = 'cancel'
        ns['_compute_payment_boundary_amounts'](records)
        self.assertEqual(record.payment_requested_amount, 0)
        self.assertEqual(record.payment_paid_amount, 20)

    def test_subcontract_attribution_cannot_reassign_financial_history(self):
        method = next(n for n in ast.walk(ast.parse(MODEL.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_assert_subcontract_attribution_unchanged')
        ns = {'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(MODEL), 'exec'), ns)
        contexts = []
        class Requests(list):
            def sudo(self): return self
            def with_context(self, **values):
                contexts.append(values)
                return self
        for current, target in ((7, False), (7, 8), (False, 7)):
            for ledger, execution in ((['reversed'], []), ([], ['cancelled'])):
                record = types.SimpleNamespace(subcontract_settlement_id=types.SimpleNamespace(id=current), ledger_line_ids=ledger, payment_execution_ids=execution)
                with self.assertRaises(ValueError):
                    ns['_assert_subcontract_attribution_unchanged'](Requests([record]), {'subcontract_settlement_id': target})
                ns['_assert_subcontract_attribution_unchanged'](Requests([record]), {'subcontract_settlement_id': current})
                ns['_assert_subcontract_attribution_unchanged'](Requests([record]), {'note': 'explanation'})
        record.ledger_line_ids, record.payment_execution_ids = [], []
        ns['_assert_subcontract_attribution_unchanged'](Requests([record]), {'subcontract_settlement_id': 8})
        self.assertTrue(contexts)
        self.assertTrue(all(values == {'active_test': False} for values in contexts))

    def test_execution_contract_resolves_caller_visible_subcontract_source(self):
        path = MODEL.with_name('payment_execution.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_payment_basis_contracts_map')
        method.decorator_list = []
        ns = {'ValidationError': ValueError, '_': lambda text: text}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(path), 'exec'), ns)
        class Rows(list):
            def search(self, domain): return Rows()
            @property
            def ids(self): return [row.id for row in self]
            @property
            def id(self): return self[0].id if self else False
            def mapped(self, name):
                result = Rows()
                for row in self:
                    value = getattr(row, name)
                    result.extend(value if isinstance(value, list) else [value])
                return result
            def __or__(self, other):
                return Rows(list(self) + [row for row in other if row not in self])
        empty = Rows()
        contract = types.SimpleNamespace(id=15, project_id=11)
        source = types.SimpleNamespace(id=7, project_id=11, contract_id=Rows([contract]))
        calls = []
        request = types.SimpleNamespace(id=23, project_id=11, subcontract_settlement_id=Rows([source]), rental_settlement_id=empty, settlement_id=empty, material_settlement_id=empty, contract_id=Rows([contract]), _check_subcontract_settlement_consistency=lambda: calls.append('identity'))
        def visible(model, ids):
            calls.append((model, set(ids)))
            if model == 'sc.subcontract.settlement': return {7: source}
            if model == 'construction.contract': return {15: Rows([contract])}
            return {}
        service = types.SimpleNamespace(env={'construction.contract': empty, 'payment.request.line': Rows()}, _caller_visible_payment_relations=visible)
        result = ns['_payment_basis_contracts_map'](service, Rows([request]))
        self.assertEqual(result[23], Rows([contract]))
        self.assertIn(('sc.subcontract.settlement', {7}), calls)
        self.assertIn('identity', calls)
        source.contract_id, request.contract_id = empty, empty
        self.assertEqual(ns['_payment_basis_contracts_map'](service, Rows([request]))[23], empty)
        def denied(model, ids):
            if model == 'sc.subcontract.settlement': raise PermissionError('source invisible')
            return visible(model, ids)
        service._caller_visible_payment_relations = denied
        with self.assertRaises(PermissionError): ns['_payment_basis_contracts_map'](service, Rows([request]))

    def test_ledger_accepts_only_confirmed_valid_subcontract_payment_basis(self):
        path = MODEL.with_name('payment_ledger.py')
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in {'_check_request_state', 'action_open_settlement'}]
        ns = {'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        checks = []
        source = types.SimpleNamespace(id=7, state='confirmed', project_id=types.SimpleNamespace(id=11))
        request = types.SimpleNamespace(state='approved', payment_basis_type='subcontract_settlement', subcontract_settlement_id=source, rental_settlement_id=False,
            _check_subcontract_settlement_consistency=lambda: checks.append('identity'),
            _check_subcontract_settlement_remaining_amount=lambda: checks.append('reservation'))
        ledger = types.SimpleNamespace(ensure_one=lambda: None, payment_request_id=request)
        ns['_check_request_state'](ledger, request)
        self.assertEqual(checks, ['identity', 'reservation'])
        action = ns['action_open_settlement'](ledger)
        self.assertEqual((action['res_model'], action['res_id']), ('sc.subcontract.settlement', 7))
        self.assertEqual(action['context'], {'default_project_id': 11})
        for state in ('draft', 'submitted', 'approved', 'paid', 'cancel'):
            source.state = state
            with self.assertRaises(ValueError): ns['_check_request_state'](ledger, request)
        source.state = 'confirmed'
        request.state = 'submit'
        with self.assertRaises(ValueError): ns['_check_request_state'](ledger, request)
        request.state = 'approved'
        request._check_subcontract_settlement_remaining_amount = lambda: (_ for _ in ()).throw(ValueError('overbooked'))
        with self.assertRaisesRegex(ValueError, 'overbooked'): ns['_check_request_state'](ledger, request)

    def test_subcontract_settlement_approval_precedes_explicit_confirmation(self):
        path = MODEL.with_name('subcontract_management.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScSubcontractSettlement')
        names = {'action_submit', 'action_confirm', 'action_cancel', 'action_on_tier_approved'}
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        ns = {'UserError': ValueError, 'ValidationError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        for required in (False, True):
            rec = self._purchase_request_record(required=required, state='draft')
            rec._name = 'sc.subcontract.settlement'
            anchors = []
            rec._check_business_anchor = lambda: anchors.append('checked')
            rec.line_ids = types.SimpleNamespace(_check_values=lambda: None)
            rec._write_approval_state = lambda vals: rec.data.update(vals)
            with self.assertRaises(ValueError): ns['action_confirm'](rec)
            ns['action_submit'](rec)
            self.assertEqual(rec.state, 'submitted' if required else 'approved')
            if required:
                with self.assertRaises(ValueError): ns['action_confirm'](rec)
                ns['action_on_tier_approved'](rec)
                self.assertEqual(rec.state, 'submitted')
                rec.data['validation_status'] = 'validated'
                ns['action_on_tier_approved'](rec)
            self.assertEqual(rec.state, 'approved')
            ns['action_confirm'](rec)
            self.assertEqual(rec.state, 'confirmed')
            self.assertGreaterEqual(len(anchors), 2)
            with self.assertRaises(ValueError): ns['action_confirm'](rec)
            with self.assertRaises(ValueError): ns['action_cancel'](rec)

    def test_subcontract_generated_number_is_hidden_on_create(self):
        path = ROOT / 'addons/smart_construction_core/views/core/subcontract_management_views.xml'
        tree = ET.parse(path)
        for name in ('plan', 'request', 'settlement'):
            field = tree.find(".//record[@id='view_sc_subcontract_%s_form']//form//field[@name='name']" % name)
            self.assertEqual(field.attrib.get('invisible'), 'not id')
            self.assertEqual(field.attrib.get('readonly'), '1')

    def test_subcontract_request_input_policy_preserves_calculated_facts(self):
        path = ROOT / 'addons/smart_construction_core/data/p1_daily_business_form_orchestration_contract_data.xml'
        record = ET.parse(path).find(".//record[@id='business_config_contract_sc_subcontract_request_p1_form_business_facts_v1']")
        payload = ast.literal_eval(record.find("field[@name='contract_json']").attrib['eval'])
        fields = {row['name']: row for row in payload['view_orchestration']['views']['form']['fields']}
        for name in ('project_id', 'request_date', 'subcontract_scope', 'suggested_subcontractor_id', 'note', 'attachment_ids'):
            self.assertNotIn('readonly', fields[name])
        for name in ('state', 'name', 'subcontract_type_text', 'quantity_total', 'price_unit', 'amount_total', 'monthly_amount_total', 'applicant_id', 'create_date'):
            self.assertIs(fields[name]['readonly'], True)

    def test_subcontract_submitted_and_approved_facts_are_frozen(self):
        path = MODEL.with_name('subcontract_management.py')
        for name in ('ScSubcontractPlan', 'ScSubcontractRequest'):
            cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == name)
            methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('write', '_assert_approval_facts_editable', 'unlink')]
            ns = {'UserError': ValueError, '_': lambda text: text, '_SUBCONTRACT_APPROVAL_STATE_TOKEN': object()}
            exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
            for state in ('submitted', 'approved', 'cancel'):
                rec = self._purchase_request_record(state=state)
                rec._assert_approval_facts_editable = lambda: ns['_assert_approval_facts_editable'](rec)
                for field in ('project_id', 'contract_id', 'currency_id', 'line_ids', 'estimated_amount', 'subcontract_scope'):
                    with self.assertRaises(ValueError): ns['write'](rec, {field: False})
                with self.assertRaises(ValueError): ns['unlink'](rec)
            rec = self._purchase_request_record(state='draft')
            ns['_assert_approval_facts_editable'](rec)

    def test_subcontract_direct_lines_check_old_new_and_default_parent(self):
        path = MODEL.with_name('subcontract_management.py')
        for name, parent in [('ScSubcontractPlanLine', 'plan_id'), ('ScSubcontractRequestLine', 'request_id')]:
            cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == name)
            methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('create', 'write', 'unlink')]
            for method in methods: method.decorator_list = []
            ns = {}
            exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
            calls = []
            def locked():
                calls.append('locked')
                raise ValueError('approval fact frozen')
            frozen = types.SimpleNamespace(_assert_approval_facts_editable=locked)
            draft = types.SimpleNamespace(_assert_approval_facts_editable=lambda: calls.append('draft'))
            class Env(dict):
                context = {'default_' + parent: 12}
            class Model:
                def browse(self, ids):
                    calls.append(ids)
                    return frozen
            rec = types.SimpleNamespace(env=Env({'sc.subcontract.' + ('plan' if parent == 'plan_id' else 'request'): Model()}),
                mapped=lambda field: frozen)
            with self.assertRaises(ValueError): ns['create'](rec, [{}])
            self.assertIn([12], calls)
            with self.assertRaises(ValueError): ns['write'](rec, {'estimated_amount': 1})
            with self.assertRaises(ValueError): ns['unlink'](rec)
            rec.mapped = lambda field: draft
            with self.assertRaises(ValueError): ns['write'](rec, {parent: 12})
            self.assertIn('draft', calls)
            self.assertIn(12, calls)

    def test_rental_order_approval_does_not_execute_rental(self):
        path = MODEL.with_name('material_rental.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScMaterialRentalOrder')
        names = {'action_submit', 'action_activate', 'action_return', 'action_settle', 'action_cancel', 'action_on_tier_approved'}
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        ns = {'UserError': ValueError, '_': lambda text: text, 'fields': types.SimpleNamespace(Date=types.SimpleNamespace(context_today=lambda record: '2026-10-01'))}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        for required in (False, True):
            rec = self._purchase_request_record(required=required, state='draft')
            rec._name = 'sc.material.rental.order'
            rec._write_approval_state = lambda values: rec.data.update(values)
            checks = []
            rec._check_business_anchor = lambda: checks.append('anchor')
            with self.assertRaises(ValueError): ns['action_activate'](rec)
            ns['action_submit'](rec)
            self.assertEqual(rec.state, 'submitted' if required else 'approved')
            if required:
                with self.assertRaises(ValueError): ns['action_activate'](rec)
                ns['action_on_tier_approved'](rec)
                self.assertEqual(rec.state, 'submitted')
                rec.data['validation_status'] = 'validated'
                ns['action_on_tier_approved'](rec)
            self.assertEqual(rec.state, 'approved')
            ns['action_activate'](rec)
            self.assertEqual(rec.state, 'active')
            rec.data['actual_return_date'] = False
            ns['action_return'](rec)
            self.assertEqual(rec.state, 'returned')
            self.assertEqual(rec.actual_return_date, '2026-10-01')
            with self.assertRaises(ValueError): ns['action_cancel'](rec)
            ns['action_settle'](rec)
            self.assertEqual(rec.state, 'settled')
            self.assertEqual(len(checks), 4)
            with self.assertRaises(ValueError): ns['action_settle'](rec)

    def test_rental_attribution_cannot_reassign_financial_history(self):
        method = next(n for n in ast.walk(ast.parse(MODEL.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_assert_rental_attribution_unchanged')
        ns = {'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(MODEL), 'exec'), ns)
        contexts = []
        class Requests(list):
            def sudo(self): return self
            def with_context(self, **values):
                contexts.append(values)
                return self
        for current, target in ((7, False), (7, 8), (False, 7)):
            for ledger, execution in ((['reversed'], []), ([], ['cancelled'])):
                record = types.SimpleNamespace(rental_settlement_id=types.SimpleNamespace(id=current), ledger_line_ids=ledger, payment_execution_ids=execution)
                with self.assertRaises(ValueError):
                    ns['_assert_rental_attribution_unchanged'](Requests([record]), {'rental_settlement_id': target})
                ns['_assert_rental_attribution_unchanged'](Requests([record]), {'rental_settlement_id': current})
                ns['_assert_rental_attribution_unchanged'](Requests([record]), {'note': 'explanation'})
        record.ledger_line_ids, record.payment_execution_ids = [], []
        ns['_assert_rental_attribution_unchanged'](Requests([record]), {'rental_settlement_id': 8})
        self.assertTrue(contexts)
        self.assertTrue(all(values == {'active_test': False} for values in contexts))

    def test_rental_source_cannot_cancel_live_payment_obligations(self):
        path = MODEL.with_name('material_rental.py')
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in {'_assert_no_live_payment_obligations', '_payment_cancellation_blocker'}]
        ns = {'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list):
            def filtered(self, predicate): return Rows(filter(predicate, self))
            def mapped(self, name): return Rows(row for item in self for row in getattr(item, name))
        record = self._purchase_request_record(state='confirmed')
        record._lock_payment_basis = lambda: None
        record.sudo = lambda: record
        record._payment_cancellation_blocker = lambda: ns['_payment_cancellation_blocker'](record)
        for state, ledger, blocked in [('approved', [], True), ('done', [], True), ('cancel', [types.SimpleNamespace(state='posted')], True), ('cancel', [types.SimpleNamespace(state='reversed')], False), ('draft', [], False)]:
            record.payment_request_ids = Rows([types.SimpleNamespace(state=state, ledger_line_ids=ledger)])
            if blocked:
                with self.assertRaises(ValueError): ns['_assert_no_live_payment_obligations'](record)
            else: ns['_assert_no_live_payment_obligations'](record)

    def test_execution_contract_resolves_caller_visible_rental_source(self):
        path = MODEL.with_name('payment_execution.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_payment_basis_contracts_map')
        method.decorator_list = []
        ns = {'ValidationError': ValueError, '_': lambda text: text}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(path), 'exec'), ns)
        class Rows(list):
            def search(self, domain): return Rows()
            @property
            def ids(self): return [row.id for row in self]
            @property
            def id(self): return self[0].id if self else False
            def mapped(self, name):
                result = Rows()
                for row in self:
                    value = getattr(row, name)
                    result.extend(value if isinstance(value, list) else [value])
                return result
            def __or__(self, other):
                return Rows(list(self) + [row for row in other if row not in self])
        empty = Rows()
        contract = types.SimpleNamespace(id=15, project_id=11)
        source = types.SimpleNamespace(id=7, project_id=11, contract_id=Rows([contract]))
        calls = []
        request = types.SimpleNamespace(id=23, project_id=11, rental_settlement_id=Rows([source]), subcontract_settlement_id=empty, settlement_id=empty, material_settlement_id=empty, contract_id=Rows([contract]), _check_rental_settlement_consistency=lambda: calls.append('identity'))
        def visible(model, ids):
            calls.append((model, set(ids)))
            if model == 'sc.material.rental.settlement': return {7: source}
            if model == 'construction.contract': return {15: Rows([contract])}
            return {}
        service = types.SimpleNamespace(env={'construction.contract': empty, 'payment.request.line': Rows()}, _caller_visible_payment_relations=visible)
        result = ns['_payment_basis_contracts_map'](service, Rows([request]))
        self.assertEqual(result[23], Rows([contract]))
        self.assertIn(('sc.material.rental.settlement', {7}), calls)
        self.assertIn('identity', calls)
        source.contract_id, request.contract_id = empty, empty
        self.assertEqual(ns['_payment_basis_contracts_map'](service, Rows([request]))[23], empty)
        def denied(model, ids):
            if model == 'sc.material.rental.settlement': raise PermissionError('source invisible')
            return visible(model, ids)
        service._caller_visible_payment_relations = denied
        with self.assertRaises(PermissionError): ns['_payment_basis_contracts_map'](service, Rows([request]))

    def test_rental_basis_counts_as_payment_basis_without_contract(self):
        method = next(n for n in ast.walk(ast.parse(MODEL.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_has_payment_basis')
        ns = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(MODEL), 'exec'), ns)
        record = types.SimpleNamespace(ensure_one=lambda: None, contract_id=False, settlement_id=False, material_settlement_id=False, rental_settlement_id=7, subcontract_settlement_id=False, outflow_line_ids=types.SimpleNamespace(filtered=lambda field: []))
        self.assertTrue(ns['_has_payment_basis'](record))
        record.rental_settlement_id = False
        self.assertFalse(ns['_has_payment_basis'](record))

    def test_rental_basis_defaults_preserve_zero_remaining_amount(self):
        method = next(n for n in ast.walk(ast.parse(MODEL.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_basis_payment_request_values')
        method.decorator_list = []
        ns = {}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(MODEL), 'exec'), ns)
        source = types.SimpleNamespace(project_id=types.SimpleNamespace(id=11), contract_id=types.SimpleNamespace(id=False), supplier_id=types.SimpleNamespace(id=13), currency_id=types.SimpleNamespace(id=14))
        source.exists = lambda: source
        class Env(dict): context = {}
        record = types.SimpleNamespace(env=Env({'sc.material.rental.settlement': types.SimpleNamespace(browse=lambda value: source)}), _partner_payment_defaults=lambda partner, request_type: {'payment_account_no': 'existing-authority'})
        for amount in (0, 40):
            source._payment_unreserved_amount = lambda: amount
            values = ns['_basis_payment_request_values'](record, {'rental_settlement_id': 7})
            self.assertEqual(values['amount'], amount)
            self.assertEqual(values['project_id'], 11)
            self.assertEqual(values['partner_id'], 13)
            self.assertEqual(values['currency_id'], 14)
            self.assertEqual(values['payment_account_no'], 'existing-authority')

    def _rental_reservation_check(self, *, amount=40, reserved=60, state='approved', has_source=True):
        method = next(n for n in ast.walk(ast.parse(MODEL.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_check_rental_settlement_remaining_amount')
        method.decorator_list = []
        def compare(a, b, precision_rounding):
            left, right = round(a / precision_rounding), round(b / precision_rounding)
            return (left > right) - (left < right)
        ns = {'ValidationError': ValueError, '_': lambda text: text, 'float_compare': compare}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(MODEL), 'exec'), ns)
        events = []
        source = types.SimpleNamespace(id=7, amount_total=100, currency_id=types.SimpleNamespace(rounding=0.01))
        record = types.SimpleNamespace(id=23, rental_settlement_id=source if has_source else False, amount=amount, state=state)
        source.ensure_one = lambda: None
        source_path = MODEL.with_name('material_rental.py')
        reserve = next(n for n in ast.walk(ast.parse(source_path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_payment_reserved_amount')
        exec(compile(ast.Module(body=[reserve], type_ignores=[]), str(source_path), 'exec'), ns)
        source._payment_reserved_amount = lambda **kw: ns['_payment_reserved_amount'](source, **kw)
        class Requests(list):
            def filtered(self, predicate): return Requests(filter(predicate, self))
            def mapped(self, field): return types.SimpleNamespace(_serialize_payment_reservation=lambda: events.append('serialize'))
            def _check_rental_settlement_consistency(self): events.append('identity')
            def sudo(self): return self
            def read_group(self, domain, fields, groupby):
                events.append(domain)
                return [{'amount': reserved}]
        source.env = {'payment.request': Requests([record])}
        return lambda: ns['_check_rental_settlement_remaining_amount'](Requests([record])), events

    def test_rental_reservation_allows_split_payments_but_not_overbooking(self):
        validate, events = self._rental_reservation_check()
        validate()
        self.assertEqual(events[:2], ['serialize', 'identity'])
        self.assertIn(('id', '!=', 23), events[2])
        self.assertIn(('rental_settlement_id', '=', 7), events[2])
        self.assertIn(('state', 'not in', ('draft', 'rejected', 'cancel')), events[2])
        for amount, reserved in ((40.01, 60), (1, 100), (0, 0), (-1, 0)):
            validate, _ = self._rental_reservation_check(amount=amount, reserved=reserved)
            with self.assertRaises(ValueError): validate()

    def test_rental_reservation_does_not_charge_inactive_or_unrelated_requests(self):
        for state in ('draft', 'rejected', 'cancel'):
            validate, events = self._rental_reservation_check(state=state, amount=999)
            validate()
            self.assertEqual(events, [])
        validate, events = self._rental_reservation_check(has_source=False, amount=999)
        validate()
        self.assertEqual(events, [])

    def test_rental_reservation_touches_source_version_after_lock(self):
        path = MODEL.with_name('material_rental.py')
        tree = ast.parse(path.read_text())
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_serialize_payment_reservation')
        ns = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        rec = self._purchase_request_record(state='confirmed')
        rec.payment_allocation_revision = 8
        rec.sudo = lambda: rec
        events = []
        rec._lock_payment_basis = lambda: events.append('lock')
        rec._write_approval_state = lambda vals: events.append(vals)
        ns['_serialize_payment_reservation'](rec)
        self.assertEqual(events, ['lock', {'payment_allocation_revision': 9}])
        ns = self._rental_fact_lock_methods('ScMaterialRentalSettlement')
        with self.assertRaises(ValueError): ns['write'](rec, {'payment_allocation_revision': 100})

    def _rental_fact_lock_methods(self, class_name):
        path = MODEL.with_name('material_rental.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == class_name)
        names = {'write', 'create', 'unlink', '_assert_business_facts_editable'}
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        for method in methods:
            method.decorator_list = []
        ns = {'UserError': ValueError, '_': lambda text: text, '_RENTAL_APPROVAL_STATE_TOKEN': object(), 'super': lambda: types.SimpleNamespace(write=lambda vals: vals, create=lambda vals: vals, unlink=lambda: True)}
        exec(compile(ast.fix_missing_locations(ast.Module(body=methods, type_ignores=[])), str(path), 'exec'), ns)
        return ns

    def test_rental_settlement_submitted_facts_cannot_be_rewritten(self):
        ns = self._rental_fact_lock_methods('ScMaterialRentalSettlement')
        for state in ('submitted', 'approved', 'confirmed', 'paid', 'cancel'):
            rec = self._purchase_request_record(state=state)
            rec._lock_payment_basis = lambda: None
            rec._assert_business_facts_editable = lambda: ns['_assert_business_facts_editable'](rec)
            for field in ('project_id', 'supplier_id', 'contract_id', 'currency_id', 'rental_order_id', 'settlement_date', 'line_ids', 'amount_total', 'damage_amount', 'rent_amount'):
                with self.subTest(state=state, field=field):
                    with self.assertRaises(ValueError): ns['write'](rec, {field: False})
            self.assertEqual(ns['write'](rec, {'note': 'explanation'}), {'note': 'explanation'})
        rec.data['state'] = 'draft'
        self.assertEqual(ns['write'](rec, {'supplier_id': 19}), {'supplier_id': 19})
        # Re-read after the serialization point, not the stale draft snapshot.
        rec._lock_payment_basis = lambda: rec.data.update(state='submitted')
        with self.assertRaises(ValueError): ns['write'](rec, {'supplier_id': 20})

    def test_rental_settlement_direct_line_writes_check_both_parents(self):
        ns = self._rental_fact_lock_methods('ScMaterialRentalSettlementLine')
        class Parents(list):
            def __or__(self, other): return Parents(list(self) + list(other))
            def _assert_business_facts_editable(self):
                if any(state != 'draft' for state in self): raise ValueError('immutable settlement')
        source, target = Parents(['confirmed']), Parents(['draft'])
        model = types.SimpleNamespace(browse=lambda ids: target)
        env = {'sc.material.rental.settlement': model}
        rec = types.SimpleNamespace(env=env, mapped=lambda name: source)
        with self.assertRaises(ValueError): ns['write'](rec, {'qty': 100})
        with self.assertRaises(ValueError): ns['unlink'](rec)
        with self.assertRaises(ValueError): ns['write'](rec, {'settlement_id': 23})
        source[:] = ['draft']
        target[:] = ['approved']
        with self.assertRaises(ValueError): ns['write'](rec, {'settlement_id': 23})
        target[:] = ['draft']
        self.assertEqual(ns['write'](rec, {'qty': 2}), {'qty': 2})
        self.assertTrue(ns['unlink'](rec))

    def test_rental_settlement_line_creation_checks_context_parent(self):
        ns = self._rental_fact_lock_methods('ScMaterialRentalSettlementLine')
        seen = []
        def browse(ids):
            seen.append(ids)
            return types.SimpleNamespace(_assert_business_facts_editable=lambda: (_ for _ in ()).throw(ValueError('immutable settlement')))
        class Env(dict): context = {'default_settlement_id': 41}
        rec = types.SimpleNamespace(env=Env({'sc.material.rental.settlement': types.SimpleNamespace(browse=browse)}))
        for vals in ({'settlement_id': 42}, {}):
            with self.assertRaises(ValueError): ns['create'](rec, [vals])
        self.assertEqual(seen, [[42], [41]])

    def _rental_payment_basis(self, **changes):
        tree = ast.parse(MODEL.read_text())
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_check_rental_settlement_consistency')
        method.decorator_list = []
        ns = {'ValidationError': ValueError, '_': lambda text: text}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(MODEL), 'exec'), ns)
        source = types.SimpleNamespace(state='confirmed', project_id=11, company_id=12, supplier_id=13, currency_id=14, contract_id=15)
        lines = changes.pop('lines', [])
        record = types.SimpleNamespace(rental_settlement_id=source, subcontract_settlement_id=False, type='pay', project_id=11, company_id=12, partner_id=13, currency_id=14, contract_id=15, settlement_id=False, material_settlement_id=False, outflow_line_ids=types.SimpleNamespace(filtered=lambda predicate: list(filter(predicate, lines))))
        record.__dict__.update(changes)
        return record, lambda: ns['_check_rental_settlement_consistency']([record])

    def test_rental_payment_basis_rejects_identity_mismatch(self):
        for field, value in [('type', 'receive'), ('project_id', 99), ('company_id', 99), ('partner_id', 99), ('currency_id', 99), ('contract_id', 99), ('partner_id', False), ('currency_id', False)]:
            with self.subTest(field=field, value=value):
                record, validate = self._rental_payment_basis(**{field: value})
                with self.assertRaises(ValueError): validate()
        for state in ('draft', 'submitted', 'approved', 'cancel'):
            record, validate = self._rental_payment_basis()
            record.rental_settlement_id.state = state
            with self.assertRaises(ValueError): validate()

    def test_rental_payment_basis_prevents_duplicate_obligation_claim(self):
        for field in ('settlement_id', 'material_settlement_id'):
            record, validate = self._rental_payment_basis(**{field: 17})
            with self.assertRaises(ValueError): validate()
        for line in [types.SimpleNamespace(settlement_id=17, settlement_line_id=False, contract_id=15), types.SimpleNamespace(settlement_id=False, settlement_line_id=18, contract_id=15), types.SimpleNamespace(settlement_id=False, settlement_line_id=False, contract_id=99)]:
            record, validate = self._rental_payment_basis(lines=[line])
            with self.assertRaises(ValueError): validate()

    def test_rental_payment_basis_accepts_same_source_multiple_requests(self):
        record, validate = self._rental_payment_basis(lines=[types.SimpleNamespace(settlement_id=False, settlement_line_id=False, contract_id=15)])
        validate()
        other, validate_other = self._rental_payment_basis(rental_settlement_id=record.rental_settlement_id)
        validate_other()
        record.rental_settlement_id.state = 'paid'
        validate()  # Historical attribution remains readable after completion.
        record, validate = self._rental_payment_basis(contract_id=False)
        record.rental_settlement_id.contract_id = False
        validate()
        record, validate = self._rental_payment_basis(rental_settlement_id=False)
        validate()  # Existing non-rental request paths are unaffected.

    def _rental_paid_methods(self):
        path = MODEL.with_name('material_rental.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScMaterialRentalSettlement')
        names = {'_compute_payment_summary', '_payment_confirmation_blocker', '_refresh_payment_confirmation', 'action_paid'}
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        for method in methods: method.decorator_list = []
        def compare(a, b, precision_rounding):
            left, right = round(a / precision_rounding), round(b / precision_rounding)
            return (left > right) - (left < right)
        ns = {'UserError': ValueError, '_': lambda text: text, 'float_compare': compare}
        exec(compile(ast.fix_missing_locations(ast.Module(body=methods, type_ignores=[])), str(path), 'exec'), ns)
        paid_map, ambiguous, events = {1: 60, 2: 40, 999: 999}, set(), []
        class Requests(list):
            def _canonical_payment_paid_amount_map(self): return paid_map
            def _ambiguous_posted_payment_request_ids(self): return ambiguous
        class Settlements(list):
            def sudo(self): return self
            def with_context(self, **values): return self
            def mapped(self, name): return Requests(row for record in self for row in record.payment_request_ids)
            def _lock_payment_basis(self): events.append('lock')
            def _serialize_payment_reservation(self): events.append('version')
        record = types.SimpleNamespace(state='confirmed', amount_total=100, currency_id=types.SimpleNamespace(rounding=0.01), payment_request_ids=Requests([types.SimpleNamespace(id=1, state='cancel'), types.SimpleNamespace(id=2, state='approved')]), ensure_one=lambda: None, _check_business_anchor=lambda: None)
        record.sudo = lambda: record
        record.with_context = lambda **values: record
        record._write_approval_state = lambda values: record.__dict__.update(values)
        record._payment_confirmation_blocker = lambda: ns['_payment_confirmation_blocker'](record)
        return ns, Settlements([record]), record, paid_map, ambiguous, events

    def test_rental_paid_summary_uses_only_attributed_canonical_posted_totals(self):
        ns, records, record, paid_map, ambiguous, events = self._rental_paid_methods()
        ns['_compute_payment_summary'](records)
        self.assertEqual((record.payment_paid_amount, record.payment_remaining_amount), (100, 0))
        self.assertIsNone(record._payment_confirmation_blocker())
        ns['action_paid'](records)
        self.assertEqual(record.state, 'paid')
        self.assertEqual(events, ['lock'])
        with self.assertRaises(ValueError): ns['action_paid'](records)

    def test_rental_partial_or_ambiguous_payment_cannot_confirm(self):
        ns, records, record, paid_map, ambiguous, events = self._rental_paid_methods()
        paid_map[2] = 0
        ns['_compute_payment_summary'](records)
        self.assertEqual((record.payment_paid_amount, record.payment_remaining_amount), (60, 40))
        with self.assertRaisesRegex(ValueError, 'RENTAL_PAYMENT_NOT_FULLY_PAID'): ns['action_paid'](records)
        self.assertEqual(record.state, 'confirmed')
        paid_map[2] = 40
        ambiguous.add(2)
        ns['_compute_payment_summary'](records)
        with self.assertRaisesRegex(ValueError, 'RENTAL_PAYMENT_HISTORY_AMBIGUOUS'): ns['action_paid'](records)
        ambiguous.clear()
        record.amount_total = 0
        with self.assertRaisesRegex(ValueError, 'RENTAL_PAYMENT_AMOUNT_INVALID'): ns['action_paid'](records)

    def test_rental_reversal_reopens_confirmation_without_automatic_repayment(self):
        ns, records, record, paid_map, ambiguous, events = self._rental_paid_methods()
        ns['_compute_payment_summary'](records)
        ns['action_paid'](records)
        paid_map[2] = 0
        ns['_compute_payment_summary'](records)
        ns['_refresh_payment_confirmation'](records)
        self.assertEqual(record.state, 'confirmed')
        self.assertIn('version', events)
        paid_map[2] = 40
        ns['_compute_payment_summary'](records)
        ns['_refresh_payment_confirmation'](records)
        self.assertEqual(record.state, 'confirmed')
        ns['action_paid'](records)
        self.assertEqual(record.state, 'paid')

    def test_ledger_accepts_only_confirmed_valid_rental_payment_basis(self):
        path = MODEL.with_name('payment_ledger.py')
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in {'_check_request_state', 'action_open_settlement'}]
        ns = {'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        checks = []
        source = types.SimpleNamespace(id=7, state='confirmed', project_id=types.SimpleNamespace(id=11))
        request = types.SimpleNamespace(state='approved', payment_basis_type='rental_settlement', rental_settlement_id=source,
            _check_rental_settlement_consistency=lambda: checks.append('identity'),
            _check_rental_settlement_remaining_amount=lambda: checks.append('reservation'))
        ledger = types.SimpleNamespace(ensure_one=lambda: None, payment_request_id=request)
        ns['_check_request_state'](ledger, request)
        self.assertEqual(checks, ['identity', 'reservation'])
        action = ns['action_open_settlement'](ledger)
        self.assertEqual((action['res_model'], action['res_id']), ('sc.material.rental.settlement', 7))
        self.assertEqual(action['context'], {'default_project_id': 11})
        for state in ('draft', 'submitted', 'approved', 'paid', 'cancel'):
            source.state = state
            with self.assertRaises(ValueError): ns['_check_request_state'](ledger, request)
        source.state = 'confirmed'
        request.state = 'submit'
        with self.assertRaises(ValueError): ns['_check_request_state'](ledger, request)
        request.state = 'approved'
        request._check_rental_settlement_remaining_amount = lambda: (_ for _ in ()).throw(ValueError('overbooked'))
        with self.assertRaisesRegex(ValueError, 'overbooked'): ns['_check_request_state'](ledger, request)

    def test_ledger_reversal_refreshes_rental_after_fact_write(self):
        path = MODEL.with_name('payment_ledger.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and any(isinstance(child, ast.FunctionDef) and child.name == 'action_reverse' for child in n.body))
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'write')
        events = []
        row = types.SimpleNamespace(state='posted')
        class Ledgers(list):
            env = types.SimpleNamespace(su=True, context={'_sc_payment_ledger_internal_reversal': True})
            def mapped(self, path):
                events.append(path)
                return types.SimpleNamespace(_refresh_payment_confirmation=lambda: events.append(row.state))
        def write(values):
            row.state = values['state']
            return True
        ns = {'AccessError': PermissionError, 'UserError': ValueError, '_': lambda text: text, 'super': lambda: types.SimpleNamespace(write=write)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        self.assertTrue(ns['write'](Ledgers([row]), {'state': 'reversed'}))
        self.assertEqual(events, ['payment_request_id.rental_settlement_id', 'reversed'])
        with self.assertRaises(ValueError): ns['write'](Ledgers([row]), {'state': 'reversed'})

    def test_rental_settlement_payment_link_cannot_manufacture_paid_fact(self):
        path = MODEL.with_name('material_rental.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScMaterialRentalSettlement')
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in {'action_paid', '_payment_confirmation_blocker'}]
        ns = {'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        for request in (False, types.SimpleNamespace(is_fully_paid=True, paid_amount_total=100)):
            rec = self._purchase_request_record(state='confirmed')
            rec.payment_request_id = request
            rec.payment_request_ids = []
            rec.sudo = lambda: rec
            rec._lock_payment_basis = lambda: None
            rec._check_business_anchor = lambda: None
            rec._write_approval_state = lambda values: rec.data.update(values)
            rec._payment_confirmation_blocker = lambda: ns['_payment_confirmation_blocker'](rec)
            with self.assertRaisesRegex(ValueError, 'RENTAL_PAYMENT_ATTRIBUTION_MISSING'):
                ns['action_paid'](rec)
            self.assertEqual(rec.state, 'confirmed')

    def test_rental_settlement_approval_requires_explicit_confirmation(self):
        path = MODEL.with_name('material_rental.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScMaterialRentalSettlement')
        names = {'action_submit', 'action_confirm', 'action_cancel', 'action_on_tier_approved', 'action_on_tier_rejected', 'write'}
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        ns = {'UserError': ValueError, '_': lambda text: text, '_RENTAL_APPROVAL_STATE_TOKEN': object()}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        for required in (False, True):
            rec = self._purchase_request_record(required=required, state='draft')
            rec._name = 'sc.material.rental.settlement'
            rec._lock_payment_basis = lambda: None
            rec._write_approval_state = lambda values: rec.data.update(values)
            rec._check_business_anchor = lambda: None
            with self.assertRaises(ValueError): ns['write'](rec, {'state': 'paid'})
            with self.assertRaises(ValueError): ns['action_confirm'](rec)
            ns['action_submit'](rec)
            self.assertEqual(rec.state, 'submitted' if required else 'approved')
            if required:
                with self.assertRaises(ValueError): ns['action_confirm'](rec)
                ns['action_on_tier_approved'](rec)
                self.assertEqual(rec.state, 'submitted')
                rec.data['validation_status'] = 'rejected'
                ns['action_on_tier_rejected'](rec, 'revise')
                self.assertEqual(rec.state, 'draft')
                self.assertEqual(rec.reject_reason, 'revise')
                ns['action_submit'](rec)
                rec.data['validation_status'] = 'validated'
                ns['action_on_tier_approved'](rec)
            self.assertEqual(rec.state, 'approved')
            ns['action_confirm'](rec)
            self.assertEqual(rec.state, 'confirmed')
            with self.assertRaises(ValueError): ns['action_confirm'](rec)
            ns['action_on_tier_approved'](rec)
            self.assertEqual(rec.state, 'confirmed')

    def test_rental_settlement_creation_policy_keeps_required_inputs_editable(self):
        path = ROOT / 'addons/smart_construction_core/data/p1_daily_business_form_orchestration_contract_data.xml'
        record = ET.parse(path).find(".//record[@id='business_config_contract_sc_material_rental_settlement_p1_form_business_facts_v1']")
        contract = ast.literal_eval(record.find("field[@name='contract_json']").get('eval'))
        fields = {field['name']: field for field in contract['view_orchestration']['views']['form']['fields']}
        for field in ('project_id', 'supplier_id'):
            self.assertNotIn('readonly', fields[field])
        for field in ('state', 'name', 'message_attachment_count', 'rental_settlement_source_created_by_display', 'source_created_at'):
            self.assertTrue(fields[field]['readonly'])

    def test_rental_order_input_policy_separates_execution_and_calculated_facts(self):
        path = ROOT / 'addons/smart_construction_core/data/p1_daily_business_form_orchestration_contract_data.xml'
        record = ET.parse(path).find(".//record[@id='business_config_contract_sc_material_rental_order_p1_form_business_facts_v1']")
        contract = ast.literal_eval(record.find("field[@name='contract_json']").attrib['eval'])
        fields = {row['name']: row for row in contract['view_orchestration']['views']['form']['fields']}
        for name in ('project_id', 'supplier_id', 'contract_id', 'rental_date', 'planned_return_date', 'use_unit_name', 'deposit_amount', 'compensation_fee', 'repair_fee', 'transport_fee', 'deposit_deduction', 'attachment_ids', 'note', 'owner_id'):
            self.assertNotIn('readonly', fields[name], name)
        for name in ('state', 'name', 'actual_return_date', 'material_summary', 'specification_summary', 'quantity_total', 'amount_total', 'settlement_amount', 'create_date'):
            self.assertIs(fields[name]['readonly'], True, name)

    def test_labor_settlement_inputs_remain_editable_in_published_contract(self):
        path = ROOT / 'addons/smart_construction_core/data/p1_daily_business_form_orchestration_contract_data.xml'
        record = ET.parse(path).find(".//record[@id='business_config_contract_sc_labor_settlement_p1_form_business_facts_v1']")
        contract = ast.literal_eval(record.find("field[@name='contract_json']").attrib['eval'])
        fields = {row['name']: row for row in contract['view_orchestration']['views']['form']['fields']}
        for name in ('project_id', 'contractor_id', 'settlement_date', 'note'):
            self.assertNotIn('readonly', fields[name], name)
        for name in ('payment_paid_amount', 'payment_unpaid_amount', 'payment_requested_amount', 'payment_unrequested_amount', 'source_created_at'):
            self.assertIs(fields[name]['readonly'], True, name)

    def test_labor_execution_family_requires_approval_before_confirmation(self):
        path = MODEL.with_name('labor_management.py')
        tree = ast.parse(path.read_text())
        for cls_name, model, writer in [('ScAttendanceCheckin', 'sc.attendance.checkin', '_write_approval_state'), ('ScLaborUsage', 'sc.labor.usage', '_write_cost_source_state'), ('ScLaborSettlement', 'sc.labor.settlement', '_write_approval_state')]:
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls_name)
            names = {'action_submit', 'action_confirm', 'action_cancel', 'action_reset_draft', 'action_on_tier_approved'}
            methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
            ns = {'ValidationError': ValueError, 'UserError': ValueError, '_': lambda text: text}
            exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
            for required in (False, True):
                rec = self._purchase_request_record(required=required, state='draft')
                rec._name = model
                rec.line_ids = types.SimpleNamespace(_check_values=lambda: None)
                rec._check_values = rec._check_business_anchor = lambda: None
                rec._check_project_operator = rec._check_project_manager = lambda: None
                setattr(rec, writer, lambda values: rec.data.update(values))
                ns['action_submit'](rec)
                self.assertEqual(rec.state, 'submitted' if required else 'approved')
                if required:
                    with self.assertRaises(ValueError): ns['action_confirm'](rec)
                    ns['action_on_tier_approved'](rec)
                    self.assertEqual(rec.state, 'submitted')
                    rec.data['validation_status'] = 'validated'
                    ns['action_on_tier_approved'](rec)
                self.assertEqual(rec.state, 'approved')
                if model == 'sc.labor.usage':
                    rec._check_project_manager = lambda: (_ for _ in ()).throw(PermissionError('manager required'))
                    with self.assertRaises(PermissionError): ns['action_cancel'](rec)
                    with self.assertRaises(PermissionError): ns['action_confirm'](rec)
                    rec._check_project_manager = lambda: None
                ns['action_confirm'](rec)
                self.assertEqual(rec.state, 'confirmed')
                for method in ('action_confirm', 'action_cancel', 'action_reset_draft'):
                    with self.assertRaises(ValueError): ns[method](rec)

    def _purchase_request_methods(self):
        path = MODEL.with_name('material_acceptance.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScMaterialPurchaseRequest')
        names = {'action_submit', 'action_approve', '_require_approved_for_downstream', 'action_on_tier_approved', 'action_on_tier_rejected', 'write'}
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        namespace = {'ValidationError': ValueError, 'UserError': ValueError, '_': lambda text: text, '_PURCHASE_REQUEST_STATE_TOKEN': object()}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
        return namespace

    def _purchase_request_record(self, **values):
        rec = self.record(**values)
        rec._name, rec.id = 'sc.material.purchase.request', 23
        rec.line_ids = types.SimpleNamespace(_check_qty=lambda: None)
        rec._sc_require_material_user = lambda label: None
        def require_state(states, label):
            if rec.state not in states:
                raise ValueError('wrong state')
        rec._sc_require_state = require_state
        rec._sc_material_audit_payload = lambda: {'state': rec.state}
        rec._sc_warn_system_defaults_on_action = lambda label: None
        rec._write_purchase_request_state = lambda values: rec.data.update(values)
        rec._sc_audit_material_transition = lambda *args, **kw: rec.audits.append((args, kw))
        rec.policy._assert_submission_approved = lambda record, states: PRODUCTION['_assert_submission_approved'](rec.policy, record, states)
        return rec

    def test_purchase_request_submission_requires_actual_review_before_downstream(self):
        methods = self._purchase_request_methods()
        for required in (False, True):
            rec = self._purchase_request_record(required=required, state='draft')
            methods['action_submit'](rec)
            self.assertEqual(rec.state, 'submitted' if required else 'approved')
            if required:
                with self.assertRaises(ValueError):
                    methods['_require_approved_for_downstream'](rec, 'generate')
                methods['action_on_tier_approved'](rec)
                self.assertEqual(rec.state, 'submitted')
                # A forged approved state still cannot bypass pending review facts.
                rec.data['state'] = 'approved'
                with self.assertRaises(ValueError):
                    methods['_require_approved_for_downstream'](rec, 'generate')
                rec.data.update(state='submitted', validation_status='validated')
                methods['action_on_tier_approved'](rec)
                self.assertEqual(rec.state, 'approved')
            methods['_require_approved_for_downstream'](rec, 'generate')
            self.assertEqual(rec.state, 'approved')

    def test_purchase_request_legacy_approve_preserves_review_wizard(self):
        rec = self._purchase_request_record(required=True, state='submitted', reviews=['tier'], status='pending')
        wizard = {'type': 'ir.actions.act_window', 'res_model': 'comment.wizard'}
        rec.validate_tier = lambda: wizard
        self.assertIs(self._purchase_request_methods()['action_approve'](rec), wizard)
        self.assertEqual(rec.state, 'submitted')

    def test_purchase_request_state_write_rejects_external_tokens(self):
        for token in (None, True, 'trusted'):
            rec = self._purchase_request_record(state='draft').with_context(sc_purchase_request_state_token=token)
            with self.assertRaises(ValueError):
                self._purchase_request_methods()['write'](rec, {'state': 'approved'})
            self.assertEqual(rec.state, 'draft')

    def test_purchase_request_rejected_submission_restarts_review(self):
        rec = self._purchase_request_record(required=True, state='draft', status='rejected', reviews=['old-review'])
        del rec._write_purchase_request_state
        def write_state(actor, values):
            if actor.review_ids and actor.validation_status == 'rejected' and not actor.env.context.get('skip_validation_check'):
                raise ValueError('tier write lock')
            actor.data.update(values)
        with patch.object(Record, '_write_purchase_request_state', write_state, create=True):
            self._purchase_request_methods()['action_submit'](rec)
        self.assertEqual(rec.state, 'submitted')
        self.assertEqual(rec.restarts, 1)
        self.assertEqual(rec.validation_status, 'pending')

    def _inbound_methods(self):
        path = MODEL.with_name('material_acceptance.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScMaterialInbound')
        names = {'action_submit', 'action_receive', 'action_on_tier_approved', 'action_on_tier_rejected', 'write'}
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        namespace = {'ValidationError': ValueError, 'UserError': ValueError, '_': lambda text: text, '_INBOUND_STATE_TOKEN': object()}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
        return namespace

    def test_inbound_submission_and_review_do_not_receive_material(self):
        methods = self._inbound_methods()
        for required in (False, True):
            rec = self.record(required=required, state='draft')
            rec._name, rec.id = 'sc.material.inbound', 23
            rec.line_ids = types.SimpleNamespace(_check_qty=lambda: None)
            rec.acceptance_id = False
            rec._sc_require_material_user = rec._sc_require_material_manager = lambda label: None
            def require_state(states, label):
                if rec.state not in states:
                    raise ValueError('wrong state')
            rec._sc_require_state = require_state
            rec._sc_material_audit_payload = lambda: {'state': rec.state}
            rec._sc_warn_system_defaults_on_action = lambda label: None
            rec._write_inbound_state = lambda values: rec.data.update(values)
            rec._sc_audit_material_transition = lambda *args, **kw: rec.audits.append((args, kw))
            rec.policy._assert_submission_approved = lambda record, states: PRODUCTION['_assert_submission_approved'](rec.policy, record, states)
            methods['action_submit'](rec)
            self.assertEqual(rec.state, 'submitted' if required else 'approved')
            if required:
                with self.assertRaises(ValueError):
                    methods['action_receive'](rec)
                methods['action_on_tier_approved'](rec)
                self.assertEqual(rec.state, 'submitted')
                rec.data['validation_status'] = 'validated'
                methods['action_on_tier_approved'](rec)
                self.assertEqual(rec.state, 'approved')
            methods['action_receive'](rec)
            self.assertEqual(rec.state, 'received')

    def test_inbound_resubmission_uses_private_transition_before_restarting_tier(self):
        methods = self._inbound_methods()
        rec = self.record(required=True, state='draft', status='rejected', reviews=['old-review'])
        rec._name, rec.id = 'sc.material.inbound', 23
        rec.line_ids = types.SimpleNamespace(_check_qty=lambda: None)
        rec._sc_require_material_user = rec._sc_require_state = lambda *args: None
        rec._sc_material_audit_payload = lambda: {'state': rec.state}
        rec._sc_warn_system_defaults_on_action = rec._sc_audit_material_transition = lambda *args, **kw: None
        def write_state(actor, values):
            if actor.review_ids and actor.validation_status == 'rejected' and not actor.env.context.get('skip_validation_check'):
                raise ValueError('tier write lock')
            actor.data.update(values)
        # Bind the collaborator on the type so context clones retain their own
        # environment (an instance-bound lambda would hide this regression).
        with patch.object(Record, '_write_inbound_state', write_state, create=True):
            methods['action_submit'](rec)
        self.assertEqual(rec.state, 'submitted')
        self.assertEqual(rec.restarts, 1)
        self.assertEqual(rec.validation_status, 'pending')

    def test_inbound_state_write_rejects_external_context_tokens(self):
        methods = self._inbound_methods()
        for token in (None, True, 'trusted'):
            rec = self.record(state='draft').with_context(sc_inbound_state_token=token)
            with self.assertRaises(ValueError):
                methods['write'](rec, {'state': 'approved'})
            self.assertEqual(rec.state, 'draft')

    def test_transfer_preserves_pending_inbound_instead_of_bypassing_review(self):
        path = MODEL.with_name('material_acceptance.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScMaterialOutbound')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_sync_transfer_inbound_after_issue')
        namespace = {'ValidationError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        for state, reviews, expected in [('submitted', ['review'], 'submitted'), ('approved', ['review'], 'approved'), ('approved', [], 'received')]:
            inbound = types.SimpleNamespace(id=9, state=state, review_ids=reviews)
            inbound.action_receive = lambda: setattr(inbound, 'state', 'received')
            outbound = types.SimpleNamespace(id=8, outbound_type='transfer', transfer_inbound_id=inbound, ensure_one=lambda: None)
            outbound.env = {'sc.material.inbound': types.SimpleNamespace(sudo=lambda: None)}
            self.assertIs(namespace['_sync_transfer_inbound_after_issue'](outbound), inbound)
            self.assertEqual(inbound.state, expected)

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

    def test_contract_event_external_state_and_defaults_cannot_bypass_actions(self):
        path = MODEL.with_name('contract_event.py')
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in {'create', 'write'}]
        for method in methods: method.decorator_list = []
        token, calls = object(), []
        ns = {'UserError': ValueError, '_': lambda text: text, '_DOCUMENT_STATE_TOKEN': token,
              'super': lambda: types.SimpleNamespace(create=lambda vals: calls.append(vals) or True,
                                                     write=lambda vals: calls.append(vals) or True)}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list): pass
        row = Rows([types.SimpleNamespace(state='draft', validation_status='no')])
        row.env = types.SimpleNamespace(context={})
        for state in ('submitted', 'approved', 'rejected', 'done', 'cancel'):
            for context in ({}, {'sc_document_state_token': True}, {'skip_validation_check': True}):
                row.env.context = context
                with self.subTest(state=state, context=context), self.assertRaises(ValueError): ns['write'](row, {'state': state})
                with self.assertRaises(ValueError): ns['create'](row, [{'state': state}])
            row.env.context = {'default_state': state}
            with self.assertRaises(ValueError): ns['create'](row, [{}])
        self.assertEqual(calls, [])
        row.env.context = {}
        self.assertTrue(ns['create'](row, [{'name': 'draft'}]))
        self.assertTrue(ns['write'](row, {'description': 'editable draft'}))
        row.env.context = {'sc_document_state_token': token}
        self.assertTrue(ns['write'](row, {'state': 'approved'}))

    def test_plan_external_state_and_defaults_cannot_bypass_actions(self):
        path = MODEL.with_name('plan_management.py')
        cls = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.ClassDef) and n.name == 'ScPlan')
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in {'create', 'write'}]
        for method in methods: method.decorator_list = []
        token, calls = object(), []
        ns = {'UserError': ValueError, '_': lambda text: text, '_DOCUMENT_STATE_TOKEN': token,
              'super': lambda: types.SimpleNamespace(create=lambda vals: calls.append(vals) or True,
                                                     write=lambda vals: calls.append(vals) or True)}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        row = types.SimpleNamespace(env=types.SimpleNamespace(context={}))
        for state in ('confirmed', 'in_progress', 'done', 'cancel'):
            for context in ({}, {'sc_document_state_token': True}, {'skip_validation_check': True}):
                row.env.context = context
                with self.subTest(state=state, context=context), self.assertRaises(ValueError): ns['write'](row, {'state': state})
                with self.assertRaises(ValueError): ns['create'](row, [{'state': state}])
            row.env.context = {'default_state': state}
            with self.assertRaises(ValueError): ns['create'](row, [{}])
        self.assertEqual(calls, [])
        row.env.context = {}
        self.assertTrue(ns['create'](row, [{'name': 'draft'}]))
        self.assertTrue(ns['write'](row, {'description': 'editable draft'}))
        row.env.context = {'sc_document_state_token': token}
        self.assertTrue(ns['write'](row, {'state': 'confirmed'}))

    def test_contract_event_reviewed_content_and_rejected_editability_agree(self):
        path = MODEL.with_name('contract_event.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'write')
        token, writes = object(), []
        ns = {'UserError': ValueError, '_': lambda text: text, '_DOCUMENT_STATE_TOKEN': token,
              'super': lambda: types.SimpleNamespace(write=lambda vals: writes.append(vals) or True)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list): pass
        row = types.SimpleNamespace(state='draft', validation_status='no')
        rows = Rows([row]); rows.env = types.SimpleNamespace(context={'skip_validation_check': True, 'sc_document_state_token': True})
        for state, status in (('submitted', 'pending'), ('approved', 'no'), ('done', 'validated'), ('cancel', 'no'), ('rejected', 'pending')):
            row.state, row.validation_status = state, status
            for vals in ({'amount_impact': 999}, {'project_id': 11}, {'description': 'changed'}, {'attachment_ids': [(5, 0, 0)]}, {'settlement_included': True}):
                with self.subTest(state=state, vals=vals), self.assertRaises(ValueError): ns['write'](rows, vals)
        self.assertEqual(writes, [])
        row.state, row.validation_status = 'rejected', 'rejected'
        self.assertTrue(ns['write'](rows, {'description': 'corrected'}))
        service_path = MODEL.parents[1] / 'support/workflow_contract_service.py'
        tree = ast.parse(service_path.read_text())
        profile = next(ast.literal_eval(value) for node in ast.walk(tree) if isinstance(node, ast.Dict)
                       for key, value in zip(node.keys, node.values) if isinstance(key, ast.Constant) and key.value == 'sc.contract.event')
        edit = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_editability')
        edit.decorator_list = []
        exec(compile(ast.Module(body=[edit], type_ignores=[]), str(service_path), 'exec'), ns)
        service = types.SimpleNamespace(TERMINAL_PHASES={'done', 'cancelled'})
        self.assertEqual(ns['_editability'](service, profile, 'rejected', 'rejected'), 'editable')
        self.assertEqual(ns['_editability'](service, profile, 'rejected', 'pending'), 'readonly')
        self.assertEqual(ns['_editability'](service, profile, 'approved', 'approved'), 'readonly')

    def test_field_editable_phases_cannot_override_pending_approval(self):
        path = MODEL.parents[1] / 'support/workflow_contract_service.py'
        tree = ast.parse(path.read_text())
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_editability')
        method.decorator_list = []
        ns = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        service = types.SimpleNamespace(TERMINAL_PHASES={'done', 'cancelled', 'closed'})
        profiles = [ast.literal_eval(n) for n in ast.walk(tree) if isinstance(n, ast.Dict)
                    and any(isinstance(k, ast.Constant) and k.value == 'field_editable_phases' for k in n.keys)]
        self.assertGreater(len(profiles), 0)
        for profile in profiles:
            for phase in profile['field_editable_phases']:
                for approval in ('waiting', 'pending'):
                    with self.subTest(phase=phase, approval=approval):
                        self.assertEqual(ns['_editability'](service, profile, phase, approval), 'readonly')
                for approval in ('none', 'approved'):
                    self.assertEqual(ns['_editability'](service, profile, phase, approval), 'editable')
        self.assertEqual(ns['_editability'](service, {}, 'draft', 'rejected'), 'editable')
        self.assertEqual(ns['_editability'](service, {}, 'approved', 'approved'), 'readonly')
        self.assertEqual(ns['_editability'](service, {}, 'done', 'approved'), 'locked')

    def test_contract_event_submission_and_callback_require_shared_approval_facts(self):
        path = MODEL.parent / 'contract_event.py'
        tree = ast.parse(path.read_text())
        names = {'action_submit', 'action_approve', 'action_reject', 'action_done', 'action_on_tier_approved'}
        methods = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in names]
        namespace = {'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
        class Event:
            def __iter__(self): return iter([self])
            def ensure_one(self): pass
            def _check_business_anchor(self):
                if not self.valid_anchor: raise ValueError('anchor')
            def with_context(self, **kw): return self
            def _write_document_state(self, values): self.__dict__.update(values)
        for required in (False, True):
            event = Event()
            event.state, event.valid_anchor = 'draft', True
            event.review_ids, event.validation_status = [], 'no'
            calls = []
            policy = types.SimpleNamespace(
                _start_submission_review=lambda rec: required,
                _approve_submission_review=lambda rec: calls.append('approve'),
                _reject_submission_review=lambda rec: calls.append('reject'),
                _assert_submission_approved=lambda rec, states: None)
            event.env = {'sc.approval.policy': policy}
            namespace['action_submit'](event)
            self.assertEqual(event.state, 'submitted' if required else 'approved')
            if required:
                namespace['action_approve'](event)
                namespace['action_reject'](event)
                self.assertEqual(calls, ['approve', 'reject'])
                namespace['action_on_tier_approved'](event)
                self.assertEqual(event.state, 'submitted')
                event.review_ids, event.validation_status = [1], 'pending'
                namespace['action_on_tier_approved'](event)
                self.assertEqual(event.state, 'submitted')
                event.validation_status = 'validated'
                namespace['action_on_tier_approved'](event)
                self.assertEqual(event.state, 'approved')
            namespace['action_done'](event)
            self.assertEqual(event.state, 'done')
            event.state, event.valid_anchor = 'draft', False
            with self.assertRaises(ValueError): namespace['action_submit'](event)
            self.assertEqual(event.state, 'draft')

    def test_plan_configuration_routes_confirmation_and_never_starts_execution(self):
        path = MODEL.parent / 'plan_management.py'
        names = {'action_confirm', 'action_on_tier_approved', 'action_start', 'action_done'}
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScPlan')
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        namespace = {'UserError': ValueError, '_': lambda text: text,
                     'fields': types.SimpleNamespace(Date=types.SimpleNamespace(context_today=lambda rec: '2026-09-30'))}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
        class Plan:
            def __iter__(self): return iter([self])
            def with_context(self, **kw): return self
            def _write_document_state(self, values): self.__dict__.update(values)
            def _check_business_anchor(self, **kw):
                if not self.valid: raise ValueError('schedule')
                self.checks.append(kw)
        for configured in (True, False):
            plan = Plan()
            plan.state, plan.valid, plan.checks = 'draft', True, []
            plan.review_ids, plan.validation_status = [], 'no'
            gates = []
            plan.env = {'sc.approval.policy': types.SimpleNamespace(
                _start_submission_review=lambda rec: configured,
                _assert_submission_approved=lambda rec, states: gates.append(states))}
            namespace['action_confirm'](plan)
            self.assertEqual(plan.state, 'draft' if configured else 'confirmed')
            if configured:
                namespace['action_on_tier_approved'](plan)
                self.assertEqual(plan.state, 'draft')
                plan.review_ids, plan.validation_status = [1], 'pending'
                namespace['action_on_tier_approved'](plan)
                self.assertEqual(plan.state, 'draft')
                plan.validation_status = 'validated'
                namespace['action_on_tier_approved'](plan)
                self.assertEqual(plan.state, 'confirmed')
            self.assertFalse(hasattr(plan, 'actual_start'))
            namespace['action_start'](plan)
            self.assertEqual(plan.state, 'in_progress')
            namespace['action_done'](plan)
            self.assertEqual(plan.state, 'done')
            self.assertEqual(gates, [('confirmed',), ('in_progress',)])
            self.assertIn({'require_schedule': True, 'require_lines_done': True}, plan.checks)
            plan.state, plan.valid = 'draft', False
            with self.assertRaises(ValueError): namespace['action_confirm'](plan)
            self.assertEqual(plan.state, 'draft')

    def test_diary_state_and_origin_writes_require_internal_authority(self):
        path = MODEL.with_name('construction_diary.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'write')
        token, writes = object(), []
        ns = {'UserError': ValueError, '_': lambda text: text, '_DOCUMENT_STATE_TOKEN': token,
              'super': lambda: types.SimpleNamespace(write=lambda vals: writes.append(dict(vals)) or True)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list): pass
        rows = Rows([types.SimpleNamespace(source_origin='manual', state='draft')])
        for context in ({}, {'sc_document_state_token': True}, {'skip_validation_check': True}):
            rows.env = types.SimpleNamespace(context=context)
            for values in ({'state': 'confirmed'}, {'state': 'done'}, {'source_origin': 'legacy'}):
                with self.subTest(context=context, values=values), self.assertRaises(ValueError): ns['write'](rows, values)
        self.assertEqual(writes, [])
        rows.env.context = {'sc_document_state_token': token}
        self.assertTrue(ns['write'](rows, {'state': 'confirmed'}))
        rows.env.context = {}
        self.assertTrue(ns['write'](rows, {'description': 'draft content'}))
        rows[0].source_origin, rows[0].state = 'legacy', 'legacy_confirmed'
        self.assertTrue(ns['write'](rows, {'note': 'supplement'}))
        with self.assertRaises(ValueError): ns['write'](rows, {'description': 'rewrite history'})

    def test_diary_create_rejects_state_defaults_before_sequence(self):
        path = MODEL.with_name('construction_diary.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'create')
        method.decorator_list = []
        ns = {'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        class SequenceReached(Exception): pass
        class Env:
            def __getitem__(self, key): raise SequenceReached(key)
        row = types.SimpleNamespace(env=Env())
        for su in (False, True):
            row.env.su = su
            for state in ('confirmed', 'done', 'cancel'):
                for vals, context in (({'state': state}, {}), ({}, {'default_state': state})):
                    row.env.context = context
                    with self.subTest(su=su, vals=vals, context=context), self.assertRaises(ValueError): ns['create'](row, [vals])
        row.env.su, row.env.context = False, {}
        with self.assertRaises(ValueError): ns['create'](row, [{'source_origin': 'legacy'}])
        with self.assertRaises(SequenceReached): ns['create'](row, [{}])
        row.env.su = True
        with self.assertRaises(SequenceReached): ns['create'](row, [{'source_origin': 'legacy', 'state': 'legacy_confirmed'}])

    def test_diary_real_rejected_draft_can_edit_under_tier_rules(self):
        path = MODEL.with_name('construction_diary.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_check_allow_write_under_validation')
        calls = []
        ns = {'super': lambda: types.SimpleNamespace(_check_allow_write_under_validation=lambda vals: calls.append(vals) or False)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        row = types.SimpleNamespace(ensure_one=lambda: None, state='draft', validation_status='rejected')
        self.assertTrue(ns[method.name](row, {'description': 'corrected'}))
        self.assertEqual(calls, [])
        for vals in ({'state': 'confirmed'}, {'source_origin': 'legacy'}):
            self.assertFalse(ns[method.name](row, vals))
        for state, status in (('draft', 'waiting'), ('draft', 'pending'), ('draft', 'validated'), ('confirmed', 'rejected'), ('done', 'validated')):
            row.state, row.validation_status = state, status
            self.assertFalse(ns[method.name](row, {'description': 'changed'}))

    def test_plan_reviewed_definition_is_protected_without_freezing_child_execution(self):
        path = MODEL.with_name('plan_management.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'write')
        token, writes = object(), []
        ns = {'UserError': ValueError, '_': lambda text: text, '_DOCUMENT_STATE_TOKEN': token,
              'super': lambda: types.SimpleNamespace(write=lambda vals: writes.append(dict(vals)) or True)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list): pass
        row = types.SimpleNamespace(state='draft', validation_status='no')
        rows = Rows([row]); rows.env = types.SimpleNamespace(context={'skip_validation_check': True, 'sc_document_state_token': True})
        for state, approval in (('draft', 'waiting'), ('draft', 'pending'), ('draft', 'validated'),
                                ('confirmed', 'no'), ('in_progress', 'validated'), ('done', 'no'), ('cancel', 'no')):
            row.state, row.validation_status = state, approval
            for vals in ({'name': 'changed'}, {'project_id': 2}, {'company_id': 2}, {'planned_finish': '2026-12-31'},
                         {'owner_id': 2}, {'version_stage': 'adjustment'}, {'note': 'changed'}, {'attachment_ids': [(5, 0, 0)]}):
                with self.subTest(state=state, approval=approval, vals=vals), self.assertRaises(ValueError):
                    ns['write'](rows, vals)
        self.assertEqual(writes, [])
        row.state, row.validation_status = 'draft', 'rejected'
        self.assertTrue(ns['write'](rows, {'name': 'corrected', 'note': 'corrected'}))
        row.state, row.validation_status = 'in_progress', 'validated'
        self.assertTrue(ns['write'](rows, {'line_ids': [(1, 5, {'progress_rate': 50})]}))
        self.assertTrue(ns['write'](rows, {'report_ids': [(0, 0, {'summary': 'execution'})]}))
        rows.env.context = {'sc_document_state_token': token}
        self.assertTrue(ns['write'](rows, {'state': 'done', 'actual_finish': '2026-10-01'}))

    def test_plan_node_definition_and_execution_have_separate_guards(self):
        path = MODEL.with_name('plan_management.py')
        cls = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.ClassDef) and n.name == 'ScPlanLine')
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in {'write', 'create', 'unlink', '_assert_definition_editable'}]
        for m in methods: m.decorator_list = []
        writes = []
        ns = {'UserError': ValueError, '_': lambda text: text, 'super': lambda: types.SimpleNamespace(
            write=lambda vals: writes.append(vals) or True, create=lambda vals: vals, unlink=lambda: True)}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        class Plan:
            def exists(self): return self
        plan = Plan(); plan.state, plan.validation_status = 'draft', 'no'
        class Env(dict): context = {}
        class Rows(list):
            def _assert_definition_editable(self): return ns['_assert_definition_editable'](self)
        rows = Rows([types.SimpleNamespace(plan_id=plan)])
        rows.env = Env({'sc.plan': types.SimpleNamespace(browse=lambda id: plan)})
        self.assertTrue(ns['write'](rows, {'name': 'draft baseline'}))
        for state, status in (('draft', 'pending'), ('confirmed', 'validated'), ('in_progress', 'validated'), ('done', 'no')):
            plan.state, plan.validation_status = state, status
            for method, args in [('write', ({'name': 'changed'},)), ('create', ([{'plan_id': 1}],)), ('unlink', ())]:
                with self.subTest(state=state, method=method), self.assertRaises(ValueError): ns[method](rows, *args)
        for state in ('draft', 'confirmed', 'done', 'cancel'):
            plan.state, plan.validation_status = state, 'no'
            with self.assertRaises(ValueError): ns['write'](rows, {'progress_rate': 50})
        plan.state, plan.validation_status = 'in_progress', 'validated'
        self.assertTrue(ns['write'](rows, {'progress_rate': 50, 'state': 'in_progress'}))
        plan.validation_status = 'pending'
        with self.assertRaises(ValueError): ns['write'](rows, {'progress_rate': 50})
        plan.state, plan.validation_status = 'draft', 'rejected'
        self.assertTrue(ns['write'](rows, {'name': 'corrected'}))

    def test_plan_native_fields_declare_baseline_and_execution_conditions(self):
        path = ROOT / 'addons/smart_construction_core/views/core/plan_management_views.xml'
        root = ET.parse(path).getroot()
        for record in root.findall('record'):
            for field in record.findall('field'):
                self.assertNotIn('readonly', field.attrib, 'view metadata is not a form field')
        form = root.find(".//record[@id='view_sc_plan_form']/field[@name='arch']/form")
        definition = "state != 'draft' or validation_status in ('waiting', 'pending', 'validated')"
        for name in ('name', 'plan_type', 'project_id', 'company_id', 'owner_id', 'planned_start', 'planned_finish', 'note', 'attachment_ids'):
            field = form.find(".//field[@name='%s']" % name)
            self.assertEqual(field.get('readonly'), definition)
        tree = form.find(".//field[@name='line_ids']/tree")
        for name in ('name', 'planned_start', 'planned_finish', 'owner_id', 'parent_id'):
            self.assertEqual(tree.find("field[@name='%s']" % name).get('readonly'),
                             "parent.state != 'draft' or parent.validation_status in ('waiting', 'pending', 'validated')")
        for name in ('progress_rate', 'state'):
            self.assertEqual(tree.find("field[@name='%s']" % name).get('readonly'),
                             "parent.state != 'in_progress' or parent.validation_status in ('waiting', 'pending')")

    def test_plan_entry_retires_layout_mirror_without_dropping_business_fields(self):
        root = ET.parse(ROOT / 'addons/smart_construction_core/data/construction_plan_form_productization_contract.xml').getroot()
        record = root.find(".//record[@id='business_config_contract_construction_plan_productized_form_v1']")
        payload = ast.literal_eval(record.find("field[@name='contract_json']").get('eval'))
        form = payload['view_orchestration']['views']['form']
        self.assertEqual(form, {'title': '计划管理', 'composition_mode': 'native_semantic_surface'})
        replay = [n for n in root.findall('function') if 'construction_plan_productized_form_v1' in n.find('value').get('eval', '')]
        self.assertEqual(len(replay), 1)
        self.assertEqual(ast.literal_eval(replay[0].findall('value')[1].get('eval')), {'priority': 800, 'contract_json': payload})
        views = ET.parse(ROOT / 'addons/smart_construction_core/views/core/plan_management_views.xml').getroot()
        native = views.find(".//record[@id='view_sc_plan_form']/field[@name='arch']/form")
        fields = {n.get('name') for n in native.iter('field')}
        required = {'state', 'name', 'plan_type', 'project_id', 'phase_name', 'company_id', 'owner_id', 'department_id',
                    'template_name', 'creation_method', 'version_stage', 'report_cycle', 'planned_start', 'planned_finish',
                    'actual_start', 'actual_finish', 'progress_rate', 'attainment_state', 'line_ids', 'report_ids',
                    'version_ids', 'attachment_ids', 'note', 'legacy_fact_model', 'legacy_fact_id', 'legacy_fact_type',
                    'source_created_by', 'source_created_at', 'active'}
        self.assertFalse(required - fields)

    def test_plan_node_create_rejects_initial_execution_and_context_defaults(self):
        path = MODEL.with_name('plan_management.py')
        cls = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.ClassDef) and n.name == 'ScPlanLine')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'create')
        method.decorator_list = []
        calls = []
        ns = {'UserError': ValueError, '_': lambda text: text,
              'super': lambda: types.SimpleNamespace(create=lambda vals: calls.append(vals) or True)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        class Env:
            context = {}
            def __getitem__(self, name):
                return types.SimpleNamespace(browse=lambda id: types.SimpleNamespace(
                    exists=lambda: types.SimpleNamespace(state='draft', validation_status='no')))
        row = types.SimpleNamespace(env=Env())
        for field, value in [('state', 'done'), ('state', 'in_progress'), ('state', 'cancel'),
                             ('progress_rate', 100), ('actual_start', '2026-10-01'), ('actual_finish', '2026-10-01')]:
            for vals, context in (({field: value}, {}), ({}, {'default_' + field: value})):
                row.env.context = context
                with self.subTest(field=field, context=context), self.assertRaises(ValueError):
                    ns['create'](row, [{'plan_id': 1, **vals}])
        self.assertEqual(calls, [])
        row.env.context = {}
        self.assertTrue(ns['create'](row, [{'plan_id': 1, 'state': 'draft', 'progress_rate': 0}]))
        row.env.context = {'default_state': 'done', 'default_progress_rate': 100}
        self.assertTrue(ns['create'](row, [{'plan_id': 1, 'state': 'draft', 'progress_rate': 0}]))

    def test_plan_node_contract_restricts_structure_without_granting_permissions(self):
        path = ROOT / 'addons/smart_construction_core/core_extension_contract_normalizers.py'
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'restrict_plan_node_structure')
        ns = {'Any': object, 'deepcopy': copy.deepcopy}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        source = {'record': {'id': 1, 'state': 'draft', 'validation_status': 'no'},
                  'views': {'form': {'subviews': {'line_ids': {'policies': {'can_create': True, 'can_unlink': True, 'inline_edit': True}},
                                                 'report_ids': {'policies': {'can_create': True}}}}},
                  'fields': {'line_ids': {'name': 'line_ids', 'subview': {'policies': {'can_create': False, 'can_unlink': True}}}}}
        for state, approval, allowed in [('draft', 'no', True), ('draft', 'rejected', True), ('draft', 'pending', False),
                                        ('draft', 'waiting', False), ('draft', 'validated', False), ('confirmed', 'no', False),
                                        ('in_progress', 'validated', False), ('done', 'no', False), (None, 'no', False)]:
            source['record'].update(state=state, validation_status=approval)
            out = ns[method.name](source)
            policies = out['views']['form']['subviews']['line_ids']['policies']
            self.assertEqual(policies['can_create'], allowed)
            self.assertEqual(policies['can_unlink'], allowed)
            self.assertTrue(policies['inline_edit'])
            self.assertFalse(out['fields']['line_ids']['subview']['policies']['can_create'])
            self.assertTrue(out['views']['form']['subviews']['report_ids']['policies']['can_create'])
            self.assertTrue(source['views']['form']['subviews']['line_ids']['policies']['can_create'])
        source['record'] = {}
        self.assertEqual(ns[method.name](source), source)

    def test_plan_real_rejected_draft_can_edit_under_tier_rules(self):
        path = MODEL.with_name('plan_management.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_check_allow_write_under_validation')
        calls = []
        ns = {'super': lambda: types.SimpleNamespace(_check_allow_write_under_validation=lambda vals: calls.append(vals) or False)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        row = types.SimpleNamespace(ensure_one=lambda: None, state='draft', validation_status='rejected')
        self.assertTrue(ns[method.name](row, {'note': 'corrected'}))
        self.assertEqual(calls, [])
        for vals in ({'state': 'confirmed'}, {'state': 'in_progress'}):
            self.assertFalse(ns[method.name](row, vals))
        for state, status in (('draft', 'waiting'), ('draft', 'pending'), ('draft', 'validated'), ('confirmed', 'rejected'), ('done', 'validated')):
            row.state, row.validation_status = state, status
            self.assertFalse(ns[method.name](row, {'note': 'changed'}))

    def test_diary_reviewed_content_is_frozen_but_rejected_and_legacy_rules_remain(self):
        path = MODEL.with_name('construction_diary.py')
        method = next(n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name == 'write')
        token, writes = object(), []
        ns = {'UserError': ValueError, '_': lambda text: text, '_DOCUMENT_STATE_TOKEN': token,
              'super': lambda: types.SimpleNamespace(write=lambda vals: writes.append(dict(vals)) or True)}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        class Rows(list): pass
        row = types.SimpleNamespace(source_origin='manual', state='draft', validation_status='no')
        rows = Rows([row]); rows.env = types.SimpleNamespace(context={'sc_document_state_token': True, 'skip_validation_check': True})
        for state, status in (('draft', 'waiting'), ('draft', 'pending'), ('draft', 'validated'), ('confirmed', 'no'), ('done', 'validated'), ('cancel', 'no')):
            row.state, row.validation_status = state, status
            for vals in ({'project_id': 11}, {'title': 'replaced'}, {'description': 'rewritten'}, {'note': 'changed'},
                         {'attachment_ids': [(5, 0, 0)]}, {'date_diary': '2026-10-01'}, {'active': False}):
                with self.subTest(state=state, status=status, vals=vals), self.assertRaises(ValueError): ns['write'](rows, vals)
        self.assertEqual(writes, [])
        row.state, row.validation_status = 'draft', 'rejected'
        self.assertTrue(ns['write'](rows, {'description': 'corrected for resubmission'}))
        row.source_origin, row.state = 'legacy', 'legacy_confirmed'
        self.assertTrue(ns['write'](rows, {'note': 'historical supplement', 'attendance_equipment': 'equipment'}))
        with self.assertRaises(ValueError): ns['write'](rows, {'description': 'rewrite history'})
        row.source_origin, row.state = 'manual', 'draft'
        rows.env.context = {'sc_document_state_token': token}
        self.assertTrue(ns['write'](rows, {'state': 'confirmed'}))

    def test_diary_business_overlay_preserves_native_editability(self):
        import xml.etree.ElementTree as ET
        root = MODEL.parents[2]
        data = ET.parse(root / 'data/p1_daily_business_form_orchestration_contract_data.xml')
        record = data.find(".//record[@id='business_config_contract_sc_construction_diary_p1_form_business_facts_v1']")
        config = ast.literal_eval(record.find("field[@name='contract_json']").attrib['eval'])
        fields_by_name = {item['name']: item for item in config['view_orchestration']['views']['form']['fields']}
        for name in ('project_id', 'date_diary', 'title', 'description', 'manpower_count', 'weather', 'attachment_ids'):
            self.assertNotIn('readonly', fields_by_name[name], name)
        for name in ('state', 'name', 'create_date'):
            self.assertTrue(fields_by_name[name]['readonly'])
        native = ET.parse(root / 'views/core/construction_diary_views.xml')
        for name in ('project_id', 'title', 'description'):
            field = native.find(".//record[@id='view_sc_construction_diary_form']//field[@name='%s']" % name)
            self.assertEqual(field.attrib['readonly'], "state == 'legacy_confirmed'")

    def test_diary_configuration_and_real_approval_precede_completion(self):
        path = MODEL.parent / 'construction_diary.py'
        names = {'action_confirm', 'action_done', 'action_on_tier_approved'}
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in names]
        namespace = {'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
        class Diary:
            def __iter__(self): return iter([self])
            def with_context(self, **kw): return self
            def _write_document_state(self, values): self.__dict__.update(values)
            def _check_business_ready(self):
                if not self.ready: raise ValueError('content')
        for configured in (True, False):
            record = Diary()
            record.state, record.ready = 'draft', True
            record.review_ids, record.validation_status = [], 'no'
            gates = []
            record.env = {'sc.approval.policy': types.SimpleNamespace(
                _start_submission_review=lambda rec: configured,
                _assert_submission_approved=lambda rec, states: gates.append(states))}
            with self.assertRaises(ValueError): namespace['action_done'](record)
            namespace['action_confirm'](record)
            self.assertEqual(record.state, 'draft' if configured else 'confirmed')
            if configured:
                namespace['action_on_tier_approved'](record)
                self.assertEqual(record.state, 'draft')
                record.review_ids, record.validation_status = [1], 'pending'
                namespace['action_on_tier_approved'](record)
                self.assertEqual(record.state, 'draft')
                with self.assertRaises(ValueError): namespace['action_done'](record)
                record.validation_status = 'validated'
                namespace['action_on_tier_approved'](record)
                self.assertEqual(record.state, 'confirmed')
            namespace['action_done'](record)
            self.assertEqual(record.state, 'done')
            self.assertEqual(gates, [('confirmed',)])
            record.state, record.ready = 'draft', False
            with self.assertRaises(ValueError): namespace['action_confirm'](record)
            self.assertEqual(record.state, 'draft')

    def test_tax_submission_resolves_amount_before_policy_without_executing(self):
        path = MODEL.parent / 'tax_deduction_registration.py'
        names = {'action_confirm', '_prepare_approval_amounts', '_complete_registration_approval', 'action_on_tier_approved'}
        methods = [n for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name in names]
        namespace = {'UserError': ValueError, '_': lambda text: text}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
        class Record:
            def __iter__(self): return iter([self])
            def ensure_one(self): pass
            def with_context(self, **kw): return self
            def write(self, values): self.__dict__.update(values)
            def _check_deduct_ready(self, require_date=True):
                self.calls.append(('ready', require_date))
                if not self.ready: raise ValueError('invalid invoice')
            def _check_company_contractor_deduction_responsibility_or_raise(self): self.calls.append('responsibility')
            def _snapshot_audit_payload(self): return {'state': self.state}
            def _audit_transition(self, *args, **kw): self.calls.append('audit')
        for name in names: setattr(Record, name, namespace[name])
        for configured in (True, False):
            record = Record()
            record.state, record.ready, record.calls = 'draft', True, []
            record.deduction_amount, record.deduction_tax_amount = 0, 0
            record.invoice_amount_untaxed, record.invoice_tax_amount = 100, 13
            record.review_ids, record.validation_status = [], 'no'
            def start(rec):
                self.assertEqual((rec.deduction_amount, rec.deduction_tax_amount), (100, 13))
                self.assertEqual(rec.calls[-2:], [('ready', False), 'responsibility'])
                return configured
            record.env = {'sc.approval.policy': types.SimpleNamespace(_start_submission_review=start)}
            record.action_confirm()
            self.assertEqual(record.state, 'draft' if configured else 'confirmed')
            self.assertFalse(hasattr(record, 'deduction_confirm_date'))
            if configured:
                record.action_on_tier_approved()
                self.assertEqual(record.state, 'draft')
                record.review_ids, record.validation_status = [1], 'pending'
                record.action_on_tier_approved()
                self.assertEqual(record.state, 'draft')
                record.validation_status = 'validated'
                record.action_on_tier_approved()
                self.assertEqual(record.state, 'confirmed')
            self.assertEqual(record.calls.count('audit'), 1)
            record.state, record.ready = 'draft', False
            with self.assertRaises(ValueError): record.action_confirm()
            self.assertEqual(record.state, 'draft')
            record.deduction_amount, record.deduction_tax_amount = 50, 6
            record._prepare_approval_amounts()
            self.assertEqual((record.deduction_amount, record.deduction_tax_amount), (50, 6))

    def test_tax_threshold_domain_uses_prepared_deduction_amount(self):
        method = next(n for n in ast.walk(ast.parse(POLICY.read_text())) if isinstance(n, ast.FunctionDef) and n.name == '_tier_definition_domain')
        namespace = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(POLICY), 'exec'), namespace)
        domain = namespace['_tier_definition_domain'](
            types.SimpleNamespace(target_model='sc.tax.deduction.registration'),
            types.SimpleNamespace(amount_min=50, amount_max=150))
        self.assertEqual(ast.literal_eval(domain), [('deduction_amount', '>=', 50), ('deduction_amount', '<=', 150)])

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


class PlanReportStateMachineTests(unittest.TestCase):
    def methods(self):
        path = MODEL.with_name('plan_management.py')
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'ScPlanReport')
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
        for method in methods: method.decorator_list = []
        token, calls = object(), []
        ns = {'UserError': ValueError, 'ValidationError': ValueError, '_': lambda text: text,
              '_DOCUMENT_STATE_TOKEN': token, 'fields': types.SimpleNamespace(Date=types.SimpleNamespace(context_today=lambda rec: '2026-10-01')),
              'super': lambda: types.SimpleNamespace(create=lambda vals: calls.append(vals) or True, write=lambda vals: calls.append(vals) or True)}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), ns)
        return ns, token, calls

    def test_external_state_audit_and_default_values_are_not_authority(self):
        ns, token, calls = self.methods()
        row = types.SimpleNamespace(env=types.SimpleNamespace(context={}))
        for name, value in (('state', 'accepted'), ('state', 'submitted'), ('approver_id', 42), ('approved_date', '2026-10-01'), ('reject_reason', 'forged')):
            for context in ({}, {'sc_document_state_token': True}, {'skip_validation_check': True}):
                row.env.context = context
                with self.subTest(name=name, context=context), self.assertRaises(ValueError): ns['create'](row, [{name: value}])
                with self.assertRaises(ValueError): ns['write'](row, {name: value})
            row.env.context = {'default_' + name: value}
            with self.assertRaises(ValueError): ns['create'](row, [{}])
        self.assertEqual(calls, [])
        row.env.context = {}
        self.assertTrue(ns['create'](row, [{'name': 'draft'}]))
        row.env.context = {'sc_document_state_token': token}
        self.assertTrue(ns['write'](row, {'state': 'accepted'}))

    def test_reviewed_content_is_locked_and_rejected_content_editable(self):
        ns, _, calls = self.methods()
        class Rows(list): pass
        rec = types.SimpleNamespace(state='draft', validation_status='no')
        rows = Rows([rec]); rows.env = types.SimpleNamespace(context={})
        for state, status in (('submitted', 'pending'), ('accepted', 'no'), ('accepted', 'validated'), ('rejected', 'pending')):
            rec.state, rec.validation_status = state, status
            for field in ('summary', 'plan_id', 'line_id', 'progress_rate', 'attachment_ids'):
                with self.subTest(state=state, field=field), self.assertRaises(ValueError): ns['write'](rows, {field: 'changed'})
        self.assertEqual(calls, [])
        rec.state, rec.validation_status = 'rejected', 'rejected'
        self.assertTrue(ns['write'](rows, {'summary': 'corrected'}))

    def test_submission_uses_shared_policy_and_does_not_invent_approver(self):
        ns, _, _ = self.methods()
        class Rows(list): pass
        class Report:
            state = 'draft'
            def _check_plan_anchor(self): pass
            def _write_document_state(self, vals): self.__dict__.update(vals)
            def with_context(self, **kw): return self
        for configured in (False, True):
            rec = Report(); rows = Rows([rec])
            rows.env = {'sc.approval.policy': types.SimpleNamespace(_start_submission_review=lambda rec: configured)}
            self.assertTrue(ns['action_submit'](rows))
            self.assertEqual(rec.state, 'submitted' if configured else 'accepted')
            self.assertFalse(rec.approver_id)
            self.assertEqual(rec.approved_date, False if configured else '2026-10-01')
            with self.assertRaises(ValueError): ns['action_submit'](rows)
        rec = Report(); rec.line_id = types.SimpleNamespace(plan_id=2); rec.plan_id = 1
        with self.assertRaises(ValueError): ns['_check_plan_anchor']([rec])

    def test_callbacks_require_real_terminal_review(self):
        ns, _, _ = self.methods()
        for state, reviews, status in (('draft', [], 'validated'), ('submitted', [], 'validated'), ('submitted', [1], 'pending'), ('accepted', [1], 'validated')):
            rec = types.SimpleNamespace(state=state, review_ids=reviews, validation_status=status)
            ns['action_on_tier_approved']([rec]); ns['action_on_tier_rejected']([rec])
            self.assertEqual(rec.state, state)

    def test_native_report_replaces_mirror_without_losing_fields_or_audit_guards(self):
        import xml.etree.ElementTree as ET
        root = MODEL.parents[2]
        view = ET.parse(root / 'views/core/plan_management_views.xml').find(".//record[@id='view_sc_plan_report_form']/field[@name='arch']/form")
        self.assertEqual({b.get('name') for b in view.findall('./header/button')}, {'action_submit', 'validate_tier', 'reject_tier'})
        for name in ('approver_id', 'approved_date', 'reject_reason', 'state'):
            self.assertEqual(view.find(".//field[@name='%s']" % name).get('readonly'), '1')
        for name in ('legacy_fact_model', 'legacy_fact_id', 'legacy_fact_type', 'source_created_by', 'source_created_at', 'active'):
            self.assertIsNotNone(view.find(".//field[@name='%s']" % name))
        config = ET.parse(root / 'data/construction_plan_form_productization_contract.xml')
        record = config.find(".//record[@id='business_config_contract_construction_plan_report_productized_form_v1']")
        payload = ast.literal_eval(record.find("field[@name='contract_json']").get('eval'))
        self.assertEqual(payload['view_orchestration']['views']['form'], {'title': '计划汇报', 'composition_mode': 'native_semantic_surface'})
        upgrade = next(f for f in config.findall('./function') if 'construction_plan_report_productized' in f[0].get('eval', ''))
        self.assertEqual(ast.literal_eval(upgrade[1].get('eval'))['contract_json'], payload)


if __name__ == '__main__':
    unittest.main()
