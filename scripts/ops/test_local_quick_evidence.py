"""Real temporary Git histories exercise incremental evidence rejection and execution."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import local_quick_evidence as evidence

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('quick_test_fixtures', ROOT / 'scripts/verify/test_local_quick_evidence.py')
fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixtures)
MANIFEST = ['guard.prod.forbid', 'ci.generated_evidence.preflight',
            'security.legacy_credential_guard', 'verify.quick.evidence.unit']


class IncrementalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.LocalQuickEvidenceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.addCleanup(self.fixture.tearDown)
        self.root = self.fixture.root
        with (self.root / '.git/info/exclude').open('a') as handle:
            handle.write('\n.runtime/\n')
        self.fixture.commit_change('make/ci.mk', 'ci.local.quick.run: ' + ' '.join(MANIFEST) + '\n\t@git diff --check\n\t@echo pass\n')
        self.fixture.commit_change('frontend/existing.ts', 'old\n')
        self.source = evidence.git(self.root, 'rev-parse', 'HEAD')
        self.calls = []
        with mock.patch.object(evidence, 'is_linked_worktree', return_value=False):
            self.receipt = evidence.run_quick(self.root, runner=self.runner)
        self.head = self.fixture.commit_change('frontend/existing.ts', 'new\n')
        self.calls.clear()

    def runner(self, command, **kwargs):
        self.calls.append(command)
        with mock.patch.dict(os.environ, kwargs.get('env', {})):
            for kind in evidence.scans.AUTHORITY:
                evidence.scans.record_scan_success(self.root, kind)
        return subprocess.CompletedProcess(command, 0)

    def test_plan_keeps_unscoped_targets_and_reuses_bounded_test(self):
        run, reuse, base = evidence._incremental_plan(self.root, self.head)
        self.assertEqual(MANIFEST[:-1], run)
        self.assertEqual(MANIFEST[-1:], reuse)
        self.assertEqual(self.source, base)

    def test_declared_suite_reaches_shard_plan_and_preserves_execution_source(self):
        suite = 'verify.test.determinism'
        manifest = MANIFEST + [suite]
        declaration = json.loads((ROOT / 'scripts/ops/quick_suite_manifest.json').read_text())
        self.fixture.commit_change('scripts/ops/quick_suite_manifest.json', json.dumps(declaration))
        self.fixture.commit_change('frontend/apps/web/scripts/check.js', 'fixture')
        self.fixture.commit_change('frontend/apps/web/package.json', '{}')
        self.fixture.commit_change('.github/workflows/check.yml', 'fixture')
        self.fixture.commit_change('docs/engineering_convergence/test_inventory.csv', 'fixture')
        source = self.fixture.commit_change('make/ci.mk', 'ci.local.quick.run: ' + ' '.join(manifest) + '\n\t@git diff --check\n')
        with mock.patch.object(evidence, 'is_linked_worktree', return_value=False):
            evidence.run_quick(self.root, runner=self.runner)
        head = self.fixture.commit_change('docs/notes.md', 'bookkeeping')
        run, reused, base = evidence._incremental_plan(self.root, head)
        self.assertIn(suite, reused)
        self.assertNotIn(suite, run)
        self.assertEqual(source, base)
        self.calls.clear()
        with mock.patch.object(evidence, 'is_linked_worktree', return_value=False), \
             mock.patch.object(evidence, '_observe_quick'):
            evidence.run_default(self.root, shards=2, jobs=1, runner=self.runner)
        self.assertFalse(any(suite in command for command in self.calls))
        ledger = json.loads((self.root / '.runtime/evidence-scope/ci.local.quick.json').read_text())
        self.assertEqual(source, ledger['units'][suite]['source'])
        self.assertEqual(evidence.evidence_path(self.root, head), evidence.verify(self.root, head))

    def test_incremental_run_issues_ordinary_verifiable_receipt(self):
        with mock.patch.object(evidence, 'is_linked_worktree', return_value=False):
            path = evidence.run_quick(self.root, runner=self.runner)
        self.assertEqual(['make', '--no-print-directory', '--jobs=1', *MANIFEST[:-1]], self.calls[0])
        self.assertNotIn('targets', json.loads(path.read_text()))
        self.assertEqual(path, evidence.verify(self.root, self.head))
        ledger = json.loads((self.root / '.runtime/evidence-scope/ci.local.quick.json').read_text())
        self.assertEqual(self.source, ledger['units'][MANIFEST[-1]]['source'])
        self.assertEqual(self.head, ledger['units'][MANIFEST[0]]['source'])
        self.assertCountEqual(MANIFEST[:-1], ledger['runs'][-1]['units'])

    def test_linked_execution_uses_registered_authority_wrapper(self):
        with mock.patch.object(evidence, 'is_linked_worktree', return_value=True):
            evidence.run_quick(self.root, runner=self.runner)
        self.assertEqual(['python3', 'scripts/dev/local_dev_frontend_quick.py', '--quick-targets', *MANIFEST[:-1]], self.calls[0])

    def test_primary_default_preserves_sharded_execution(self):
        with mock.patch.object(evidence, 'is_linked_worktree', return_value=False), \
             mock.patch.object(evidence, '_observe_quick'):
            path = evidence.run_default(self.root, shards=2, jobs=1, runner=self.runner)
        self.assertEqual(2, len(self.calls))
        executed = [target for command in self.calls for target in command[2:]]
        self.assertCountEqual(MANIFEST[:-1], executed)
        self.assertEqual(path, evidence.verify(self.root, self.head))
        composition = json.loads((evidence.shard_root(self.root, self.head) / 'composition.json').read_text())
        self.assertEqual(MANIFEST[-1:], composition['reused_targets'])
        self.assertEqual(self.source, composition['reuse_source'])

    def test_shard_composition_revalidates_reuse_proof(self):
        with mock.patch.object(evidence, 'is_linked_worktree', return_value=False):
            for index in range(2):
                evidence.run_shard(self.root, 2, index, runner=self.runner)
        self.receipt.with_suffix('.scope.json').unlink()
        with self.assertRaises(evidence.EvidenceError):
            evidence.compose(self.root, 2, self.head)
        self.assertFalse(evidence.evidence_path(self.root, self.head).exists())

    def test_missing_scan_proofs_never_issue_receipt(self):
        with mock.patch.object(evidence, 'is_linked_worktree', return_value=False):
            with self.assertRaises(evidence.EvidenceError):
                evidence.run_quick(self.root, runner=lambda command, **kwargs: subprocess.CompletedProcess(command, 0))
        self.assertFalse(evidence.evidence_path(self.root, self.head).exists())

    def test_failed_target_never_issues_receipt(self):
        with mock.patch.object(evidence, 'is_linked_worktree', return_value=False):
            with self.assertRaises(evidence.QuickRunFailed):
                evidence.run_quick(self.root, runner=lambda command, **kwargs: subprocess.CompletedProcess(command, 7))
        self.assertFalse(evidence.evidence_path(self.root, self.head).exists())

    def test_invalid_source_receipt_falls_back_to_full_execution(self):
        original = self.receipt.read_text()
        for field, value in [('suite', 'other'), ('tree', 'f'*40), ('producer', 'other'),
                             ('schema_version', 2), ('coverage', {}), ('head', self.head)]:
            with self.subTest(field=field):
                payload = json.loads(original)
                payload[field] = value
                self.receipt.write_text(json.dumps(payload))
                self.assertIsNone(evidence._incremental_plan(self.root, self.head))
        self.receipt.write_text('[]')
        self.assertIsNone(evidence._incremental_plan(self.root, self.head))

    def test_missing_or_tampered_scope_cannot_reuse(self):
        sidecar = self.receipt.with_suffix('.scope.json')
        original = json.loads(sidecar.read_text())
        for key, value in [('receipt_sha256', 'wrong'), ('document', {})]:
            payload = dict(original)
            payload[key] = value
            sidecar.write_text(json.dumps(payload))
            self.assertIsNone(evidence._incremental_plan(self.root, self.head))
        sidecar.unlink()
        self.assertIsNone(evidence._incremental_plan(self.root, self.head))

    def test_environment_drift_forces_full_run(self):
        with mock.patch.dict(os.environ, {'QUICK_TEST_NEW_INPUT': 'changed'}):
            self.assertIsNone(evidence._incremental_plan(self.root, self.head))

    def test_recipe_change_forces_full_run(self):
        head = self.fixture.commit_change('make/ci.mk', (self.root / 'make/ci.mk').read_text() + '\n# changed recipe authority\n')
        self.assertIsNone(evidence._incremental_plan(self.root, head))

    def test_unreproduced_root_recipe_is_rejected(self):
        with mock.patch.object(evidence, 'declared_quick_recipe', return_value=['python3 extra.py']), \
             mock.patch.object(evidence, 'is_linked_worktree', return_value=False):
            with self.assertRaises(evidence.EvidenceError):
                evidence.run_quick(self.root, runner=self.runner)
        self.assertEqual([], self.calls)

    def test_dirty_end_cannot_sign_incremental_success(self):
        def mutate(command, **kwargs):
            result = self.runner(command, **kwargs)
            (self.root / 'frontend/existing.ts').write_text('changed during execution')
            return result
        with mock.patch.object(evidence, 'is_linked_worktree', return_value=False):
            with self.assertRaises(evidence.EvidenceError):
                evidence.run_quick(self.root, runner=mutate)
        self.assertFalse(evidence.evidence_path(self.root, self.head).exists())


if __name__ == '__main__':
    unittest.main()
