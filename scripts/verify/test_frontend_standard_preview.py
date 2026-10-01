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

    def test_attachment_cleanup_binds_two_exact_contents(self):
        import base64
        import hashlib
        from scripts.verify.frontend_expense_probe_cleanup import expense_probe_attachment_checksums
        first = {'name': 'first.txt', 'data': base64.b64encode(b'first').decode()}
        second = {'name': 'tpl53-partial-second.txt', 'data': base64.b64encode(b'Rollback-only second attachment').decode()}
        scope = {'filename': first['name'], 'data': first['data'], 'files': [first, second]}
        self.assertEqual(expense_probe_attachment_checksums(scope)[first['name']], hashlib.sha1(b'first').hexdigest())
        self.assertEqual(len(expense_probe_attachment_checksums(scope)), 2)
        for files in [[first], [first, second, second], [second, first],
                      [first, {**second, 'name': 'unowned.txt'}], [first, {**second, 'data': first['data']}]]:
            with self.assertRaises(AssertionError): expense_probe_attachment_checksums({**scope, 'files': files})
        self.assertEqual(len(expense_probe_attachment_checksums({'filename': first['name'], 'data': first['data']})), 1)

    def test_diary_cleanup_rejects_unowned_record_and_scope(self):
        from scripts.verify.frontend_expense_probe_cleanup import validate_diary_probe_target
        from datetime import datetime, timezone
        marker = 'TPL53-DIARY-SAVE-1790807163178'
        scope = {'model': 'sc.construction.diary', 'id': 123, 'request': {
            'vals': {'title': marker, 'project_id': 10, 'description': 'content'}, 'context': {'company_id': 8}}}
        row = {'id': 123, 'title': marker, 'description': 'content', 'project_id': 10, 'company_id': 8,
               'create_uid': 24, 'source_origin': 'manual', 'state': 'confirmed',
               'create_date': datetime.fromtimestamp(1790807163.178 + 10, timezone.utc).replace(tzinfo=None).isoformat()}
        validate_diary_probe_target('sc_frontend_acceptance', scope, row, 24)
        for patch in ({'id': 124}, {'title': 'existing'}, {'description': 'changed'}, {'project_id': 11},
                      {'company_id': 9}, {'create_uid': 1}, {'source_origin': 'legacy'}, {'state': 'done'},
                      {'create_date': '2020-01-01 00:00:00'}):
            with self.assertRaises(AssertionError): validate_diary_probe_target('sc_frontend_acceptance', scope, {**row, **patch}, 24)
        with self.assertRaises(AssertionError): validate_diary_probe_target('sc_dev_demo', scope, row, 24)

    def test_event_cleanup_rejects_unowned_record_and_scope(self):
        from scripts.verify.frontend_expense_probe_cleanup import validate_event_probe_target
        from datetime import datetime, timezone
        marker = 'TPL53-EVENT-SAVE-1790807163178'
        scope = {'model': 'sc.contract.event', 'id': 123, 'projectId': 464, 'request': {
            'vals': {'name': marker, 'project_id': 464, 'description': 'content', 'event_type': 'design_change'}, 'context': {'company_id': 8}}}
        row = {'id': 123, 'name': marker, 'description': 'content', 'project_id': 464, 'company_id': 8,
               'create_uid': 24, 'event_type': 'design_change', 'state': 'approved',
               'create_date': datetime.fromtimestamp(1790807163.178 + 10, timezone.utc).replace(tzinfo=None).isoformat()}
        validate_event_probe_target('sc_frontend_acceptance', scope, row, 24)
        for patch in ({'id': 124}, {'name': 'existing'}, {'description': 'changed'}, {'project_id': 11},
                      {'company_id': 9}, {'create_uid': 1}, {'event_type': 'claim'}, {'state': 'done'},
                      {'create_date': '2020-01-01 00:00:00'}):
            with self.assertRaises(AssertionError): validate_event_probe_target('sc_frontend_acceptance', scope, {**row, **patch}, 24)
        with self.assertRaises(AssertionError): validate_event_probe_target('sc_dev_demo', scope, row, 24)
class PlanReportCleanupTest(unittest.TestCase):
    def test_cleanup_binds_both_records_and_rejects_unowned_data(self):
        from scripts.verify.frontend_expense_probe_cleanup import validate_report_probe_target
        from datetime import datetime, timezone
        marker = 'TPL53-REPORT-SAVE-1790807163178'
        scope = {'model': 'sc.plan.report', 'marker': marker, 'parentId': 24, 'id': 31,
                 'request': {'vals': {'name': marker, 'plan_id': 24, 'summary': 'content'}, 'context': {'company_id': 8}}}
        common = {'company_id': 8, 'create_uid': 32, 'create_date': datetime.fromtimestamp(1790807163.178 + 10, timezone.utc).replace(tzinfo=None).isoformat()}
        report = dict(common, id=31, name=marker, plan_id=24, summary='content', state='accepted')
        parent = dict(common, id=24, name=marker.replace('REPORT-SAVE', 'REPORT-PARENT'), project_id=10, state='draft')
        for row, is_parent in ((report, False), (parent, True)):
            validate_report_probe_target('sc_frontend_acceptance', scope, row, 32, is_parent)
            for patch in ({'id': 99}, {'name': 'unowned'}, {'company_id': 1}, {'create_uid': 1}, {'state': 'submitted'}, {'create_date': '2020-01-01 00:00:00'}):
                with self.subTest(parent=is_parent, patch=patch), self.assertRaises(AssertionError):
                    validate_report_probe_target('sc_frontend_acceptance', scope, {**row, **patch}, 32, is_parent)
            with self.assertRaises(AssertionError): validate_report_probe_target('sc_dev_demo', scope, row, 32, is_parent)
        for patch in ({'plan_id': 99}, {'summary': 'changed'}):
            with self.assertRaises(AssertionError): validate_report_probe_target('sc_frontend_acceptance', scope, {**report, **patch}, 32)

class PlanVersionCleanupTest(unittest.TestCase):
    def test_only_exact_draft_version_is_recoverable(self):
        from scripts.verify.frontend_expense_probe_cleanup import validate_version_probe_target
        from datetime import datetime, timezone
        marker = 'TPL53-REPORT-SAVE-1790807163178'
        scope = {'model': 'sc.plan.report', 'marker': marker, 'versionProbe': True, 'parentId': 24, 'versionId': 31,
                 'versionDefaults': {'version_date': '2026-10-01'}}
        row = {'id': 31, 'version_no': marker.replace('REPORT-SAVE', 'VERSION-SAVE'), 'plan_id': 24, 'state': 'draft',
               'company_id': 8, 'create_uid': 32, 'revision_type': 'adjustment', 'version_date': '2026-10-01',
               'create_date': datetime.fromtimestamp(1790807163.178 + 10, timezone.utc).replace(tzinfo=None).isoformat()}
        validate_version_probe_target('sc_frontend_acceptance', scope, row, 32)
        for patch in ({'id': 99}, {'plan_id': 25}, {'version_no': 'existing'}, {'state': 'approved'}, {'company_id': 9},
                      {'create_uid': 1}, {'revision_type': 'baseline'}, {'version_date': '2026-10-02'}, {'create_date': '2020-01-01'}):
            with self.subTest(patch=patch), self.assertRaises(AssertionError):
                validate_version_probe_target('sc_frontend_acceptance', scope, {**row, **patch}, 32)
        with self.assertRaises(AssertionError): validate_version_probe_target('sc_dev_demo', scope, row, 32)
        with self.assertRaises(AssertionError): validate_version_probe_target('sc_frontend_acceptance', {**scope, 'versionProbe': False}, row, 32)

    def test_only_owned_automatic_approval_can_be_restored(self):
        from scripts.verify.frontend_expense_probe_cleanup import validate_version_probe_target
        from datetime import datetime, timezone
        marker = 'TPL53-REPORT-SAVE-1790807163178'
        scope = {'model': 'sc.plan.report', 'marker': marker, 'versionProbe': True, 'versionSubmitProbe': True,
                 'phase': 'version-submit_in_flight', 'parentId': 24, 'versionId': 31, 'versionDefaults': {'version_date': '2026-10-01'}}
        row = {'id': 31, 'version_no': marker.replace('REPORT-SAVE', 'VERSION-SAVE'), 'plan_id': 24, 'state': 'approved',
               'company_id': 8, 'create_uid': 32, 'revision_type': 'adjustment', 'version_date': '2026-10-01',
               'approved_by': False, 'approved_date': '2026-10-01',
               'create_date': datetime.fromtimestamp(1790807163.178 + 10, timezone.utc).replace(tzinfo=None).isoformat()}
        validate_version_probe_target('sc_frontend_acceptance', scope, row, 32)
        for patch in ({'versionSubmitProbe': False}, {'phase': 'version-save'}, {'versionId': 32}):
            with self.assertRaises(AssertionError): validate_version_probe_target('sc_frontend_acceptance', {**scope, **patch}, row, 32)
        for patch in ({'approved_by': 32}, {'approved_date': '2026-09-30'}, {'state': 'pending'}, {'id': 32}):
            with self.assertRaises(AssertionError): validate_version_probe_target('sc_frontend_acceptance', scope, {**row, **patch}, 32)

class PlanExecutionCleanupTest(unittest.TestCase):
    def test_node_cleanup_rejects_foreign_or_unexpected_execution(self):
        from scripts.verify.frontend_expense_probe_cleanup import validate_plan_node_probe_target
        from datetime import datetime, timezone
        marker = 'TPL53-REPORT-SAVE-1790807163178'
        scope = {'model': 'sc.plan.report', 'marker': marker, 'planExecutionProbe': True, 'parentId': 24, 'nodeId': 31}
        row = {'id': 31, 'name': marker.replace('REPORT-SAVE', 'PLAN-NODE'), 'plan_id': 24, 'create_uid': 32,
               'state': 'done', 'progress_rate': 100,
               'create_date': datetime.fromtimestamp(1790807163.178 + 10, timezone.utc).replace(tzinfo=None).isoformat()}
        validate_plan_node_probe_target('sc_frontend_acceptance', scope, row, 32)
        for patch in ({'id': 99}, {'plan_id': 25}, {'name': 'existing'}, {'create_uid': 1}, {'state': 'cancel'},
                      {'progress_rate': 50}, {'create_date': '2020-01-01'}):
            with self.assertRaises(AssertionError): validate_plan_node_probe_target('sc_frontend_acceptance', scope, {**row, **patch}, 32)
        with self.assertRaises(AssertionError): validate_plan_node_probe_target('sc_dev_demo', scope, row, 32)
        with self.assertRaises(AssertionError): validate_plan_node_probe_target('sc_frontend_acceptance', {**scope, 'versionProbe': True}, row, 32)


class VersionReviewRecoveryIdentityTest(unittest.TestCase):
    def test_policy_recovery_is_exact_and_never_replaces_an_existing_configuration(self):
        from datetime import datetime, timezone
        from scripts.verify.frontend_expense_probe_cleanup import validate_version_review_policy
        marker = 'TPL53-REPORT-SAVE-1790816000000'
        scope = {'model': 'sc.plan.report', 'marker': marker, 'versionReviewProbe': True,
                 'versionProbe': True, 'versionSubmitProbe': True, 'approvalPolicyId': 17}
        row = {'id': 17, 'code': 'low_code_sc_plan_version_company_8', 'target_model': 'sc.plan.version',
               'company_id': 8, 'create_uid': 34, 'approval_required': True, 'mode': 'single', 'trigger': 'submit',
               'manager_scope_key': 'executive', 'active': True,
               'create_date': datetime.fromtimestamp(1790816000, timezone.utc).replace(tzinfo=None).isoformat()}
        validate_version_review_policy('sc_frontend_acceptance', scope, row)
        for patch in ({'id': 18}, {'company_id': 9}, {'create_uid': 1}, {'target_model': 'sc.plan'},
                      {'code': 'existing'}, {'mode': 'linear'}, {'manager_scope_key': 'business_admin'},
                      {'approval_required': False}, {'active': False}, {'create_date': '2020-01-01 00:00:00'}):
            with self.subTest(patch=patch), self.assertRaises(AssertionError):
                validate_version_review_policy('sc_frontend_acceptance', scope, {**row, **patch})
        for patch in ({'versionReviewProbe': False}, {'versionProbe': False}, {'versionSubmitProbe': False},
                      {'planExecutionProbe': True}, {'marker': 'existing'}, {'model': 'sc.expense.claim'}):
            with self.subTest(patch=patch), self.assertRaises(AssertionError):
                validate_version_review_policy('sc_frontend_acceptance', {**scope, **patch}, row)
        with self.assertRaises(AssertionError):
            validate_version_review_policy('sc_dev_demo', scope, row)

    def test_configured_version_cleanup_requires_actual_declared_reviewer(self):
        from datetime import datetime, timezone
        from scripts.verify.frontend_expense_probe_cleanup import validate_version_probe_target
        date = datetime.fromtimestamp(1790816000, timezone.utc).replace(tzinfo=None)
        marker = 'TPL53-REPORT-SAVE-1790816000000'
        scope = {'model': 'sc.plan.report', 'marker': marker, 'versionReviewProbe': True, 'versionProbe': True,
                 'versionSubmitProbe': True, 'phase': 'version-approve_in_flight', 'parentId': 24, 'versionId': 31,
                 'approvalBaseline': {'reviewer_id': 28}, 'versionDefaults': {'version_date': str(date.date())}}
        row = {'id': 31, 'version_no': marker.replace('REPORT-SAVE', 'VERSION-SAVE'), 'plan_id': 24,
               'company_id': 8, 'create_uid': 32, 'state': 'approved', 'revision_type': 'adjustment',
               'version_date': str(date.date()), 'approved_date': str(date.date()), 'approved_by': 28,
               'create_date': date.isoformat()}
        validate_version_probe_target('sc_frontend_acceptance', scope, row, 32)
        for patch in ({'approved_by': False}, {'approved_by': 34}, {'company_id': 9}, {'plan_id': 25}, {'id': 32}):
            with self.subTest(patch=patch), self.assertRaises(AssertionError):
                validate_version_probe_target('sc_frontend_acceptance', scope, {**row, **patch}, 32)
        with self.assertRaises(AssertionError):
            validate_version_probe_target('sc_frontend_acceptance', {**scope, 'versionReviewProbe': False}, row, 32)


class PaymentToggleTransitionTest(unittest.TestCase):
    def setUp(self):
        from copy import deepcopy
        from scripts.verify.frontend_expense_probe_cleanup import validate_payment_toggle_transition
        self.validate = validate_payment_toggle_transition
        self.baseline = {'source': [{'id': 1710, 'amount': 2000}], 'execution_ids': [186], 'ledger': [],
            'policies': [{'id': 18, 'company_id': [8, 'A'], 'target_model': 'sc.payment.execution',
                          'approval_required': True, 'mode': 'single', 'active': True, 'write_date': 'old'},
                         {'id': 20, 'active': True, 'write_date': 'unchanged'}],
            'steps': [{'id': 2187, 'policy_id': [18, 'Policy'], 'active': True, 'tier_definition_id': [2187, 'Definition'],
                       'approval_scope_key': 'finance_manager', 'write_date': 'unchanged'}],
            'definitions': [{'id': 2187, 'active': True, 'company_id': [8, 'A'], 'write_date': 'old'},
                            {'id': 10, 'active': False, 'write_date': 'unchanged'}],
            'callbacks': [{'id': 507, 'groups': [93]}]}
        self.disabled = deepcopy(self.baseline)
        self.disabled['policies'][0].update(approval_required=False, mode='none', write_date='new')
        self.disabled['definitions'][0].update(active=False, write_date='new')

    def test_only_expected_disabled_configuration_is_accepted(self):
        self.assertEqual(self.validate(self.baseline, self.disabled, disabled=True), 2187)
        from copy import deepcopy
        restored = deepcopy(self.baseline)
        restored['policies'][0]['write_date'] = 'restored-now'
        restored['definitions'][0]['write_date'] = 'restored-now'
        self.assertEqual(self.validate(self.baseline, restored, disabled=False), 2187)
        self.assertEqual(self.baseline['policies'][0]['write_date'], 'old')

    def test_rejects_other_changes_and_wrong_phase(self):
        from copy import deepcopy
        for bucket, field, value in [('source', 'amount', 1), ('policies', 'company_id', [1, 'Other']),
                                      ('steps', 'active', False), ('definitions', 'company_id', [1, 'Other']),
                                      ('callbacks', 'groups', [])]:
            changed = deepcopy(self.disabled)
            changed[bucket][0][field] = value
            with self.subTest(bucket=bucket), self.assertRaises(AssertionError):
                self.validate(self.baseline, changed, disabled=True)
        with self.assertRaises(AssertionError): self.validate(self.baseline, self.disabled, disabled=False)
        changed = deepcopy(self.disabled)
        changed['definitions'][1]['write_date'] = 'unrelated-change'
        with self.assertRaises(AssertionError): self.validate(self.baseline, changed, disabled=True)


class PaymentReviewRecoveryScopeTest(unittest.TestCase):
    def setUp(self):
        from scripts.verify.frontend_expense_probe_cleanup import validate_payment_review_probe_target
        from datetime import datetime, timezone
        self.validate = validate_payment_review_probe_target
        stamp = 1790816000000
        marker = f'TPL53-PAYMENT-REVIEW-{stamp}'
        self.scope = {'model': 'sc.payment.execution', 'source': {'id': 1710, 'company_id': 8},
                      'marker': marker, 'id': 200, 'baseline': {'execution_ids': [186]}, 'phase': 'done',
                      'origin': {'source': 'tier.review', 'id': 123}}
        self.row = {'id': 200, 'note': marker, 'payment_request_id': 1710, 'company_id': 8,
                    'create_uid': 44, 'paid_amount': 1, 'source_origin': 'manual', 'state': 'confirmed',
                    'validation_status': 'validated', 'review_ids': [123], 'reviewer_ids': [30],
                    'create_date': datetime.fromtimestamp(stamp / 1000, tz=timezone.utc).isoformat()}

    def test_owned_confirmed_execution_is_recoverable(self):
        self.validate('sc_frontend_acceptance', self.scope, self.row)

    def test_existing_paid_other_actor_source_or_amount_rejected(self):
        for patch in ({'id': 186}, {'state': 'paid'}, {'create_uid': 30}, {'company_id': 1},
                      {'payment_request_id': 30}, {'paid_amount': 2}, {'source_origin': 'legacy'},
                      {'reviewer_ids': [44]}, {'review_ids': [124]}, {'validation_status': 'pending'},
                      {'note': 'pre-existing'}, {'create_date': '2000-01-01T00:00:00'}):
            with self.subTest(patch=patch), self.assertRaises(AssertionError):
                self.validate('sc_frontend_acceptance', self.scope, {**self.row, **patch})

    def test_unknown_scope_or_phase_cannot_authorize_cleanup(self):
        with self.assertRaises(AssertionError):
            self.validate('sc_dev_demo', self.scope, self.row)
        for patch in ({'phase': 'created'}, {'origin': {'source': 'tier.review', 'id': 124}},
                      {'baseline': {'execution_ids': [186, 200]}}, {'source': {'id': 1710, 'company_id': 1}}):
            with self.subTest(patch=patch), self.assertRaises(AssertionError):
                self.validate('sc_frontend_acceptance', {**self.scope, **patch}, self.row)


class PaymentReviewRecoveryExecutionTest(unittest.TestCase):
    def setUp(self):
        PaymentReviewRecoveryScopeTest.setUp(self)
        self.scope['baseline']['definitions'] = []

    def fake_env(self, row_patch=None):
        from unittest.mock import MagicMock
        from types import SimpleNamespace
        env = MagicMock()
        env.cr.dbname = 'sc_frontend_acceptance'
        row = {**self.row, 'state': 'draft', **(row_patch or {})}
        record = MagicMock()
        record._name = 'sc.payment.execution'
        record.__getitem__.side_effect = lambda key: SimpleNamespace(id=row[key]) if key in ('payment_request_id', 'company_id', 'create_uid') else row[key]
        record.id, record.create_date = row['id'], row['create_date']
        for field in ('payment_request_id', 'company_id', 'create_uid'):
            setattr(record, field, SimpleNamespace(id=row[field]))
        record.review_ids.ids = []
        record.review_ids.filtered.return_value.mapped.return_value.ids = []
        record.review_ids.__iter__.return_value = iter([])
        records = MagicMock()
        records.ids = [row['id']]
        records.__len__.return_value = 1
        records.__iter__.side_effect = lambda: iter([record])
        records.exists.return_value = False
        records.mapped.return_value.ids = []
        execution = MagicMock()
        execution.sudo.return_value = execution
        execution.with_context.return_value = execution
        execution.search.return_value = records
        execution.browse.return_value.exists.return_value = False
        users = MagicMock()
        users.sudo.return_value = users
        users.browse.side_effect = lambda uid: SimpleNamespace(active=True, company_id=SimpleNamespace(id=8),
            login={30: 'fixture_role_finance', 44: 'fixture_role_pfl035_finance_user',
                   34: 'fixture_role_config_admin'}[uid])
        attachments = MagicMock()
        attachments.sudo.return_value.search_count.return_value = 0
        reviews = MagicMock()
        reviews.sudo.return_value.browse.return_value.exists.return_value = False
        env.__getitem__.side_effect = {'res.users': users, 'sc.payment.execution': execution,
                                       'ir.attachment': attachments, 'tier.review': reviews}.__getitem__
        return env, records

    def test_native_cleanup_commits_only_after_owned_record_and_baseline_checks(self):
        from scripts.verify.frontend_expense_probe_cleanup import recover_payment_review
        env, records = self.fake_env()
        with patch('scripts.verify.frontend_expense_probe_cleanup.payment_review_baseline', return_value=self.scope['baseline']) as baseline:
            recover_payment_review(env, {**self.scope, 'phase': 'created'})
        records.unlink.assert_called_once()
        env.cr.commit.assert_called_once()
        self.assertEqual(baseline.call_count, 3)

    def test_paid_record_never_reaches_delete_or_commit(self):
        from scripts.verify.frontend_expense_probe_cleanup import recover_payment_review
        env, records = self.fake_env({'state': 'paid'})
        with patch('scripts.verify.frontend_expense_probe_cleanup.payment_review_baseline', return_value=self.scope['baseline']):
            with self.assertRaises(AssertionError): recover_payment_review(env, self.scope)
        records.unlink.assert_not_called()
        env.cr.commit.assert_not_called()


    def test_changed_original_facts_never_reach_delete_or_commit(self):
        from scripts.verify.frontend_expense_probe_cleanup import recover_payment_review
        env, records = self.fake_env()
        with patch('scripts.verify.frontend_expense_probe_cleanup.payment_review_baseline', return_value={'execution_ids': [186, 201]}):
            with self.assertRaises(AssertionError): recover_payment_review(env, self.scope)
        records.unlink.assert_not_called()
        env.cr.commit.assert_not_called()


class PaymentToggleRecoveryExecutionTest(unittest.TestCase):
    def setUp(self):
        from unittest.mock import MagicMock
        baseline_case = PaymentToggleTransitionTest()
        baseline_case.setUp()
        self.baseline, self.disabled = baseline_case.baseline, baseline_case.disabled
        record_case = PaymentReviewRecoveryExecutionTest()
        record_case.setUp()
        self.scope = {**record_case.scope, 'baseline': self.baseline, 'approvalToggle': True, 'phase': 'submitted'}
        self.env, self.records = record_case.fake_env({'state': 'confirmed', 'validation_status': 'no'})
        self.policy = MagicMock()
        self.policy.company_id.id = 8
        self.policy.target_model = 'sc.payment.execution'
        model = MagicMock()
        model.sudo.return_value.browse.return_value.exists.return_value = self.policy
        previous_get = self.env.__getitem__.side_effect
        self.env.__getitem__.side_effect = lambda key: model if key == 'sc.approval.policy' else previous_get(key)

    def recover(self, snapshots):
        from scripts.verify.frontend_expense_probe_cleanup import recover_payment_review
        with patch('scripts.verify.frontend_expense_probe_cleanup.payment_review_baseline', side_effect=snapshots):
            recover_payment_review(self.env, self.scope)

    def test_disabled_policy_allows_own_auto_confirm_and_restores_native_policy(self):
        self.recover([self.disabled, self.baseline, self.baseline])
        self.records.unlink.assert_called_once()
        self.policy.write.assert_called_once_with({'approval_required': True, 'mode': 'single'})
        self.env.cr.commit.assert_called_once()

    def test_scope_flag_alone_cannot_authorize_auto_confirm_cleanup(self):
        with self.assertRaises(AssertionError): self.recover([self.baseline])
        self.records.unlink.assert_not_called()
        self.policy.write.assert_not_called()
        self.env.cr.commit.assert_not_called()

    def test_unrelated_mutation_prevents_delete_and_restore(self):
        from copy import deepcopy
        changed = deepcopy(self.disabled)
        changed['source'][0]['amount'] = 1
        with self.assertRaises(AssertionError): self.recover([changed])
        self.records.unlink.assert_not_called()
        self.policy.write.assert_not_called()
        self.env.cr.commit.assert_not_called()

    def test_failed_disable_with_no_record_needs_no_policy_write(self):
        self.scope['phase'] = 'config_disable_in_flight'
        self.records.ids = []
        self.records.__len__.return_value = 0
        self.records.__iter__.side_effect = lambda: iter([])
        self.recover([self.baseline, self.baseline, self.baseline])
        self.policy.write.assert_not_called()
        self.env.cr.commit.assert_called_once()

    def test_failure_after_disable_before_creation_still_restores_policy(self):
        self.scope['phase'] = 'config_disabled'
        self.records.ids = []
        self.records.__len__.return_value = 0
        self.records.__iter__.side_effect = lambda: iter([])
        self.recover([self.disabled, self.baseline, self.baseline])
        self.policy.write.assert_called_once_with({'approval_required': True, 'mode': 'single'})
        self.env.cr.commit.assert_called_once()

    def test_failed_native_restore_readback_prevents_commit(self):
        with self.assertRaises(AssertionError): self.recover([self.disabled, self.disabled])
        self.policy.write.assert_called_once()
        self.env.cr.commit.assert_not_called()


class SceneEntryRuntimeProbeTest(unittest.TestCase):
    def run_probe(self, missing=False, wrong_database=False):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        path = Path(__file__).with_name('business_config_approval_runtime_smoke.py')
        method = next(n for n in ast.parse(path.read_text()).body
                      if isinstance(n, ast.FunctionDef) and n.name == '_scene_entry_contract_checks')
        method.body = [n for n in method.body if not isinstance(n, ast.ImportFrom)]
        base = MagicMock()
        base.cr.dbname = 'other' if wrong_database else 'sc_frontend_acceptance'
        users = []
        for uid in (30, 37, 37):
            user = MagicMock(id=uid, active=True, company_id=SimpleNamespace(id=8))
            user.__len__.return_value = 1
            users.append(user)
        base.__getitem__.return_value.sudo.return_value.search.side_effect = users
        handler = MagicMock()
        handler.return_value.handle.side_effect = [SimpleNamespace(ok=True, data={
            'navigation': {'route_authority': {'primary_actions': [{'scene_key': key, 'action_id': 51}]}},
            'scene_ready_contract': {'scenes': [] if missing else [{'scene': {'key': key, 'title': 'Declared'},
                'meta': {'target': {'intent': intent}}}]}})
            for key, intent in [('workspace.home', 'workspace.home.enter'),
                                ('dashboard.company', 'dashboard.company.enter'),
                                ('project.management', 'project.dashboard.enter')]]
        namespace = {'_env': lambda: base, 'SystemInitHandler': handler, 'json': json, 'load_scene_configs': lambda actor: []}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        self.base, self.handler = base, handler
        with patch('builtins.print') as output:
            namespace['_scene_entry_contract_checks']()
        self.readbacks = [json.loads(call.args[0].split('=', 1)[1]) for call in output.call_args_list
                          if call.args[0].startswith('SCENE_ENTRY_READBACK=')]

    def test_exact_role_scoped_readback_and_rollback(self):
        self.run_probe()
        self.assertEqual(self.handler.return_value.handle.call_count, 3)
        for call in self.handler.return_value.handle.call_args_list:
            self.assertEqual(call.kwargs['payload']['params']['scene_ready_mode'], 'full')
        self.base.cr.rollback.assert_called_once()
        self.base.cr.commit.assert_not_called()

    def test_reads_canonical_navigation_authority(self):
        self.run_probe()
        self.assertEqual(len(self.readbacks), 3)
        for row in self.readbacks:
            self.assertEqual(row['route_authority']['primary_actions'], [{'scene_key': row['scene'], 'action_id': 51}])

    def test_missing_scene_fails_and_rolls_back(self):
        with self.assertRaises(AssertionError): self.run_probe(missing=True)
        self.base.cr.rollback.assert_called_once()
        self.base.cr.commit.assert_not_called()

    def test_wrong_database_never_calls_startup(self):
        with self.assertRaises(AssertionError): self.run_probe(wrong_database=True)
        self.handler.assert_not_called()


class ConcurrencySourcePreflightTest(unittest.TestCase):
    def run_probe(self, *, database='sc_frontend_acceptance', uid=30):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        path = Path(__file__).with_name('business_config_approval_runtime_smoke.py')
        method = next(n for n in ast.parse(path.read_text()).body
                      if isinstance(n, ast.FunctionDef) and n.name == '_concurrency_source_preflight')
        base = MagicMock()
        base.cr.dbname = database
        user = MagicMock(id=uid, company_id=SimpleNamespace(id=8))
        user.__len__.return_value = 1
        base.__getitem__.return_value.sudo.return_value.search.return_value = user
        namespace = {'_env': lambda: base, 'json': json}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        self.base = base
        with patch('builtins.print') as output:
            namespace['_concurrency_source_preflight']()
        self.output = output

    def test_read_only_does_not_promote_empty_sources_to_concurrency_pass(self):
        self.run_probe()
        self.base.cr.rollback.assert_called_once()
        self.base.cr.commit.assert_not_called()
        self.base.assert_called_once_with(user=30, context={'allowed_company_ids': [8], 'company_id': 8, 'lang': 'zh_CN'})
        self.assertIn('not_a_concurrency_pass', self.output.call_args.args[0])
        for name in ('create', 'write', 'unlink'):
            getattr(self.base.return_value.__getitem__.return_value, name).assert_not_called()

    def test_wrong_database_refused_before_any_access(self):
        with self.assertRaisesRegex(AssertionError, 'wrong concurrency database'):
            self.run_probe(database='other')
        self.base.__getitem__.assert_not_called()

    def test_changed_role_identity_refused_and_rolled_back(self):
        with self.assertRaisesRegex(AssertionError, 'finance identity drift'):
            self.run_probe(uid=99)
        self.base.assert_not_called()
        self.base.cr.rollback.assert_called_once()


class CommittedBusinessConflictProbeTest(unittest.TestCase):
    def prepare(self, *, pgcode='55P03', sql=b'SELECT id FROM project_project FOR UPDATE', retry_message='exhausted', block=True):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        path = Path(__file__).with_name('business_config_approval_runtime_smoke.py')
        method = next(n for n in ast.parse(path.read_text()).body
                      if isinstance(n, ast.FunctionDef) and n.name == '_prove_committed_business_conflict')
        method.body = [n for n in method.body if not isinstance(n, ast.ImportFrom)]
        class BusinessError(Exception): pass
        blocked = Exception('bounded conflict')
        blocked.pgcode = pgcode
        blocked.diag = SimpleNamespace(context='')
        self.base = MagicMock()
        self.base.cr.dbname = 'sc_frontend_acceptance'
        self.cursors = [MagicMock() for _ in range(3)]
        self.actors = [MagicMock(su=False) for _ in range(3)]
        for cursor in self.cursors:
            cursor.__enter__.return_value = cursor
            cursor._obj.query = sql
        self.base.registry.cursor.side_effect = self.cursors
        if block:
            self.actors[1].__getitem__.return_value.browse.return_value.action_submit.side_effect = blocked
        self.actors[2].__getitem__.return_value.browse.return_value.action_submit.side_effect = BusinessError(retry_message)
        namespace = {'api': SimpleNamespace(Environment=MagicMock(side_effect=self.actors)), 'UserError': BusinessError, 'json': json}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
        self.probe = namespace['_prove_committed_business_conflict']
        return self

    def execute(self):
        with patch('builtins.print') as output:
            result = self.probe(self.base, 'payment.request', [10, 11], 'action_submit', ('project_project',), 'exhausted')
        self.output = output
        return result

    def test_committed_winner_then_fresh_retry_denied(self):
        self.prepare()
        result = self.execute()
        self.assertEqual(result['winner_committed'], 10)
        self.assertEqual(result['sqlstate'], '55P03')
        self.assertEqual(result['fresh_retry_denied'], 'exhausted')
        self.cursors[0].commit.assert_called_once()
        self.cursors[1].rollback.assert_called_once()
        self.cursors[2].rollback.assert_called_once()
        self.cursors[1].commit.assert_not_called()
        self.cursors[2].commit.assert_not_called()
        self.assertEqual(self.base.registry.cursor.call_count, 3)

    def test_unblocked_second_writer_refuses_commit(self):
        self.prepare(block=False)
        with self.assertRaisesRegex(AssertionError, 'was not blocked'): self.execute()
        self.cursors[0].commit.assert_not_called()

    def test_other_sql_failure_refuses_commit(self):
        self.prepare(pgcode='23503')
        with self.assertRaisesRegex(AssertionError, 'unexpected concurrency failure'): self.execute()
        self.cursors[0].commit.assert_not_called()

    def test_unrelated_lock_refuses_commit(self):
        self.prepare(sql=b'SELECT id FROM ir_sequence FOR UPDATE')
        with self.assertRaisesRegex(AssertionError, 'unrelated resource'): self.execute()
        self.cursors[0].commit.assert_not_called()

    def test_wrong_retry_business_reason_is_not_success(self):
        self.prepare(retry_message='permission denied')
        with self.assertRaisesRegex(AssertionError, 'unexpected retry refusal'): self.execute()
        self.cursors[2].rollback.assert_called_once()

    def test_wrong_database_refused_before_cursor(self):
        self.prepare()
        self.base.cr.dbname = 'production'
        with self.assertRaises(AssertionError): self.execute()
        self.base.registry.cursor.assert_not_called()

    def test_same_record_cannot_masquerade_as_distinct_transactions(self):
        self.prepare()
        with self.assertRaises(AssertionError):
            self.probe(self.base, 'payment.request', [10, 10], 'action_submit', ('project_project',), 'exhausted')
        self.base.registry.cursor.assert_not_called()

    def test_elevated_actor_refused(self):
        self.prepare()
        self.actors[0].su = True
        with self.assertRaises(AssertionError): self.execute()
        self.cursors[0].commit.assert_not_called()


class OrdinaryRoleCapabilityProbeTest(unittest.TestCase):
    def load_functions(self, **extra):
        path = Path(__file__).with_name('business_config_approval_runtime_smoke.py')
        methods = [node for node in ast.parse(path.read_text()).body
                   if isinstance(node, ast.FunctionDef) and node.name.startswith('_ordinary_pm_')]
        for method in methods:
            method.body = [node for node in method.body if not isinstance(node, ast.ImportFrom)]
        import datetime
        namespace = {'json': json, 'datetime': datetime.datetime, 'timezone': datetime.timezone, **extra}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
        return namespace

    def prepare(self, scope='ordinary-role-safety-plan', database='sc_frontend_acceptance', uid=32,
                elevated=False, missing_supplier=False, create_bid=False, fail_submit=False, fresh_state=None):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        self.base = MagicMock()
        self.base.cr.dbname = database
        metadata = MagicMock(id=uid, share=False, company_id=SimpleNamespace(id=8), company_ids=SimpleNamespace(ids=[8]))
        metadata.__len__.return_value = 1
        self.base.__getitem__.return_value.sudo.return_value.search.return_value = metadata
        self.actor = MagicMock(uid=32, su=elevated, company=SimpleNamespace(id=8))
        self.actor.cr = self.base.cr
        self.base.return_value = self.actor
        self.models = {}
        self.actor.__getitem__.side_effect = lambda model: self.models.setdefault(model, MagicMock())
        self.actor['project.project'].browse.return_value.read.return_value = [{'id': 10, 'company_id': [8, 'A']}]
        bid = MagicMock(id=41)
        bid.read.return_value = [{'id': 41, 'project_id': [10, 'Project']}]
        self.actor['tender.bid'].search.return_value = False if create_bid else bid
        self.actor['tender.bid'].create.return_value = bid
        supplier = MagicMock(id=71)
        supplier.read.return_value = [{'id': 71, 'supplier_rank': 1}]
        self.actor['res.partner'].search.return_value = False if missing_supplier else supplier
        self.fresh = MagicMock(uid=32, su=False, company=SimpleNamespace(id=8))
        self.fresh_cursor = MagicMock()
        self.fresh_cursor.__enter__.return_value = self.fresh_cursor
        self.base.registry.cursor.return_value = self.fresh_cursor
        self.api = SimpleNamespace(Environment=MagicMock(return_value=self.fresh))
        self.ns = self.load_functions(_env=lambda: self.base, api=self.api)
        self.scope = scope
        try:
            spec = self.ns['_ordinary_pm_spec'](scope, 'ITER-PM-UNIT-1234567890123456')
        except AssertionError:
            return self
        self.record = MagicMock(id=501, env=self.actor, state='draft', _name=spec['model'])
        self.record.review_ids = []
        self.record.line_ids.ids = [601]
        self.record.line_ids.__len__.return_value = 1
        self.values = {}
        def create(values):
            self.values.update(values)
            return self.record
        self.actor[spec['model']].create.side_effect = create
        def read(names):
            row = {'id': 501, 'state': self.record.state, 'project_id': [10, 'Project'], 'company_id': [8, 'A'],
                   'create_uid': [32, 'PM'], 'owner_id': [32, 'PM'], 'applicant_id': [32, 'PM'], 'name': 'Native Sequence',
                   'plan_date': '2026-10-01', 'rental_date': '2026-10-01', 'apply_date': '2026-10-01', 'plan_type': 'general',
                   **{key: value for key, value in self.values.items() if key not in ('line_ids', 'project_id')},
                   **spec.get('total', {})}
            for key in ('bid_id', 'supplier_id'):
                if key in row: row[key] = [row[key], 'Source']
            return [{key: row[key] for key in names}]
        self.record.read.side_effect = read
        self.record.line_ids.read.side_effect = lambda names: [{'id': 601, 'create_uid': [32, 'PM'],
            **self.values['line_ids'][0][2]}]
        def submit():
            if fail_submit: raise AssertionError('native submission denied')
            self.record.state = 'approved'
        self.record.action_submit.side_effect = submit
        self.record.action_activate.side_effect = lambda: setattr(self.record, 'state', 'active')
        self.fresh_record = MagicMock(id=501, env=self.fresh)
        self.fresh_record.read.side_effect = lambda names: [{**read(names)[0], **({'state': fresh_state} if fresh_state else {})}]
        self.fresh_record.line_ids = self.record.line_ids
        self.fresh.__getitem__.return_value.browse.return_value = self.fresh_record
        if create_bid:
            source = MagicMock()
            source.read.return_value = [{'id': 41, 'project_id': [10, 'Project'], 'create_uid': [32, 'PM']}]
            def source_read(names):
                return [{'id': 41, 'project_id': [10, 'Project'], 'create_uid': [32, 'PM'],
                         'tender_name': self.actor['tender.bid'].create.call_args.args[0]['tender_name']}]
            source.read.side_effect = source_read
            self.fresh.__getitem__.side_effect = lambda model: SimpleNamespace(browse=lambda _id: source if model == 'tender.bid' else self.fresh_record)
        return self

    def execute(self):
        with patch('builtins.print') as output:
            try:
                self.ns['_ordinary_pm_capability_checks'](self.scope)
            finally:
                self.output = output
                receipts = [json.loads(call.args[0].split('=', 1)[1]) for call in output.call_args_list
                            if call.args[0].startswith('ORDINARY_ROLE_CAPABILITY=')]
                self.receipt = receipts[-1] if receipts else None

    def test_five_scopes_create_as_pm_and_require_fresh_committed_readback(self):
        for suffix in ['safety-plan', 'tender-purchase', 'labor-plan', 'subcontract-plan', 'rental-order']:
            with self.subTest(scope=suffix):
                self.prepare('ordinary-role-' + suffix).execute()
                self.base.assert_called_once_with(user=32, su=False, context={'allowed_company_ids': [8], 'company_id': 8, 'lang': 'zh_CN'})
                self.base.cr.commit.assert_called_once()
                self.api.Environment.assert_called_once_with(self.fresh_cursor, 32,
                    {'allowed_company_ids': [8], 'company_id': 8, 'lang': 'zh_CN'}, su=False)
                self.assertEqual(self.receipt['status'], 'passed')
                self.assertTrue(self.receipt['committed'])
                self.assertTrue(self.receipt['capability_only'])
                self.assertFalse(self.receipt['published_user_journey'])
                self.assertEqual(self.receipt['draft']['record']['state'], 'draft')
                self.assertEqual(self.receipt['committed_readback']['record']['state'], 'active' if suffix == 'rental-order' else 'approved')
                for model in self.models.values(): model.sudo.assert_not_called()
                if suffix == 'rental-order': self.record.action_activate.assert_called_once()
                else: self.record.action_activate.assert_not_called()

    def test_identity_and_unknown_scope_fail_before_business_create(self):
        for options in [{'database': 'production'}, {'uid': 1}, {'elevated': True}, {'scope': 'ordinary-role-other'}]:
            with self.subTest(options=options):
                self.prepare(**options)
                with self.assertRaises(AssertionError): self.execute()
                self.base.cr.commit.assert_not_called()
                self.base.cr.rollback.assert_called_once()
                self.assertFalse(self.receipt['committed'])
                for model in self.models.values(): model.create.assert_not_called()

    def test_missing_supplier_fails_without_elevated_source_creation(self):
        self.prepare('ordinary-role-rental-order', missing_supplier=True)
        with self.assertRaisesRegex(AssertionError, 'no visible supplier'): self.execute()
        self.actor['res.partner'].create.assert_not_called()
        self.record.action_submit.assert_not_called()
        self.base.cr.commit.assert_not_called()

    def test_missing_tender_source_is_created_by_pm_and_persistently_verified(self):
        self.prepare('ordinary-role-tender-purchase', create_bid=True).execute()
        self.actor['tender.bid'].create.assert_called_once()
        self.assertEqual(self.actor['tender.bid'].create.call_args.args[0]['project_id'], 10)
        self.assertEqual(self.receipt['sources_created'][0]['id'], 41)
        self.assertTrue(self.receipt['committed'])

    def test_native_submission_failure_rolls_back_pending_samples(self):
        self.prepare(fail_submit=True)
        with self.assertRaisesRegex(AssertionError, 'native submission denied'): self.execute()
        self.base.cr.commit.assert_not_called()
        self.base.cr.rollback.assert_called_once()
        self.assertEqual(self.receipt['status'], 'failed')
        self.assertFalse(self.receipt['committed'])

    def test_postcommit_readback_mismatch_reports_failure_without_claiming_rollback_of_committed_data(self):
        self.prepare(fresh_state='draft')
        with self.assertRaisesRegex(AssertionError, 'unexpected ordinary-role state'): self.execute()
        self.base.cr.commit.assert_called_once()
        self.assertTrue(self.receipt['committed'])
        self.assertEqual(self.receipt['id'], 501)
        self.assertEqual(self.receipt['status'], 'failed')
        self.assertFalse(any('SMOKE=PASS' in call.args[0] for call in self.output.call_args_list))

    def test_wrong_child_value_cannot_be_promoted_to_pass(self):
        self.prepare('ordinary-role-labor-plan')
        self.record.line_ids.read.side_effect = lambda names: [{'id': 601, 'create_uid': [32, 'PM'], 'work_content': 'unowned', 'planned_qty': 1}]
        with self.assertRaisesRegex(AssertionError, 'child value mismatch'): self.execute()
        self.base.cr.commit.assert_not_called()

    def test_original_scope_marker_and_terminal_are_bounded(self):
        ns = self.load_functions()
        with self.assertRaisesRegex(AssertionError, 'marker'):
            ns['_ordinary_pm_spec']('ordinary-role-safety-plan', 'arbitrary')
        with self.assertRaisesRegex(AssertionError, 'unsupported'):
            ns['_ordinary_pm_spec']('ordinary-role-other', 'ITER-PM-UNIT-1234567890123456')

    def test_wrong_project_company_stops_before_any_create(self):
        self.prepare()
        self.actor['project.project'].browse.return_value.read.return_value = [{'id': 10, 'company_id': [9, 'Other']}]
        with self.assertRaisesRegex(AssertionError, 'PM project prerequisite'): self.execute()
        self.base.cr.commit.assert_not_called()
        for model in self.models.values(): model.create.assert_not_called()

    def test_configured_approval_uses_only_assigned_fixture_identity_and_native_decision(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        class Reviews(list):
            def filtered(self, predicate): return Reviews(row for row in self if predicate(row))
            def mapped(self, name): return SimpleNamespace(ids=[37])
        for authorized in (True, False):
            with self.subTest(authorized=authorized):
                base = MagicMock()
                actor = MagicMock(uid=37, su=False, company=SimpleNamespace(id=8))
                base.return_value = actor
                user = SimpleNamespace(id=37, login='fixture_role_executive', share=False, company_ids=SimpleNamespace(ids=[8]))
                base.__getitem__.return_value.sudo.return_value.search.return_value = [user] if authorized else []
                record = MagicMock(id=501, _name='sc.safety.plan', state='submitted', validation_status='pending')
                review = SimpleNamespace(id=901, status='pending')
                record.review_ids = Reviews([review])
                candidate = actor.__getitem__.return_value.browse.return_value
                candidate.env = actor
                candidate.can_review = True
                def validate():
                    review.status = 'approved'
                    record.state = 'approved'
                    record.validation_status = 'validated'
                candidate.validate_tier.side_effect = validate
                method = self.load_functions()['_ordinary_pm_assigned_review']
                if authorized:
                    decisions = method(base, record)
                    candidate.validate_tier.assert_called_once()
                    base.assert_called_once_with(user=37, su=False, context={'allowed_company_ids': [8], 'company_id': 8, 'lang': 'zh_CN'})
                    self.assertEqual(decisions[0]['uid'], 37)
                    self.assertEqual(decisions[0]['assigned_reviewer_ids'], [37])
                    self.assertFalse(decisions[0]['sudo'])
                    self.assertEqual(decisions[0]['validation_status'], 'validated')
                else:
                    with self.assertRaisesRegex(AssertionError, 'no assigned authorized fixture reviewer'): method(base, record)
                    candidate.validate_tier.assert_not_called()
                    base.assert_not_called()

    def test_unavailable_configured_reviewer_rolls_back_the_whole_pending_sample(self):
        self.prepare()
        def submit(): self.record.state = 'submitted'
        self.record.action_submit.side_effect = submit
        def denied_review(*args): raise AssertionError('no assigned authorized fixture reviewer')
        self.ns['_ordinary_pm_assigned_review'] = denied_review
        with self.assertRaisesRegex(AssertionError, 'no assigned authorized'): self.execute()
        self.base.cr.commit.assert_not_called()
        self.base.cr.rollback.assert_called_once()
        self.assertEqual(self.receipt['submitted']['record']['state'], 'submitted')
        self.assertFalse(self.receipt['committed'])


class PaymentSourcePrepProbeTest(unittest.TestCase):
    def prepare(self, kind='subcontract', database='sc_frontend_acceptance', uid=30, fail_confirm=False, fail_fresh=False):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        import datetime
        path = Path(__file__).with_name('business_config_approval_runtime_smoke.py')
        methods = [node for node in ast.parse(path.read_text()).body if isinstance(node, ast.FunctionDef) and node.name.startswith('_payment_source_prep_')]
        for method in methods: method.body = [node for node in method.body if not isinstance(node, ast.ImportFrom)]
        self.base = MagicMock()
        self.base.cr.dbname = database
        user = MagicMock(id=uid, share=False, company_id=SimpleNamespace(id=8), company_ids=SimpleNamespace(ids=[8]))
        user.__len__.return_value = 1
        self.base.__getitem__.return_value.sudo.return_value.search.return_value = user
        self.actor = MagicMock(uid=30, su=False, company=SimpleNamespace(id=8))
        self.actor.cr = self.base.cr
        self.base.return_value = self.actor
        self.models = {}
        self.actor.__getitem__.side_effect = lambda name: self.models.setdefault(name, MagicMock())
        self.actor['project.project'].browse.return_value.read.return_value = [
            {'id': 592, 'name': 'Rental', 'company_id': [8, 'A']}, {'id': 593, 'name': 'Subcontract', 'company_id': [8, 'A']}]
        self.actor['res.partner'].browse.return_value.read.return_value = [{'id': 71}]
        self.record = MagicMock(id=801, state='draft', env=self.actor)
        self.record.with_env.return_value = self.record
        self.record.action_submit.side_effect = lambda: setattr(self.record, 'state', 'approved')
        def confirm():
            if fail_confirm: raise AssertionError('confirmation denied')
            self.record.state = 'confirmed'
        self.record.action_confirm.side_effect = confirm
        self.cursor = MagicMock()
        self.cursor.__enter__.return_value = self.cursor
        self.base.registry.cursor.return_value = self.cursor
        self.fresh = MagicMock(uid=30, su=False, company=SimpleNamespace(id=8))
        self.fresh_record = MagicMock(id=801, env=self.fresh)
        self.fresh.__getitem__.return_value.browse.return_value = self.fresh_record
        self.api = SimpleNamespace(Environment=MagicMock(return_value=self.fresh))
        self.ns = {'_env': lambda: self.base, 'json': json, 'datetime': datetime.datetime, 'timezone': datetime.timezone,
            'api': self.api, '_ordinary_pm_assigned_review': MagicMock()}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), self.ns)
        self.kind = kind
        if kind not in ('subcontract', 'rental'): return self
        spec = self.ns['_payment_source_prep_spec'](kind)
        self.actor[spec['model']].browse.return_value.read.return_value = [{'id': spec['legacy_id'], 'project_id': [spec['project_id'], 'Project'],
            'company_id': [8, 'A'], spec['partner_field']: [71, 'Supplier']}]
        self.actor[spec['model']].create.return_value = self.record
        self.actor[spec['model']].sudo.return_value.create.return_value = self.record
        self.readback = self.ns['_payment_source_prep_readback']
        def observed(record, spec, marker, partner, state):
            if fail_fresh and record is self.fresh_record: raise AssertionError('fresh mismatch')
            if record is self.record: self.assertEqual(record.state, state)
            return {'record': {'id': 801, 'currency_id': [7, 'CNY'], 'name': marker, 'state': state}, 'line': {'id': 901}, 'unreserved_amount': 100}
        self.ns['_payment_source_prep_readback'] = MagicMock(side_effect=observed)
        return self

    def execute(self):
        with patch('builtins.print') as output:
            try: self.ns['_payment_source_prep_checks'](self.kind)
            finally:
                self.output = output
                self.receipt = json.loads(next(call.args[0].split('=', 1)[1] for call in reversed(output.call_args_list)
                    if call.args[0].startswith('PAYMENT_SOURCE_PREP=')))

    def test_both_sources_use_fixed_projects_native_finance_actions_and_fresh_readback(self):
        for kind, project in [('subcontract', 593), ('rental', 592)]:
            with self.subTest(kind=kind):
                self.prepare(kind).execute()
                self.assertEqual(self.receipt['project_id'], project)
                self.assertEqual(self.receipt['source_id'], 801)
                self.assertEqual(self.receipt['status'], 'passed')
                self.assertTrue(self.receipt['committed'])
                self.assertEqual(self.receipt['currency_id'], 7)
                self.record.action_submit.assert_called_once()
                self.record.action_confirm.assert_called_once()
                self.base.cr.commit.assert_called_once()
                self.api.Environment.assert_called_once_with(self.cursor, 30, {'allowed_company_ids': [8], 'company_id': 8, 'lang': 'zh_CN'}, su=False)
                for name, model in self.models.items():
                    if kind == 'rental' and name == 'sc.material.rental.settlement': model.sudo.assert_called_once_with()
                    else: model.sudo.assert_not_called()
                self.assertEqual(self.receipt['preparation_sudo'], kind == 'rental')
                self.assertFalse(self.receipt['ordinary_role_create_proof'])
                self.assertFalse(self.receipt['readback_sudo'])
                self.actor['project.project'].create.assert_not_called()
                self.actor['res.partner'].create.assert_not_called()

    def test_invalid_environment_role_or_kind_never_commits(self):
        for options in [{'database': 'production'}, {'uid': 1}, {'kind': 'other'}]:
            with self.subTest(options=options):
                self.prepare(**options)
                with self.assertRaises(AssertionError): self.execute()
                self.base.cr.commit.assert_not_called()
                for model in self.models.values(): model.create.assert_not_called()
                self.assertFalse(self.receipt['committed'])

    def test_registered_project_or_old_source_drift_refuses_creation(self):
        for source in (False, True):
            self.prepare()
            if source:
                self.actor['sc.subcontract.settlement'].browse.return_value.read.return_value[0]['project_id'] = [999, 'Other']
            else:
                self.actor['project.project'].browse.return_value.read.return_value[0]['company_id'] = [9, 'Other']
            with self.assertRaises(AssertionError): self.execute()
            self.actor['sc.subcontract.settlement'].create.assert_not_called()
            self.base.cr.commit.assert_not_called()

    def test_native_failure_rolls_back_but_postcommit_failure_retains_honest_identity(self):
        for options in [{'fail_confirm': True}, {'fail_fresh': True}]:
            with self.subTest(options=options):
                self.prepare(**options)
                with self.assertRaises(AssertionError): self.execute()
                self.assertEqual(self.receipt['status'], 'failed')
                self.assertEqual(self.receipt['source_id'], 801)
                self.assertEqual(self.receipt['committed'], options.get('fail_fresh', False))
                self.base.cr.rollback.assert_called_once()
                self.assertFalse(any('SMOKE=PASS' in call.args[0] for call in self.output.call_args_list))

    def test_readback_rejects_wrong_owner_values_and_consumed_balance(self):
        from unittest.mock import MagicMock
        self.prepare()
        spec = self.ns['_payment_source_prep_spec']('subcontract')
        row = {'id': 801, 'name': 'Marker', 'state': 'confirmed', 'project_id': [593, 'P'], 'company_id': [8, 'A'],
            'create_uid': [30, 'Finance'], 'subcontractor_id': [71, 'S'], 'currency_id': [7, 'CNY'], 'amount_total': 100}
        self.record.read.return_value = [row]
        self.record.line_ids.__len__.return_value = 1
        self.record.line_ids.read.return_value = [{'id': 901, 'create_uid': [30, 'Finance'], 'work_scope': 'Marker', 'qty': 1, 'unit_price': 100}]
        self.record._payment_unreserved_amount.return_value = 100
        self.readback(self.record, spec, 'Marker', 71, 'confirmed')
        for key, value in [('create_uid', [1, 'Admin']), ('project_id', [592, 'Other']), ('amount_total', 99)]:
            original = row[key]; row[key] = value
            with self.assertRaises(AssertionError): self.readback(self.record, spec, 'Marker', 71, 'confirmed')
            row[key] = original
        self.record._payment_unreserved_amount.return_value = 0
        with self.assertRaisesRegex(AssertionError, 'fully unreserved'): self.readback(self.record, spec, 'Marker', 71, 'confirmed')

class PlanVersionDisplayProbeTest(unittest.TestCase):
    def prepare(self, database='sc_frontend_acceptance', uid=32):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        import datetime
        path = Path(__file__).with_name('business_config_approval_runtime_smoke.py')
        methods = [n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef) and n.name.startswith('_plan_version_display_')]
        for method in methods: method.body = [n for n in method.body if not isinstance(n, ast.ImportFrom)]
        self.base = MagicMock(); self.base.cr.dbname = database
        user = MagicMock(id=uid, share=False, company_id=SimpleNamespace(id=8), company_ids=SimpleNamespace(ids=[8]))
        user.__len__.return_value = 1
        self.base.__getitem__.return_value.sudo.return_value.search.return_value = user
        self.actor = MagicMock(uid=32, su=False, company=SimpleNamespace(id=8))
        self.base.return_value = self.actor
        self.models = {}
        self.actor.__getitem__.side_effect = lambda name: self.models.setdefault(name, MagicMock())
        self.actor['project.project'].browse.return_value.read.return_value = [{'id': 10, 'company_id': [8, 'A']}]
        self.actor['sc.plan'].create.return_value.id = 101
        self.actor['sc.plan.version'].create.return_value.id = 102
        self.cursor = MagicMock(); self.cursor.__enter__.return_value = self.cursor
        self.base.registry.cursor.return_value = self.cursor
        self.fresh = MagicMock(uid=32, su=False, company=SimpleNamespace(id=8))
        self.api = SimpleNamespace(Environment=MagicMock(return_value=self.fresh))
        self.handler = MagicMock()
        self.ns = {'_env': lambda: self.base, 'json': json, 'datetime': datetime.datetime, 'timezone': datetime.timezone,
            'api': self.api, 'UiContractV2Handler': self.handler}
        exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), self.ns)
        self.readback = self.ns['_plan_version_display_readback']
        self.ns['_plan_version_display_readback'] = MagicMock(return_value={'display_name': 'verified'})
        return self

    def execute(self):
        with patch('builtins.print') as output:
            try: self.ns['_plan_version_display_checks']()
            finally:
                self.output = output
                self.receipt = json.loads(next(c.args[0].split('=', 1)[1] for c in reversed(output.call_args_list)
                    if c.args[0].startswith('PLAN_VERSION_DISPLAY=')))

    def test_native_draft_only_and_committed_fresh_non_sudo_read(self):
        self.prepare().execute()
        self.assertEqual(self.receipt['status'], 'passed')
        self.assertTrue(self.receipt['committed'])
        self.assertFalse(self.receipt['published_user_journey'])
        self.assertEqual(self.receipt['parent_id'], 101)
        self.assertEqual(self.receipt['version_id'], 102)
        marker = self.receipt['marker']
        self.actor['sc.plan'].create.assert_called_once_with({'name': marker, 'project_id': 10})
        self.actor['sc.plan.version'].create.assert_called_once_with({'plan_id': 101, 'version_no': marker})
        for model in self.models.values():
            model.sudo.assert_not_called()
            model.create.return_value.action_submit.assert_not_called()
        self.base.cr.commit.assert_called_once()
        self.api.Environment.assert_called_once_with(self.cursor, 32, {'allowed_company_ids': [8], 'company_id': 8, 'lang': 'zh_CN'}, su=False)
        self.assertIs(self.ns['_plan_version_display_readback'].call_args_list[1].args[0], self.fresh)

    def test_wrong_database_role_project_or_elevated_actor_refuses_create(self):
        for case in ('database', 'role', 'project', 'sudo'):
            self.prepare(database='wrong' if case == 'database' else 'sc_frontend_acceptance', uid=1 if case == 'role' else 32)
            if case == 'project': self.actor['project.project'].browse.return_value.read.return_value[0]['company_id'] = [9, 'Other']
            if case == 'sudo': self.actor.su = True
            with self.assertRaises(AssertionError): self.execute()
            self.base.cr.commit.assert_not_called()
            self.actor['sc.plan'].create.assert_not_called()
            self.assertFalse(self.receipt['committed'])

    def test_failed_pending_and_committed_readback_receipts_are_honest(self):
        for after_commit in (False, True):
            self.prepare()
            self.ns['_plan_version_display_readback'].side_effect = [{}, AssertionError('fresh mismatch')] if after_commit else AssertionError('pending mismatch')
            with self.assertRaises(AssertionError): self.execute()
            self.assertEqual(self.receipt['status'], 'failed')
            self.assertEqual(self.receipt['committed'], after_commit)
            self.base.cr.rollback.assert_called_once()
            self.assertFalse(any('SMOKE=PASS' in c.args[0] for c in self.output.call_args_list))

    def test_final_contract_and_model_names_are_checked_independently(self):
        self.prepare()
        parent = {'id': 101, 'name': 'Marker', 'project_id': [10, 'P'], 'company_id': [8, 'A'], 'state': 'draft', 'create_uid': [32, 'PM']}
        version = {'id': 102, 'plan_id': [101, 'Marker'], 'version_no': 'Marker', 'display_name': 'Marker',
            'company_id': [8, 'A'], 'state': 'draft', 'create_uid': [32, 'PM']}
        main = {'id': 102, 'version_no': 'Marker', 'display_name': 'Marker'}
        self.actor['sc.plan'].browse.return_value.read.return_value = [parent]
        self.actor['sc.plan.version'].browse.return_value.read.return_value = [version]
        self.handler.return_value.handle.return_value = {'ok': True, 'data': {'dataContract': {'mainData': main}, 'pageInfo': {'pageName': '计划版本'}}}
        result = self.readback(self.actor, 101, 102, 'Marker')
        self.assertEqual(result['page_name'], '计划版本')
        self.handler.assert_called_once_with(self.actor, su_env=self.actor["ir.model"].sudo.return_value.env)
        self.actor["ir.model"].sudo.assert_called_once_with()
        self.actor["sc.plan"].sudo.assert_not_called()
        self.actor["sc.plan.version"].sudo.assert_not_called()
        for row, key, value in [(version, 'display_name', 'sc.plan.version,102'), (main, 'display_name', 'sc.plan.version,102'),
            (main, 'id', 999), (version, 'plan_id', [999, 'Wrong']), (parent, 'create_uid', [1, 'Admin']), (version, 'state', 'approved')]:
            old = row[key]; row[key] = value
            with self.assertRaises(AssertionError): self.readback(self.actor, 101, 102, 'Marker')
            row[key] = old
        self.handler.return_value.handle.return_value = {'ok': False, 'error': {'code': 'ACL_DENIED', 'message': 'metadata denied' + 'x' * 2000}}
        with self.assertRaises(AssertionError) as caught:
            self.readback(self.actor, 101, 102, 'Marker')
        self.assertIn('ACL_DENIED', str(caught.exception))
        self.assertLessEqual(len(str(caught.exception)), 1231)


class DetailStyleBrowserBoundaryTest(unittest.TestCase):
    """Execute the browser tool's pure boundaries, without launching a browser."""
    def run_js(self, body):
        import subprocess
        source = Path('frontend/apps/web/scripts/standard_page_type_browser.mjs').read_text()
        helper = source.split('// Bounded detail-style verification helpers', 1)[1].split('// End bounded detail-style verification helpers.', 1)[0]
        helper = helper[helper.index('function detailStyleScopeIsolated'):]
        completed = subprocess.run(['node', '--input-type=module', '-e', "import assert from 'node:assert/strict';\n" + helper + '\n' + body], text=True, capture_output=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_exact_readonly_scope_rejects_other_probes(self):
        self.run_js("""
const valid={TPL07_SCOPE:'style',TPL52_FAMILY:'detail'};
assert.equal(detailStyleScopeIsolated(valid),true);
for(const patch of [{TPL07_SCOPE:'approval-actions'},{TPL52_FAMILY:'all'},{TPL07_REPORT_SAVE_SUCCESS:'1'},{TPL07_PAYMENT_SOURCE_FLOW:'rental'},{TPL52_UNKNOWN:'x'}]) assert.equal(detailStyleScopeIsolated({...valid,...patch}),false);
""")

    def test_detail_origin_identity_is_declared_and_unique(self):
        self.run_js("""
assert.deepEqual(detailOriginDomain(DETAIL_ORIGIN_FIXTURE),[['name','=','FE-DELIVERY-HARDENING-001'],['company_id','=',8],['state','=','draft']]);
assert.equal(detailOriginRecord([{id:1845,name:'FE-DELIVERY-HARDENING-001'}]).id,1845);
for(const value of [null,undefined,[],[{id:1},{id:2}],'x',{}]) assert.equal(detailOriginRecord(value),null);
""")
        source = Path('frontend/apps/web/scripts/standard_page_type_browser.mjs').read_text()
        detail = source.split('async function detailStyleVisualScope', 1)[1].split('\nasync function styleScope()', 1)[0]
        self.assertNotIn('payment.request/1813', detail)
        self.assertIn('detailOriginDomain(DETAIL_ORIGIN_FIXTURE)', detail)
        self.assertIn('data-form-record="${originId}"', detail)

    def test_relation_requires_explicit_authority_and_nonempty_identity(self):
        self.run_js("""
const field={type:'field',name:'project_id',fieldInfo:{relation_entry:{can_read:true,can_open:true,model:'project.project',menu_id:12,action_id:34}}};
const authority={mainData:{project_id:[10,'Project']},layout:{containerTree:[{children:[field]}]}};
assert.equal(detailRelationCandidates(authority).length,1);
for(const patch of [{can_open:false},{can_read:false},{menu_id:0},{action_id:'34'},{model:'bad/model'}]){const copy=structuredClone(authority);Object.assign(copy.layout.containerTree[0].children[0].fieldInfo.relation_entry,patch);assert.equal(detailRelationCandidates(copy).length,0);}
for(const value of [false,[],[0,'Name'],[10,''],[true,'Name']]) assert.equal(detailRelationCandidates({...authority,mainData:{project_id:value}}).length,0);
""")

    def test_expected_sections_use_contract_boolean_visibility_and_card_ancestry(self):
        self.run_js("""
const authority={containers:[{containerId:'outer',visible:true},{containerId:'hidden',visible:false},{containerId:'book',visible:true}],layout:{containerTree:[{type:'sheet',children:[{type:'group',containerId:'outer',title:'Outer',children:[{type:'group',containerId:'inner',title:'Inner'}]},{type:'group',containerId:'hidden',title:'Hidden'},{type:'notebook',containerId:'book'}]}]}};
assert.deepEqual(detailExpectedSections(authority).expected.map(row=>row.id),['outer','book']);
assert.deepEqual(detailExpectedSections(authority).unknown,[]);
authority.containers=[];assert.equal(detailExpectedSections(authority).unknown.length,3);
""")

    def test_horizontal_geometry_and_missing_whole_section_fail_closed(self):
        self.run_js("""
const metrics={cards:[{official:true,nested:false,bodyCount:1,collapsed:false,body:{height:60},display:'block',rowGap:'normal',headerBodyGap:0,rect:{left:0,right:300,top:0,bottom:100}},{official:true,nested:false,bodyCount:1,collapsed:false,body:{height:60},display:'block',rowGap:'normal',headerBodyGap:0,rect:{left:0,right:300,top:120,bottom:200}}],expectedCount:2,expectedMatched:true,descriptions:[{official:true,owned:true}],facts:[{label:{left:0,right:90,top:10,bottom:30},value:{left:100,right:290,top:10,bottom:30}}],collectionInsideFacts:false,contained:true};
assert.deepEqual(detailGeometryFailures(metrics),[]);
for(const patch of [{expectedCount:3},{expectedMatched:false},{unknownVisibility:['missing']},{collectionInsideFacts:true},{contained:false},{facts:[]},{descriptions:[{official:false,owned:true}]}]) assert.ok(detailGeometryFailures({...metrics,...patch}).length);
for(const change of [m=>m.cards[1].rect.top=90,m=>m.cards[0].nested=true,m=>m.facts[0].label=null,m=>m.facts[0].value={left:0,right:90,top:40,bottom:60}]){const m=structuredClone(metrics);change(m);assert.ok(detailGeometryFailures(m).length);}
""")

    def test_expanded_card_requires_exact_owned_body_geometry(self):
        self.run_js("""
const card={official:true,nested:false,display:'block',rowGap:'normal',headerBodyGap:0,bodyCount:1,collapsed:false,body:{height:60},rect:{left:0,right:300,top:0,bottom:100}};
const metrics={cards:[card,{...card,rect:{left:0,right:300,top:120,bottom:200}}],expectedCount:2,expectedMatched:true,descriptions:[{official:true,owned:true}],facts:[{label:{left:0,right:90,top:10,bottom:30},value:{left:100,right:290,top:10,bottom:30}}],contained:true};
assert.deepEqual(detailGeometryFailures(metrics),[]);
for(const invalid of [{bodyCount:0,body:null,headerBodyGap:null},{bodyCount:2},{body:{height:0}},{body:{height:NaN}}]){
 metrics.cards[0]={...card,...invalid};assert.ok(detailGeometryFailures(metrics).includes('expanded Card owned body geometry'));
}
metrics.cards[0]={...card,header:{height:40},headerBodyGap:null};assert.ok(detailGeometryFailures(metrics).includes('expanded Card header/body geometry'));
metrics.cards[0]={...card,header:{height:0}};assert.ok(detailGeometryFailures(metrics).includes('expanded Card header/body geometry'));
metrics.cards[0]={...card,header:{height:40},headerBodyGap:0};assert.deepEqual(detailGeometryFailures(metrics),[]);
metrics.cards[0]={...card,collapsed:true,header:{height:40},bodyCount:0,body:null,headerBodyGap:null};assert.deepEqual(detailGeometryFailures(metrics),[]);
metrics.cards[0].bodyCount=2;assert.ok(detailGeometryFailures(metrics).includes('expanded Card owned body geometry'));
""")
        source = Path('frontend/apps/web/scripts/standard_page_type_browser.mjs').read_text()
        self.assertIn("body.closest('.t-card')===node", source)
        self.assertNotIn("querySelector(':scope > .t-card__body')", source)

    def test_native_grid_gap_cannot_masquerade_as_official_card_spacing(self):
        self.run_js("""
const card={official:true,nested:false,bodyCount:1,collapsed:false,body:{height:60},display:'grid',rowGap:'12px',headerBodyGap:12,rect:{left:0,right:300,top:0,bottom:100}};
const metrics={cards:[card,{...card,rect:{left:0,right:300,top:120,bottom:200}}],expectedCount:2,expectedMatched:true,descriptions:[{official:true,owned:true}],facts:[{label:{left:0,right:90,top:10,bottom:30},value:{left:100,right:290,top:10,bottom:30}}],contained:true};
assert.ok(detailGeometryFailures(metrics).includes('Card root spacing owned by official driver'));
metrics.cards=metrics.cards.map(card=>({...card,display:'block',rowGap:'normal',headerBodyGap:0}));
assert.deepEqual(detailGeometryFailures(metrics),[]);
metrics.cards[0].headerBodyGap=12;assert.ok(detailGeometryFailures(metrics).includes('Card root spacing owned by official driver'));
""")

    def test_real_theme_and_navigation_wiring_preserves_write_denial(self):
        source = Path('frontend/apps/web/scripts/standard_page_type_browser.mjs').read_text()
        scope = source.split('async function detailStyleVisualScope', 1)[1].split('async function styleScope', 1)[0]
        self.assertIn("page.locator('.theme-switch:visible').click()", scope)
        self.assertNotIn("setAttribute('data-sc-theme", scope)
        self.assertIn('light.background!==dark.background&&light.color!==dark.color', scope)
        self.assertIn('metrics.cards.every(card=>card.background===metrics.themeTokens.surface&&card.color===metrics.themeTokens.text)', scope)
        self.assertIn('await setTheme(initialTheme.mode)', scope)
        self.assertIn('previous?.target.contractResponseIndex ?? -1', scope)
        self.assertIn('await page.goBack()', scope)
        self.assertIn("node.getAttribute('data-section-source-identity')===section.id", scope)
        self.assertIn("!node.getAttribute('data-section-source-identity')", scope)
        self.assertIn('unique-title-and-type-fallback', scope)
        self.assertIn("report.detailVisual.relations.push({ name, status: 'not_run'", scope)
        self.assertIn("detailStyleScopeIsolated(process.env)) && ['execute_button', 'contract.action', 'file.upload']", source)


class StandardListSurfaceAdapterTest(unittest.TestCase):
    def execute_adapter(self, overrides=None, identity_passes=True, backend_passes=True):
        import subprocess
        source = Path('scripts/dev/frontend_acceptance_runtime.sh').read_text()
        self.assertNotIn('\nload_profile\n', source.split('# Exact existing standard-preview adapter inputs;', 1)[0])
        helper = source.split('# Exact existing standard-preview adapter inputs;', 1)[1].split('# End standard list input validation.', 1)[0]
        helper = helper[helper.index('validate_standard_list_surface_inputs()'):]
        dispatch = source.split('command="${1:-preflight}"', 1)[1].split('  standard-list-lowcode)', 1)[0]
        mocks = r'''
set -euo pipefail
ROOT_DIR=/fixture
PROFILE=local
BACKEND_ACCEPTANCE_NAME=fixture
load_profile(){ echo profile >&2; DB_NAME=sc_frontend_acceptance; BASE_URL=http://127.0.0.1:5175; SC_ACCEPTANCE_FIXTURE_PASSWORD=synthetic-test-secret; }
preflight(){ echo preflight >&2; DB_NAME=sc_frontend_acceptance; SC_ACCEPTANCE_FIXTURE_PASSWORD=synthetic-test-secret; }
validate_backend_resource_identity(){ echo backend >&2; BACKEND_RESULT; }
container_env_value(){ if [[ "$2" == SC_SOURCE_REVISION ]]; then printf '%040d' 0; else printf '%040d\n' 0 | sha256sum | cut -d' ' -f1; fi; }
git(){ return 0; }
python3(){ [[ "$2" == identity ]]; echo identity >&2; IDENTITY_RESULT; }
node(){
 [[ "$1" == /fixture/scripts/verify/frontend_list_surface_structure_browser.mjs ]]
 [[ "$SC_ACCEPTANCE_PROFILE" == local && "$SC_ACCEPTANCE_FRONTEND_URL" == http://127.0.0.1:5180 && "$BASE_URL" == "$SC_ACCEPTANCE_FRONTEND_URL" ]]
 [[ "$SC_ACCEPTANCE_DATABASE" == sc_frontend_acceptance && "$E2E_LOGIN" == fixture_role_finance && "$E2E_PASSWORD" == "$SC_ACCEPTANCE_FIXTURE_PASSWORD" ]]
 [[ "$SC_ACCEPTANCE_OPERATION" == readonly && "$SC_ACCEPTANCE_MANAGE_SERVICE" == false && -z "$SC_ACCEPTANCE_BOOTSTRAP_SECRET" ]]
 echo browser >&2
}
'''.replace('BACKEND_RESULT', 'return 0' if backend_passes else 'return 2').replace('IDENTITY_RESULT', 'return 0' if identity_passes else 'return 2')
        env = {'PATH': os.environ['PATH'], **(overrides or {})}
        return subprocess.run(['bash', '-c', mocks + helper + '\ncommand=standard-list-surface-browser\n' + dispatch + '\nesac\n'], env=env, capture_output=True, text=True)

    def test_registered_adapter_binds_preview_and_keeps_gate_order(self):
        result = self.execute_adapter()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr.splitlines(), ['profile', 'preflight', 'backend', 'identity', 'browser'])
        make = Path('make/frontend.mk').read_text()
        target = make.split('verify.frontend.list_surface_structure.browser: guard.prod.forbid', 1)[1].split('\n\n', 1)[0]
        self.assertIn('frontend_acceptance_operation_entry.sh standard-list-surface-browser', target)
        self.assertNotIn('@node ', target)

    def test_conflicting_profiles_urls_databases_and_actor_fail_before_preflight(self):
        for override in [{'SC_ACCEPTANCE_PROFILE':'production'}, {'SC_ACCEPTANCE_RUNTIME_PROFILE':'daily'}, {'BASE_URL':'http://127.0.0.1:5175'},
                         {'SC_ACCEPTANCE_API_URL':'http://elsewhere'}, {'DB_NAME':'sc_dev_demo'}, {'E2E_LOGIN':'admin'}, {'SC_ACCEPTANCE_OPERATION':'isolated-write'},
                         {'SC_ACCEPTANCE_BOOTSTRAP_SECRET':'unexpected'}, {'SC_ACCEPTANCE_MANAGE_SERVICE':'true'}, {'SC_ACCEPTANCE_STORAGE_STATE':'other-state'}]:
            result = self.execute_adapter(override)
            self.assertNotEqual(result.returncode, 0, override)
            self.assertNotIn('\nprofile\n', '\n' + result.stderr)
            self.assertNotIn('preflight', result.stderr)
            self.assertNotIn('browser', result.stderr)

    def test_wrong_password_or_failed_identity_never_starts_browser(self):
        for result in [self.execute_adapter({'E2E_PASSWORD':'wrong'}), self.execute_adapter(identity_passes=False), self.execute_adapter(backend_passes=False)]:
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('browser', result.stderr)

    def test_explicit_matching_inputs_and_password_are_accepted(self):
        result = self.execute_adapter({'SC_ACCEPTANCE_PROFILE':'local','BASE_URL':'http://127.0.0.1:5180','E2E_DB':'sc_frontend_acceptance','E2E_PASSWORD':'synthetic-test-secret'})
        self.assertEqual(result.returncode, 0, result.stderr)


class StandardListSurfaceMakeBoundaryTest(unittest.TestCase):
    def invoke_make(self, overrides=None, arguments=()):
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            capture = Path(directory) / 'operation.json'
            shim = Path(directory) / 'bash'
            shim.write_text("""#!/usr/bin/python3
import json, os, sys
if sys.argv[1:] == ['scripts/dev/frontend_acceptance_operation_entry.sh', 'standard-list-surface-browser']:
    keys = ['ACCEPTANCE_BASE_URL', 'BASE_URL', 'SC_ACCEPTANCE_FRONTEND_URL', 'DB_NAME', 'DB', 'E2E_DB', 'SC_ACCEPTANCE_DATABASE', 'SC_FRONTEND_RELEASE_CI_ENTRY']
    with open(os.environ['SC_TEST_MAKE_CAPTURE'], 'w') as stream:
        json.dump({key:os.environ.get(key) for key in keys}, stream)
else:
    os.execv('/bin/bash', ['/bin/bash', *sys.argv[1:]])
""")
            shim.chmod(0o755)
            env = {'PATH': directory + ':' + os.environ['PATH'], 'HOME': os.environ['HOME'],
                   'SC_TEST_MAKE_CAPTURE': str(capture), **(overrides or {})}
            result = subprocess.run(['make', '--no-print-directory', 'SHELL=/bin/bash',
                'verify.frontend.list_surface_structure.browser', *arguments], env=env,
                capture_output=True, text=True, timeout=30)
            return result, json.loads(capture.read_text()) if capture.exists() else None

    def test_real_make_file_defaults_reach_registered_preview_adapter(self):
        result, receipt = self.invoke_make()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNotNone(receipt)
        for key in ['ACCEPTANCE_BASE_URL', 'BASE_URL', 'SC_ACCEPTANCE_FRONTEND_URL']:
            self.assertEqual(receipt[key], 'http://127.0.0.1:5180')
        for key in ['DB_NAME', 'DB', 'E2E_DB', 'SC_ACCEPTANCE_DATABASE']:
            self.assertEqual(receipt[key], 'sc_frontend_acceptance')
        self.assertEqual(receipt['SC_FRONTEND_RELEASE_CI_ENTRY'], '1')

    def test_real_make_explicit_environment_and_command_inputs_cannot_be_washed(self):
        for key, value in [('ACCEPTANCE_BASE_URL', 'http://127.0.0.1:18081'), ('BASE_URL', 'http://127.0.0.1:5175'),
                           ('DB_NAME', 'sc_dev_demo'), ('DB', 'sc_dev_demo'), ('BD', 'sc_dev_demo')]:
            for overrides, arguments in [({key:value}, ()), ({}, (key + '=' + value,))]:
                with self.subTest(key=key, cli=bool(arguments)):
                    result, receipt = self.invoke_make(overrides, arguments)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('DENY standard list explicit', result.stderr)
                    self.assertIsNone(receipt)

    def test_real_make_matching_explicit_values_are_retained_as_exact_identity(self):
        result, receipt = self.invoke_make({'ACCEPTANCE_BASE_URL':'http://127.0.0.1:5180', 'DB_NAME':'sc_frontend_acceptance'},
            ('BASE_URL=http://127.0.0.1:5180', 'DB=sc_frontend_acceptance'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(receipt['DB_NAME'], 'sc_frontend_acceptance')
        self.assertEqual(receipt['BASE_URL'], 'http://127.0.0.1:5180')
