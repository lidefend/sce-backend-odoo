import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile
import json
import hashlib
import ast
import copy


class ExpenseCreateProbeScopeTest(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).with_name('business_config_approval_runtime_smoke.py')
        method = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'validate_expense_create_probe')
        ns = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), ns)
        self.validate = ns['validate_expense_create_probe']
        self.probe = {'request': {'op': 'create', 'model': 'sc.expense.claim', 'vals': {'payment_request_id': 21,
            'project_id': 10, 'partner_id': 56, 'amount': 999, 'attachment_ids': [[6, 0, []]]},
            'context': {'company_id': 8, 'default_business_category_code': 'finance.expense.reimbursement'}},
            'source': {'id': 21, 'project_id': [10, 'P'], 'partner_id': [56, 'Partner'], 'company_id': [8, 'Company'], 'amount': 999, 'type': 'pay'},
            'report_sha256': 'a' * 64}

    def test_bound_request_is_accepted(self):
        self.assertEqual(self.validate(self.probe), self.probe['request'])

    def test_state_and_privilege_inputs_rejected(self):
        for section, key, value in [('vals', 'state', 'approved'), ('context', 'sudo', True), ('context', 'tier_validation_callback', True)]:
            probe = copy.deepcopy(self.probe)
            probe['request'][section][key] = value
            with self.assertRaises(AssertionError): self.validate(probe)

    def test_source_identity_and_attachment_mutation_rejected(self):
        for key, value in [('payment_request_id', 22), ('project_id', 11), ('partner_id', 57), ('amount', 1000), ('attachment_ids', [[4, 123]])]:
            probe = copy.deepcopy(self.probe)
            probe['request']['vals'][key] = value
            with self.assertRaises(AssertionError): self.validate(probe)

spec = importlib.util.spec_from_file_location('preview', Path(__file__).resolve().parents[1] / 'dev/frontend_standard_preview.py')
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class PreviewIdentityTest(unittest.TestCase):
    def setUp(self):
        self.env = {'STATIC_ROOT': str(preview.PREVIOUS), 'STATIC_PORT': '5180', 'API_PROXY_TARGET': 'http://127.0.0.1:18082'}

    def test_registered_previous_can_be_replaced(self):
        self.assertEqual(preview.validate_listener(self.env, 'node scripts/release/release_static_server.mjs', os.getuid()), str(preview.PREVIOUS))

    def test_unrelated_candidate_is_never_stopped(self):
        with self.assertRaises(RuntimeError):
            preview.validate_listener({**self.env, 'STATIC_ROOT': '/other'}, 'node scripts/release/release_static_server.mjs', os.getuid())

    def test_browser_rejects_the_previous_candidate(self):
        with self.assertRaises(RuntimeError):
            preview.validate_listener(self.env, 'node scripts/release/release_static_server.mjs', os.getuid(), current_only=True)

    def test_wrong_proxy_is_never_reused(self):
        with self.assertRaises(RuntimeError):
            preview.validate_listener({**self.env, 'API_PROXY_TARGET': 'http://127.0.0.1:18081'}, 'node scripts/release/release_static_server.mjs', os.getuid())

    def test_other_owner_and_command_rejected(self):
        for command, owner in [('other', os.getuid()), ('node scripts/release/release_static_server.mjs', os.getuid() + 1)]:
            with self.assertRaises(RuntimeError):
                preview.validate_listener(self.env, command, owner)


class ObservedBuildIdentityTest(unittest.TestCase):
    def test_observation_preserves_artifact_checks_but_does_not_claim_current_source(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            dist = output / 'dist'
            dist.mkdir()
            (dist / 'index.html').write_text('index')
            (dist / 'entry.js').write_text('entry')
            receipt = {'base_sha': 'fixed', 'diff_sha256': 'original',
                       'index_sha256': hashlib.sha256(b'index').hexdigest(),
                       'entry': '/entry.js', 'entry_sha256': hashlib.sha256(b'entry').hexdigest()}
            (output / 'build-identity.json').write_text(json.dumps(receipt))
            with patch.object(preview, 'OUTPUT', output), patch.object(preview, 'DIST', dist), patch.object(preview, 'inputs', return_value='changed'):
                with self.assertRaisesRegex(RuntimeError, 'inputs changed'):
                    preview.identity()
                self.assertEqual(preview.identity(observed_only=True), receipt)
                (dist / 'entry.js').write_text('tampered')
                with self.assertRaisesRegex(RuntimeError, 'entry changed'):
                    preview.identity(observed_only=True)


class FavoriteRecoveryIdentityTest(unittest.TestCase):
    def test_recovery_is_exactly_bound(self):
        from scripts.verify.frontend_favorite_probe_recovery import EXPECTED, validate_target
        validate_target('sc_frontend_acceptance', EXPECTED.copy())

    def test_other_database_rejected(self):
        from scripts.verify.frontend_favorite_probe_recovery import EXPECTED, validate_target
        with self.assertRaises(RuntimeError):
            validate_target('sc_dev_demo', EXPECTED.copy())

    def test_every_object_identity_difference_rejected(self):
        from scripts.verify.frontend_favorite_probe_recovery import EXPECTED, validate_target
        for key in EXPECTED:
            with self.subTest(field=key), self.assertRaises(RuntimeError):
                validate_target('sc_frontend_acceptance', {**EXPECTED, key: 'different'})


class CandidateReplacementTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.dist = self.output / 'dist'
        self.old = self.write_candidate(self.dist, 'old')
        self.receipt = self.output / 'build-identity.json'
        self.receipt.write_text(json.dumps(self.old))
        for name, value in [('OUTPUT', self.output), ('DIST', self.dist)]:
            patcher = patch.object(preview, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(preview, 'git', side_effect=lambda *args: b'new' if args[0] == 'rev-parse' else b'')
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_candidate(self, dist, label):
        (dist / 'assets').mkdir(parents=True)
        html = '<script src="/assets/index-%s.js"></script>' % label
        (dist / 'index.html').write_text(html)
        (dist / ('assets/index-%s.js' % label)).write_text(label)
        return {'base_sha': label, 'diff_sha256': label,
                'index_sha256': hashlib.sha256(html.encode()).hexdigest(),
                'entry': '/assets/index-%s.js' % label,
                'entry_sha256': hashlib.sha256(label.encode()).hexdigest()}

    def compile(self, *args, **kwargs):
        # A build must not write into the live preview directory.
        self.assertEqual(preview.identity(observed_only=True), self.old)
        destination = Path(kwargs['env']['FRONTEND_DIST_DIR'])
        self.assertNotEqual(destination, self.dist)
        self.write_candidate(destination, 'new')

    def assert_old(self):
        self.assertEqual(preview.identity(observed_only=True), self.old)
        self.assertEqual(json.loads(self.receipt.read_text()), self.old)

    def test_unchanged_candidate_reuses_without_build(self):
        with patch.object(preview, 'inputs', return_value='old'), patch.object(preview.subprocess, 'run') as run:
            preview.build_candidate()
            run.assert_not_called()
        self.assert_old()

    def test_changed_candidate_builds_once_and_preserves_previous(self):
        with patch.object(preview, 'inputs', return_value='new'), patch.object(preview.subprocess, 'run', side_effect=self.compile) as run:
            preview.build_candidate()
            self.assertEqual(run.call_count, 1)
            self.assertEqual(preview.identity()['base_sha'], 'new')
        backups = list(self.output.glob('previous-*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads((backups[0] / 'build-identity.json').read_text()), self.old)
        self.assertEqual((backups[0] / 'dist/assets/index-old.js').read_text(), 'old')

    def test_failed_compilation_keeps_old_candidate(self):
        with patch.object(preview, 'inputs', return_value='new'), patch.object(preview.subprocess, 'run', side_effect=RuntimeError('compile failed')):
            with self.assertRaisesRegex(RuntimeError, 'compile failed'): preview.build_candidate()
        self.assert_old()

    def test_source_drift_during_build_keeps_old_candidate(self):
        with patch.object(preview, 'inputs', side_effect=['changed', 'new', 'drift']), patch.object(preview.subprocess, 'run', side_effect=self.compile):
            with self.assertRaisesRegex(RuntimeError, 'source changed'): preview.build_candidate()
        self.assert_old()

    def test_corrupt_old_artifact_is_not_silently_replaced(self):
        (self.dist / 'assets/index-old.js').write_text('corrupt')
        with patch.object(preview.subprocess, 'run') as run:
            with self.assertRaisesRegex(RuntimeError, 'entry changed'): preview.build_candidate()
            run.assert_not_called()

    def test_failed_receipt_promotion_restores_old_pair(self):
        replace = os.replace
        def fail_once(source, destination):
            if Path(source).name == 'build-identity.json': raise OSError('receipt promotion failed')
            return replace(source, destination)
        with patch.object(preview, 'inputs', return_value='new'), patch.object(preview.subprocess, 'run', side_effect=self.compile), patch.object(preview.os, 'replace', side_effect=fail_once):
            with self.assertRaisesRegex(OSError, 'receipt promotion failed'): preview.build_candidate()
        self.assert_old()

    def test_post_switch_validation_failure_restores_old_pair(self):
        with patch.object(preview, 'inputs', side_effect=['changed', 'new', 'new', 'drift']), patch.object(preview.subprocess, 'run', side_effect=self.compile):
            with self.assertRaisesRegex(RuntimeError, 'inputs changed'): preview.build_candidate()
        self.assert_old()


class ExpenseBrowserCleanupTest(unittest.TestCase):
    def setUp(self):
        from scripts.verify.frontend_expense_probe_cleanup import validate_expense_probe_target
        self.validate = validate_expense_probe_target
        from datetime import datetime, timezone
        started = 1790802321792
        self.row = dict(id=120, summary='TPL53-EXPENSE-SUCCESS-%s' % started, create_uid=30, company_id=8,
            source_origin='manual', state='approved', project_id=10, partner_id=56, payment_request_id=1815,
            amount=999, payee_account='EXPENSE-SAVE-PAYEE', payer_account='EXPENSE-SAVE-PAYER',
            create_date=datetime.fromtimestamp(started / 1000 + 10, timezone.utc).replace(tzinfo=None).isoformat())
        self.scope = {'id': 120, 'request': {'vals': {key: self.row[key] for key in ['summary', 'project_id', 'partner_id',
            'payment_request_id', 'amount', 'payee_account', 'payer_account']}},
            'source': {'id': 1815, 'project_id': [10, 'Project'], 'partner_id': [56, 'Partner'], 'amount': 999}}

    def test_exact_transient_object(self):
        self.validate('sc_frontend_acceptance', self.scope, self.row)

    def test_other_object_scope_and_terminal_state_denied(self):
        for key, value in [('id', 121), ('state', 'done'), ('create_uid', 1), ('company_id', 9), ('amount', 998),
                           ('summary', 'existing document'), ('source_origin', 'legacy'), ('create_date', '2020-01-01 00:00:00')]:
            with self.assertRaises(AssertionError): self.validate('sc_frontend_acceptance', self.scope, {**self.row, key: value})

    def test_other_database_denied(self):
        with self.assertRaises(AssertionError): self.validate('sc_dev_demo', self.scope, self.row)
