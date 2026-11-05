import unittest
import json
import io
import zipfile
import hashlib
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import backend_changed_test_coverage as coverage


class ChangedCoverageTests(unittest.TestCase):
    source = '''from odoo.tests.common import TransactionCase, tagged
@tagged('post_install', '-at_install', 'custom_acceptance')
class TestNavigation(TransactionCase):
    def test_upgrade(self): pass
    def test_delete(self): pass
'''

    def rows(self, module='example'):
        return coverage.inventory(self.source, f'addons/{module}/tests/test_nav.py')

    def test_custom_tag_methods_get_exact_selectors(self):
        self.assertEqual(['/example:TestNavigation.test_upgrade', '/example:TestNavigation.test_delete'],
                         [r['selector'] for r in self.rows()])

    def test_unrelated_nonzero_suite_does_not_prove_changed_tests(self):
        result = coverage.verify_logs(self.rows(), ['odoo.addons.other.tests.test_nav: Starting TestNavigation.test_upgrade ...',
                                                   '0 failed, 0 error(s) of 23 tests'])
        self.assertTrue(all(r['status'] == 'pending' for r in result))

    def test_each_method_requires_execution(self):
        result = coverage.verify_logs(self.rows(), [
            'odoo.addons.example.tests.test_nav: Starting TestNavigation.test_upgrade ...'])
        self.assertEqual(['executed', 'pending'], [r['status'] for r in result])

    def test_skipped_is_not_execution(self):
        result = coverage.verify_logs(self.rows(), [
            'odoo.addons.example.tests.test_nav: Starting TestNavigation.test_upgrade ...\n'
            'TestNavigation.test_upgrade skipped'])
        self.assertEqual('pending', result[0]['status'])

    def test_python_changed_method_requires_verbose_success_identity(self):
        rows = coverage.inventory('import unittest\nclass TestThing(unittest.TestCase):\n def test_one(self): pass\n',
                                  'addons/example/tests/test_python.py')
        self.assertEqual('python', rows[0]['kind'])
        good = 'test_one (test_python.TestThing.test_one) ... ok\n'
        self.assertEqual('executed', coverage.verify_logs(rows, [good])[0]['status'])
        self.assertEqual('pending', coverage.verify_logs(rows, ['Ran 9 tests\nOK'])[0]['status'])
        self.assertEqual('pending', coverage.verify_logs(rows, [good.replace('ok', 'skipped')])[0]['status'])

    def test_managed_methods_cannot_be_proven_by_generic_module_logs(self):
        rows = self.rows(coverage.MANAGED_MODULE)
        log = f'odoo.addons.{coverage.MANAGED_MODULE}.tests.test_nav: Starting TestNavigation.test_upgrade ...'
        self.assertEqual('pending', coverage.verify_logs(rows, [log])[0]['status'])

    def test_managed_acceptance_has_explicit_owner_and_stays_pending(self):
        rows = self.rows(coverage.MANAGED_MODULE)
        self.assertEqual(coverage.MANAGED_TARGET, rows[0]['owner'])
        self.assertEqual('pending', rows[0]['status'])

    def test_whole_pr_base_not_last_commit_is_used(self):
        with patch.object(coverage.impact, 'git', side_effect=[
                'addons/example/tests/test_nav.py', self.source]) as git:
            self.assertEqual(2, len(coverage.changed_tests('base', 'head')))
        self.assertIn('base', git.call_args_list[0].args)
        self.assertIn('head', git.call_args_list[0].args)


class ManagedEvidenceTests(unittest.TestCase):
    def fixture(self):
        head = 'a' * 40
        repo = {'id': coverage.receipts.REPOSITORY_ID, 'full_name': coverage.receipts.REPOSITORY}
        run = {'id': 42, 'repository': repo, 'head_repository': repo, 'head_sha': head,
               'conclusion': 'success', 'status': 'completed', 'run_attempt': 1,
               'path': '.github/workflows/frontend_release_gate.yml'}
        report = {'schema': 'managed-changed-tests/v1', 'head': head, 'owner': coverage.MANAGED_TARGET,
                  'log_sha256': 'b' * 64, 'executed': ['/example:Test.test_one']}
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('managed-test-evidence.json', json.dumps(report))
        raw = buffer.getvalue()
        artifact = {'id': 17, 'name': f'managed-orm-42-1-{head}', 'expired': False,
                    'digest': 'sha256:' + hashlib.sha256(raw).hexdigest(),
                    'workflow_run': {'id': 42, 'head_sha': head, 'repository_id': repo['id'],
                                     'head_repository_id': repo['id']}}
        return head, run, artifact, raw

    def test_scheduled_evidence_binds_slot_across_midnight_and_rejects_prior_day(self):
        head, run, artifact, raw = self.fixture()
        slot = coverage.scheduled_slot('2026-11-04T23:51:01Z')
        run.update(event='schedule', created_at='2026-11-05T01:08:23Z')
        self.assertEqual(17, coverage.authenticate_managed_report(
            head, run, artifact, raw, schedule_slot=slot)['artifact_id'])
        for event, timestamp in [('schedule', '2026-11-03T23:51:01Z'),
                                 ('workflow_dispatch', '2026-11-04T23:51:01Z')]:
            run.update(event=event, created_at=timestamp)
            with self.assertRaises(ValueError):
                coverage.authenticate_managed_report(head, run, artifact, raw, schedule_slot=slot)

    def test_scheduled_cli_passes_observed_slot_to_managed_discovery(self):
        import os
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = coverage.inventory(ChangedCoverageTests.source, f'addons/{coverage.MANAGED_MODULE}/tests/test_nav.py')[0]
            plan = root / 'plan.json'
            plan.write_text(json.dumps({'head': 'a' * 40, 'base': '', 'changed_test_coverage': [row]}))
            output = root / 'result.json'
            current = {'head_sha': 'a' * 40, 'event': 'schedule', 'created_at': '2026-11-05T01:08:23Z'}
            args = ['coverage', '--plan', str(plan), '--receipts', str(root), '--output', str(output),
                    '--discover-managed', '--wait-managed-seconds', '7200']
            with patch.object(sys, 'argv', args), patch.dict(os.environ, GITHUB_EVENT_NAME='schedule', GITHUB_RUN_ID='42'), \
                    patch.object(coverage.receipts, 'github_bytes', return_value=json.dumps(current).encode()), \
                    patch.object(coverage, 'discover_managed_evidence', return_value={'executed': [row['selector']]}) as discover:
                coverage.main()
            discover.assert_called_once_with('a' * 40, schedule_slot='2026-11-04T18:30:00+00:00')
            self.assertEqual([], json.loads(output.read_text())['pending'])

    def test_current_successful_managed_evidence_is_bound_to_platform_digest(self):
        head, run, artifact, raw = self.fixture()
        result = coverage.authenticate_managed_report(head, run, artifact, raw)
        self.assertEqual(17, result['artifact_id'])
        self.assertEqual(['/example:Test.test_one'], result['executed'])

    def test_wrong_head_failure_retry_foreign_repo_and_tampering_rejected(self):
        import copy
        for kind in ('head', 'failure', 'retry', 'foreign', 'digest', 'expired'):
            head, run, artifact, raw = self.fixture()
            if kind == 'head': head = 'c' * 40
            if kind == 'failure': run['conclusion'] = 'failure'
            if kind == 'retry': run['run_attempt'] = 2
            if kind == 'foreign': run['head_repository'] = {'full_name': 'foreign', 'id': 1}
            if kind == 'digest': raw += b'tampered'
            if kind == 'expired': artifact['expired'] = True
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                coverage.authenticate_managed_report(head, run, artifact, raw)

    def test_ci_managed_operation_validates_resources_before_and_after_execution(self):
        root = Path(__file__).resolve().parents[2]
        source = (root / 'scripts/ci/frontend_fixture_orm_entry.sh').read_text()
        body = source.split('verify_frozen_frontend_release_ci_identity \"$ROOT_DIR\"', 1)[1]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'scripts/test/frontend_acceptance_fixture_orm.sh'
            target.parent.mkdir(parents=True)
            target.write_text('echo executed\n')
            for status in (0, 1):
                stub = f'validate_frozen_frontend_release_ci_resources() {{ echo validated; return {status}; }};\n'
                result = subprocess.run(['bash', '-ec', stub + body],
                    env={'ROOT_DIR': tmp, 'PATH': '/usr/bin:/bin'}, text=True, capture_output=True)
                self.assertEqual(status, result.returncode)
                self.assertEqual(['validated', 'executed', 'validated'] if status == 0 else ['validated'],
                                 result.stdout.splitlines())

    def test_managed_producer_rejects_errors_zero_and_wrong_head(self):
        with patch.object(coverage.impact, 'git', return_value='a' * 40):
            for log in ('0 failed, 1 error(s) of 10 tests', '0 failed, 0 error(s) of 0 tests', ''):
                with self.assertRaises(ValueError): coverage.managed_report('a' * 40, log)
            with self.assertRaises(ValueError): coverage.managed_report('b' * 40, '0 failed, 0 error(s) of 1 tests')


if __name__ == '__main__':
    unittest.main()
