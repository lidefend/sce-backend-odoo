from __future__ import annotations
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.ops import validation_delivery_plan as delivery


class EvidencePlanTests(unittest.TestCase):
    def setUp(self):
        self.registry = {'suites': {key: {'entrypoints': ['make verify.' + key]} for key in ('one', 'two')}}
        self.plan = {'required_evidence_suites': ['one', 'two'], 'head_sha': 'a' * 40}

    def test_all_missing_suites_reported_together(self):
        states = delivery.evidence_states(self.registry, self.plan, {}, [])
        self.assertEqual([state['status'] for state in states.values()], ['missing', 'missing'])

    def test_reuse_uses_original_identity_and_authoritative_validator(self):
        manifest = {'head_sha': 'b' * 40, 'suites': {'one': {'status': 'pass'}}}
        with patch.object(delivery.binding, 'suite_owns_path', side_effect=lambda registry, suite, path: path.startswith('source/')), \
             patch.object(delivery.binding, 'validate_suite_record') as validate:
            states = delivery.evidence_states(self.registry, self.plan, manifest, ['docs/change.md'])
        self.assertEqual(states['one']['status'], 'reusable')
        self.assertEqual(validate.call_args.args[2]['bound_head'], 'b' * 40)
        self.assertEqual(states['two']['status'], 'missing')

    def test_dirty_input_invalidates_without_validating_stale_proof(self):
        with patch.object(delivery.binding, 'suite_owns_path', side_effect=lambda registry, suite, path: path.startswith('source/')), \
             patch.object(delivery.binding, 'validate_suite_record') as validate:
            states = delivery.evidence_states(self.registry, self.plan,
                                              {'suites': {'one': {'status': 'pass'}}}, ['source/new.py'])
        self.assertEqual(states['one']['status'], 'affected')
        validate.assert_not_called()

    def test_tampered_or_expired_evidence_is_not_reusable(self):
        with patch.object(delivery.binding, 'suite_owns_path', return_value=False), \
             patch.object(delivery.binding, 'validate_suite_record', side_effect=delivery.binding.BindingError('tampered')):
            states = delivery.evidence_states(self.registry, self.plan, {'suites': {'one': {}}}, [])
        self.assertEqual(states['one']['status'], 'invalid')
        self.assertEqual(states['two']['status'], 'missing')


class PrIdentityTests(unittest.TestCase):
    def test_governance_suite_executes_delivery_tests(self):
        text = (delivery.ROOT / 'make/ci.mk').read_text()
        start = text.index('verify.contract.architecture.suite:')
        dependencies = text[start:].split('\n\n', 1)[0]
        self.assertIn('verify.validation.delivery.unit', dependencies)

    def identity(self):
        return {'number': 7, 'state': 'OPEN', 'isCrossRepository': False, 'headRefOid': 'a' * 40,
                'baseRefOid': 'b' * 40, 'baseRefName': 'main', 'url': 'https://example.invalid/7'}

    def test_foreign_closed_or_wrong_base_is_rejected(self):
        for key, value in [('isCrossRepository', True), ('state', 'CLOSED'), ('baseRefName', 'other'),
                           ('headRefOid', 'c' * 40), ('baseRefOid', 'short')]:
            data = self.identity(); data[key] = value
            with self.subTest(key=key), patch.object(delivery.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(data))):
                with self.assertRaises(delivery.binding.BindingError): delivery.pr_identity('7', 'a' * 40)

    def test_stale_pr_base_rejected_against_live_main(self):
        for live in ('c' * 40, '', 'short'):
            with self.subTest(live=live), patch.object(delivery.subprocess, 'run', side_effect=[
                    subprocess.CompletedProcess([], 0, json.dumps(self.identity())),
                    subprocess.CompletedProcess([], 0, live)]):
                with self.assertRaisesRegex(delivery.binding.BindingError, 'live main'):
                    delivery.pr_identity('7', 'a' * 40)

    def test_current_pr_base_and_live_main_are_accepted(self):
        with patch.object(delivery.subprocess, 'run', side_effect=[
                subprocess.CompletedProcess([], 0, json.dumps(self.identity())),
                subprocess.CompletedProcess([], 0, 'b' * 40 + '\n')]) as run, \
             patch.object(delivery.runs, 'git', return_value='a' * 40):
            self.assertEqual(delivery.pr_identity('7', 'a' * 40), self.identity())
            self.assertIn('repos/{owner}/{repo}/git/ref/heads/main', run.call_args.args[0])

    def test_injected_environment_cannot_override_pr_baseline(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(delivery, 'pr_identity', return_value=self.identity()), \
             patch.object(delivery.runs, 'git', return_value='a' * 40), \
             patch.object(delivery.binding, 'resolve_head'), \
             patch.object(delivery, 'build_report', return_value={'blockers': [], 'status': 'ready_for_existing_gates', 'head': 'a'*40, 'base': 'b'*40, 'candidate_evidence': False, 'limits': []}) as build, \
             patch.dict(os.environ, {'BASE_SHA': 'a' * 40, 'HEAD_SHA': 'c' * 40}):
            result = delivery.main(['--pr', '7', '--expected-head', 'a' * 40, '--base', 'a' * 40,
                                    '--output', str(Path(tmp) / 'plan.json'), '--require-ready'])
        self.assertEqual(result, 0)
        self.assertEqual(build.call_args.args[:2], ('b' * 40, 'a' * 40))

    def test_base_drift_after_quick_blocks_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / 'plan.json'
            before = self.identity(); before['baseRefOid'] = 'c' * 40
            report.write_text(json.dumps({'pr_identity': before}))
            with patch.object(delivery, 'pr_identity', return_value=self.identity()):
                result = delivery.main(['--pr', '7', '--expected-head', 'a' * 40,
                                        '--output', str(report), '--verify-pr-identity'])
            self.assertNotEqual(result, 0)

    def test_parallel_make_never_starts_quick_after_failed_preflight(self):
        # Use the actual target dependency declaration and ordered recipe prefix.
        text = (delivery.ROOT / 'make/codex.mk').read_text()
        start = text.index('pr.merge: guard.prod.forbid pr.merge.preflight')
        block = text[start:text.index("\t@bash -c", start)]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'Makefile').write_text(block + '\nguard.prod.forbid:\n\t@true\n'
                + 'pr.merge.preflight:\n\t@exit 1\n'
                + 'pr.merge.local_quick_gate:\n\t@touch quick-ran\n')
            result = subprocess.run(['make', '-j8', 'pr.merge'], cwd=root, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'quick-ran').exists())


class WorkingTreePlanTests(unittest.TestCase):
    def test_dirty_and_untracked_inputs_are_visible_before_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
            git('init', '-q'); git('config', 'user.name', 'Test'); git('config', 'user.email', 'test@example.invalid')
            (root / 'source.py').write_text('initial')
            git('add', '.'); git('commit', '-qm', 'baseline')
            head = git('rev-parse', 'HEAD')
            (root / 'source.py').write_text('modified')
            (root / 'new.py').write_text('untracked')
            registry = {'schema': delivery.binding.REGISTRY_SCHEMA, 'suites': {
                'runtime': {'entrypoints': ['make verify.example'], 'evidence': {'adapter': 'entry_verify'}}},
                'rules': [{'id': 'code', 'paths': ['*.py'], 'suites': ['runtime']}]}
            with patch.object(delivery, 'ROOT', root), patch.object(delivery.binding, 'ROOT', root), \
                 patch.object(delivery.binding, 'load_registry', return_value=registry):
                report = delivery.build_report(head, head, root / 'absent.json')
            self.assertEqual(report['dirty_paths'], ['new.py', 'source.py'])
            self.assertEqual(report['runtime_evidence']['runtime']['status'], 'affected')
            self.assertFalse(report['candidate_evidence'])


if __name__ == '__main__':
    unittest.main()
