from __future__ import annotations
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.ops.agent_run_context import (RunError, begin, record, resolve_run, summary,
                                           resume_prompt, delta_paths, dependency_state)


class RunContextTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-q', '-b', 'fix/test')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.write('make/guards.mk', 'verify.test:\n\t@true\n')
        self.write('source/a.py', 'one')
        self.write('tools/test.py', 'tool')
        self.git('add', '.')
        self.git('commit', '-qm', 'baseline')
        self.base = self.git('rev-parse', 'HEAD')
        self.write('.gitignore', '.runtime/\n')
        self.write('.agent/goal.yaml', 'goal: test')
        self.write('record.md', 'record')
        self.run = {'schema_version': 1, 'id': 'TEST', 'branch': 'fix/test',
                    'baseline_sha': self.base, 'status': 'active', 'goal': '.agent/goal.yaml',
                    'record': 'record.md', 'scope': ['source/', 'tools/', '.agent/', '.gitignore', 'record.md'],
                    'environment': {'kind': 'offline'}, 'blockers': [], 'next_exact_step': 'run focused check',
                    'checks': {'unit': {'target': 'verify.test', 'inputs': ['source/', 'tools/test.py'], 'kind': 'offline'}}}
        self.save()
        self.write('.agent/active-runs.json', json.dumps({'schema_version': 1, 'branches': {'fix/test': '.agent/runs/TEST/run.json'}}))
        self.git('add', '.')
        self.git('commit', '-qm', 'register')
        self.write('.runtime/check.log', 'Ran 2 tests\nOK\n')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()

    def write(self, path, text):
        dest = self.root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)

    def save(self):
        self.write('.agent/runs/TEST/run.json', json.dumps(self.run))

    def receipt(self, status='passed', count=2):
        begin(self.root, 'unit')
        record(self.root, 'unit', status, count, '.runtime/check.log')

    def check(self):
        return summary(self.root)['checks']['unit']

    def test_undeclared_kind_is_rejected(self):
        del self.run['checks']['unit']['kind']; self.save()
        with self.assertRaises(RunError): resolve_run(self.root)

    def test_declaration_level_verdict_is_rejected(self):
        for verdict in ('status', 'detail'):
            self.run['checks']['unit'][verdict] = 'PASS'; self.save()
            with self.assertRaises(RunError): resolve_run(self.root)
            del self.run['checks']['unit'][verdict]

    def test_unknown_make_target_is_rejected(self):
        self.run['checks']['unit']['target'] = 'verify.does.not.exist'; self.save()
        with self.assertRaises(RunError): resolve_run(self.root)

    def test_reuse_summary_reports_unreusable_checks(self):
        self.assertEqual(summary(self.root)['check_reuse_summary'], {'not_run': 1})

    def test_direct_branch_resolution(self):
        self.assertEqual(resolve_run(self.root)[1]['id'], 'TEST')
        self.assertEqual(summary(self.root)['status'], 'resolved')

    def test_missing_registration_is_not_pass(self):
        (self.root / '.agent/active-runs.json').unlink()
        self.assertEqual(summary(self.root)['status'], 'unregistered')

    def test_branch_mismatch_rejected(self):
        self.run['branch'] = 'fix/other'; self.save()
        with self.assertRaises(RunError): resolve_run(self.root)

    def test_bad_baseline_rejected(self):
        self.run['baseline_sha'] = '0' * 40; self.save()
        with self.assertRaises(RunError): resolve_run(self.root)

    def test_malformed_index_fails_closed(self):
        self.write('.agent/active-runs.json', '{')
        self.assertIn('reconcile', resume_prompt(self.root))

    def test_completed_or_superseded_run_cannot_begin_or_record(self):
        for status in ('completed', 'superseded'):
            self.run['status'] = status; self.save()
            self.assertEqual(summary(self.root)['status'], 'closed')
            with self.assertRaises(RunError): begin(self.root, 'unit')
            with self.assertRaises(RunError): record(self.root, 'unit', 'passed', 2, '.runtime/check.log')

    def test_malformed_environment_is_reconciliation_not_controller_crash(self):
        self.run['environment'] = 'offline'; self.save()
        self.assertIn('reconcile', resume_prompt(self.root))
        with self.assertRaises(RunError): self.receipt()

    def test_missing_declared_dependency_cannot_issue_reusable_pass(self):
        self.run['checks']['unit']['inputs'].append('missing.py'); self.save()
        with self.assertRaises(RunError): self.receipt()

    def test_whole_repo_and_internal_dependencies_are_rejected_before_scanning(self):
        for path in ('.', './', '.git', '.runtime', '.runtime/agent-runs'):
            self.run['checks']['unit']['inputs'] = [path]; self.save()
            with self.assertRaises(RunError): resolve_run(self.root)

    def test_non_path_input_is_reconciliation_not_crash(self):
        self.run['checks']['unit']['inputs'] = [None]; self.save()
        self.assertIn('reconcile', resume_prompt(self.root))

    def test_no_receipt_is_not_run(self):
        self.assertEqual(self.check()['status'], 'not_run')

    def test_unchanged_pass_reusable_after_doc_commit(self):
        self.receipt()
        self.write('record.md', 'documentation only')
        self.git('add', 'record.md'); self.git('commit', '-qm', 'docs')
        self.assertEqual(self.check()['status'], 'reusable')

    def test_dirty_source_invalidates(self):
        self.receipt(); self.write('source/a.py', 'two')
        self.assertEqual(self.check()['status'], 'stale')

    def test_test_tool_change_invalidates(self):
        self.receipt(); self.write('tools/test.py', 'changed')
        self.assertEqual(self.check()['status'], 'stale')

    def test_new_dependency_child_invalidates(self):
        self.receipt(); self.write('source/b.py', 'new')
        self.assertEqual(self.check()['status'], 'stale')

    def test_deleted_dependency_invalidates(self):
        self.receipt(); (self.root / 'source/a.py').unlink()
        self.assertEqual(self.check()['status'], 'stale')

    def test_missing_log_invalidates(self):
        self.receipt(); (self.root / '.runtime/check.log').unlink()
        self.assertEqual(self.check()['status'], 'stale')

    def test_changed_log_invalidates(self):
        self.receipt(); self.write('.runtime/check.log', 'fake')
        self.assertEqual(self.check()['status'], 'stale')

    def test_failure_cannot_be_reused_as_pass(self):
        self.receipt('failed', 2)
        self.assertEqual(self.check()['status'], 'failed')

    def test_zero_test_rejected(self):
        with self.assertRaises(RunError): self.receipt(count=0)

    def test_environment_change_invalidates(self):
        self.receipt(); self.run['environment']['profile'] = 'different'; self.save()
        self.assertEqual(self.check()['status'], 'stale')

    def test_runtime_receipt_never_auto_reused(self):
        self.run['environment']['kind'] = 'runtime'; self.save(); self.receipt()
        self.assertEqual(self.check()['status'], 'stale')

    def test_input_declaration_change_invalidates(self):
        self.receipt(); self.run['checks']['unit']['inputs'].append('record.md'); self.save()
        self.assertEqual(self.check()['status'], 'stale')

    def test_scope_violation_does_not_authorize_write(self):
        self.write('unowned.txt', 'other')
        result = summary(self.root)
        self.assertEqual(result['status'], 'reconcile')
        self.assertEqual(result['outside_scope'], ['unowned.txt'])
        self.assertFalse(result['write_replay_authorized'])
        with self.assertRaises(RunError): self.receipt()

    def test_path_traversal_rejected(self):
        self.run['record'] = '../other'; self.save()
        with self.assertRaises(RunError): resolve_run(self.root)

    def test_symlink_dependency_rejected(self):
        (self.root / 'source/link').symlink_to('/etc/passwd')
        with self.assertRaises(RunError): dependency_state(self.root, self.run['checks']['unit'])

    def test_intervening_change_cannot_be_recorded(self):
        begin(self.root, 'unit'); self.write('source/a.py', 'changed during test')
        with self.assertRaises(RunError): record(self.root, 'unit', 'passed', 2, '.runtime/check.log')

    def test_record_requires_begin(self):
        with self.assertRaises(RunError): record(self.root, 'unit', 'passed', 2, '.runtime/check.log')

    def test_delta_includes_committed_staged_dirty_untracked_and_rename_both_sides(self):
        self.write('source/committed.py', 'new')
        self.git('add', 'source/committed.py'); self.git('commit', '-qm', 'commit')
        self.git('mv', 'source/a.py', 'source/renamed.py')
        self.write('source/new.py', 'new')
        self.write('tools/test.py', 'dirty')
        changes = delta_paths(self.root, self.base)
        for path in ['source/a.py', 'source/renamed.py', 'source/committed.py', 'source/new.py', 'tools/test.py']:
            self.assertIn(path, changes)

    def test_prompt_is_advisory_and_preserves_next_step(self):
        prompt = resume_prompt(self.root)
        self.assertIn('run focused check', prompt)
        self.assertIn('never authorizes replaying a write', prompt)


if __name__ == '__main__':
    unittest.main()
