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
             'action_approve', 'action_set_approved', 'action_on_tier_approved'}
    tree = ast.parse(MODEL.read_text())
    methods = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(methods) == len(names)
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(MODEL), 'exec'), namespace)
    return namespace, names


PRODUCTION, METHODS = load_methods()


class Record:
    _name = 'payment.request'
    display_name = 'approval probe'

    def __init__(self, *, required=True, reviews=None, status='no', state='submit', matching=True):
        self.data = dict(state=state, review_ids=list(reviews or []), validation_status=status,
                         can_review=True, audits=[], messages=[], requests=0, restarts=0,
                         next_status='validated', authorized=True)
        self.company_id = types.SimpleNamespace(id=7)
        self.policy = types.SimpleNamespace(is_approval_required=self.requirement)
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
        rec.env = Env(context={}, company=rec.company_id, policy=rec.policy)
        return rec

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

    def test_legacy_approving_state_uses_same_completed_chain(self):
        rec = self.record(state='approve', reviews=['tier'], status='validated')
        rec.action_set_approved()
        self.assertEqual(rec.state, 'approved')


if __name__ == '__main__':
    unittest.main()
