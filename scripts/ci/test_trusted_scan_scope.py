#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trusted_scan_scope as scope
import personal_data_scan as personal
import secret_scan as secrets
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "verify"))
import repository_clean_history_guard as history


class TrustedScopeTests(unittest.TestCase):
    def setUp(self):
        # Hosted runners export GITHUB_EVENT_NAME. Scope selection must be
        # asserted per test instead of inheriting the runner's ambient event.
        ambient_event = mock.patch.dict(os.environ)
        ambient_event.start()
        self.addCleanup(ambient_event.stop)
        os.environ.pop('GITHUB_EVENT_NAME', None)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Scope Test')
        self.git('config', 'user.email', 'scope@example.invalid')
        self.git('remote', 'add', 'origin', 'https://github.com/lidefend/sce-backend-odoo.git')
        for path in set(scope.COMMON_AUTHORITY).union(*scope.AUTHORITY.values()):
            self.write(path, 'baseline authority\n')
        self.write('scripts/ci/trusted_scan_scope.py', Path(scope.__file__).read_text())
        self.write('make/ci.mk', 'ci.local.iteration: guard.prod.forbid\n\t@echo daily\n\nsecurity.secrets.scan: security.online_capture.unit\n\t@python3 scripts/ci/secret_scan.py --scope all --auto-trusted-base\n')
        self.write('old.txt', 'baseline\n')
        self.commit('base')
        self.base = self.git('rev-parse', 'HEAD').strip()
        self.git('update-ref', 'refs/remotes/origin/main', self.base)
        self.receipt = self.root / '.git/codex/evidence/ci.local.quick' / (self.base + '.json')
        self.receipt.parent.mkdir(parents=True)
        self.receipt.write_text(json.dumps(dict(schema_version=2, suite='ci.local.quick',
            producer='atomic-ci-local-quick-runner-v1', head=self.base,
            tree=self.git('rev-parse', 'HEAD^{tree}').strip())))
        self.git('switch', '-c', 'fix/scoped')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True, stderr=subprocess.DEVNULL)

    def write(self, path, text):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit(self, message):
        self.git('add', '--all')
        self.git('commit', '-m', message)

    def test_verified_main_ignores_unrelated_product_change(self):
        self.write('product.py', 'product = True\n')
        for kind in scope.AUTHORITY:
            result = scope.select_scope(self.root, kind)
            self.assertEqual(result.base, self.base)
            self.assertEqual(result.receipt, str(self.receipt))
        self.assertEqual(scope.changed_paths(self.root, self.base), ['product.py'])

    def test_registered_linked_worktree_receipt_is_reused_without_copy(self):
        linked = self.root / 'linked'
        self.git('worktree', 'add', '--detach', str(linked), self.base)
        directory = Path(subprocess.check_output(['git', '-C', str(linked), 'rev-parse',
            '--path-format=absolute', '--git-dir'], text=True).strip())
        receipt = directory / 'codex/evidence/ci.local.quick' / self.receipt.name
        receipt.parent.mkdir(parents=True)
        self.receipt.rename(receipt)
        for kind in scope.AUTHORITY:
            selected = scope.select_scope(self.root, kind)
            self.assertEqual(selected.base, self.base)
            self.assertEqual(selected.receipt, str(receipt))
        self.assertFalse(self.receipt.exists())
        payload = json.loads(receipt.read_text());payload['tree'] = 'a' * 40
        receipt.write_text(json.dumps(payload))
        self.assertIsNone(scope.select_scope(self.root, 'secrets').base)

    def test_unregistered_receipt_directory_and_symlink_are_not_authority(self):
        fake = self.root / '.git/worktrees/unregistered/codex/evidence/ci.local.quick' / self.receipt.name
        fake.parent.mkdir(parents=True);self.receipt.rename(fake)
        self.assertIsNone(scope.select_scope(self.root, 'secrets').base)
        self.receipt.symlink_to(fake)
        self.assertIsNone(scope.select_scope(self.root, 'secrets').base)

    def test_unrelated_daily_rule_change_reuses_but_scan_changes_invalidate(self):
        path = self.root / 'make/ci.mk';original = path.read_text()
        path.write_text(original.replace('ci.local.iteration: guard.prod.forbid',
                                        'ci.local.iteration: guard.prod.forbid agent.run.resume'))
        self.assertEqual(scope.select_scope(self.root, 'secrets').base, self.base)
        for changed in (original.replace('--scope all', '--scope worktree'),
                        original + 'SCANNER_MODE = unsafe\n',
                        original + 'ci.local.iteration: second\n',
                        original.replace('ci.local.iteration: guard.prod.forbid', 'ci.local.iteration: $(DYNAMIC)'),
                        original + 'ci.local.quick.run: ci.local.iteration\n'):
            path.write_text(changed)
            self.assertIsNone(scope.select_scope(self.root, 'secrets').base)

    def test_unreviewed_selection_refactor_and_coverage_changes_invalidate(self):
        path = self.root / 'scripts/ci/trusted_scan_scope.py';original = path.read_text()
        path.write_text(original.replace("return Scope(None, 'main_tree_evidence_missing')",
                                         "return Scope(None, 'evidence_lookup_missing')"))
        self.assertIsNone(scope.select_scope(self.root, 'secrets').base)
        for changed in (original.replace("'--reverse'", "'--first-parent'"),
                        original.replace("'--no-renames', '--name-only'", "'--name-only'"),
                        original + '\nUNKNOWN_SCAN_DEPENDENCY = True\n',
                        original + '\ndef new_scan_helper():\n    return True\n'):
            path.write_text(changed)
            self.assertIsNone(scope.select_scope(self.root, 'secrets').base)

    def test_trust_checks_and_registry_changes_invalidate(self):
        path = self.root / 'scripts/ci/trusted_scan_scope.py';original = path.read_text()
        for changed in (
            original.replace("git(root, 'merge-base', '--is-ancestor', base, 'HEAD')", 'pass'),
            original.replace('payload != expected', 'False'),
            original.replace('owner != common.resolve()', 'False'),
            original.replace("COMMON_AUTHORITY = ('scripts/ops/local_quick_evidence.py',)", 'COMMON_AUTHORITY = ()'),
            original.replace('EVIDENCE_SELECTION_MIGRATIONS = frozenset(', 'EVIDENCE_SELECTION_MIGRATIONS = set('),
        ):
            path.write_text(changed)
            self.assertIsNone(scope.select_scope(self.root, 'secrets').base)

    def test_exact_reviewed_legacy_transition_not_future_refactors(self):
        import re
        current = Path(scope.__file__).read_text()
        old = re.sub(r'^EVIDENCE_SELECTION_MIGRATIONS = .*\n', '', current, flags=re.M)
        old = old.replace("'main_tree_evidence_missing'", "'legacy_lookup_missing'")
        pair = (scope.selection_digest(old.encode()), scope.selection_digest(current.encode()))
        current = re.sub(r'^EVIDENCE_SELECTION_MIGRATIONS = .*$',
                         'EVIDENCE_SELECTION_MIGRATIONS = frozenset(' + repr([pair]) + ')', current, flags=re.M)
        with mock.patch.object(scope, 'EVIDENCE_SELECTION_MIGRATIONS', frozenset([pair])):
            self.assertTrue(scope.helper_authority_equal(old.encode(), current.encode()))
            changed = current.replace("git(root, 'merge-base', '--is-ancestor', base, 'HEAD')", 'pass')
            self.assertFalse(scope.helper_authority_equal(old.encode(), changed.encode()))

    def test_missing_or_tampered_receipt_falls_back(self):
        for payload in ('{}', '{broken', '[]'):
            self.receipt.write_text(payload)
            self.assertIsNone(scope.select_scope(self.root, 'secrets').base)
        self.receipt.unlink()
        self.assertEqual(scope.select_scope(self.root, 'secrets').reason, 'main_tree_evidence_missing')

    def test_wrong_receipt_tree_falls_back(self):
        payload = json.loads(self.receipt.read_text());payload['tree'] = 'a' * 40
        self.receipt.write_text(json.dumps(payload))
        self.assertIsNone(scope.select_scope(self.root, 'personal').base)

    def test_authority_invalidates_only_affected_scanner(self):
        self.write('scripts/ci/personal_data_false_positives.json', 'changed\n')
        self.assertIsNone(scope.select_scope(self.root, 'personal').base)
        self.assertIsNone(scope.select_scope(self.root, 'history').base)
        self.assertEqual(scope.select_scope(self.root, 'secrets').base, self.base)

    def test_common_authority_change_and_deletion_invalidate(self):
        for path in scope.COMMON_AUTHORITY:
            p = self.root / path
            original = p.read_text();p.unlink()
            self.assertIsNone(scope.select_scope(self.root, 'secrets').base)
            p.write_text(original)

    def test_nonancestor_main_and_untrusted_origin_fall_back(self):
        self.git('switch', 'main');self.write('main-only.txt', 'main\n');self.commit('advance main')
        new_main = self.git('rev-parse', 'HEAD').strip()
        self.git('update-ref', 'refs/remotes/origin/main', new_main)
        self.git('switch', 'fix/scoped')
        self.assertIsNone(scope.select_scope(self.root, 'secrets').base)
        self.git('remote', 'set-url', 'origin', 'https://example.invalid/untrusted')
        self.assertEqual(scope.select_scope(self.root, 'secrets').reason, 'untrusted_origin')

    def test_scheduled_audit_remains_full(self):
        with mock.patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'schedule'}):
            self.assertEqual(scope.select_scope(self.root, 'history').reason, 'scheduled_full_audit')

    def test_squash_receipt_requires_same_complete_tree(self):
        source = self.base
        self.git('commit', '--allow-empty', '-m', 'squash equivalent tree')
        merged = self.git('rev-parse', 'HEAD').strip()
        self.git('update-ref', 'refs/remotes/origin/main', merged)
        self.assertEqual(scope.select_scope(self.root, 'secrets').base, merged)
        self.assertEqual(json.loads(self.receipt.read_text())['head'], source)

    def test_intermediate_deleted_content_is_scanned(self):
        value = 'gh' + 'p_' + 'X' * 36
        self.write('temporary.txt', value);self.commit('add intermediate sensitive content')
        (self.root / 'temporary.txt').unlink();self.commit('remove intermediate file')
        self.assertEqual(scope.changed_paths(self.root, self.base), [])
        with mock.patch.object(secrets, 'ROOT', self.root):
            findings = secrets.history_findings(self.base)
        self.assertTrue(any('temporary.txt@' in row for row in findings))
        self.assertNotIn(value, str(findings))

    def test_renamed_reused_blob_and_intermediate_path_are_not_exempt(self):
        self.git('mv', 'old.txt', 'moved.txt');self.commit('rename existing blob')
        self.git('rm', 'moved.txt');self.commit('remove moved file')
        rows = scope.candidate_blobs(self.root, self.base)
        self.assertIn('moved.txt', [r[1] for r in rows])
        self.assertEqual(rows[0][0], self.git('rev-parse', self.base + ':old.txt').strip())

    def test_staged_unstaged_untracked_and_spaced_paths(self):
        self.write('old.txt', 'changed\n')
        self.write('staged.txt', 'stage\n');self.git('add', 'staged.txt')
        self.write('space file.txt', 'new\n')
        self.assertEqual(scope.changed_paths(self.root, self.base), ['old.txt', 'space file.txt', 'staged.txt'])

    def test_incremental_read_set_excludes_unchanged_main(self):
        self.write('new.txt', 'safe\n');self.commit('candidate')
        with mock.patch.object(personal, 'ROOT', self.root), mock.patch.object(personal, 'scan_text', wraps=personal.scan_text) as scan:
            self.assertEqual(personal.worktree_findings(self.base), [])
            self.assertEqual([c.args[1] for c in scan.call_args_list], ['new.txt'])
        with mock.patch.object(secrets, 'ROOT', self.root):
            self.assertEqual([p.name for p in secrets.worktree_files(self.base)], ['new.txt'])
        self.assertEqual([row[1] for row in scope.candidate_blobs(self.root, self.base)], ['new.txt'])

    def test_personal_data_in_intermediate_commit_is_rejected(self):
        self.write('person.txt', 'phone=' + '139' + '1234' + '5678')
        self.commit('candidate data');self.git('rm', 'person.txt');self.commit('delete data')
        with mock.patch.object(personal, 'ROOT', self.root):
            self.assertTrue(any(f.rule_id == 'PD002' for f in personal.history_findings(self.base)))


    def test_secret_cli_uses_incremental_scope_and_detects_untracked_value(self):
        self.write('new.txt', 'gh' + 'p_' + 'Y' * 36)
        with mock.patch.object(secrets, 'ROOT', self.root), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(secrets.main(['--scope', 'all', '--auto-trusted-base']), 1)

    def test_history_cli_does_not_reread_unchanged_main_blobs(self):
        self.write('new.txt', 'candidate safe content\n');self.commit('candidate')
        oid = self.git('rev-parse', 'HEAD:new.txt').strip()
        rules = {'allowed_remotes': {'origin': 'https://github.com/lidefend/sce-backend-odoo.git'}}
        with mock.patch.object(history, 'load_policy', return_value=rules), mock.patch.object(history, 'read_blob', wraps=history.read_blob) as read, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(history.main(['--root', str(self.root), '--auto-trusted-base']), 0)
        self.assertEqual({call.args[1] for call in read.call_args_list}, {oid})

    def test_history_cli_rejects_deleted_intermediate_sensitive_blob(self):
        self.write('bad.txt', 'gh' + 'p_' + 'Z' * 36);self.commit('bad intermediate')
        self.git('rm', 'bad.txt');self.commit('delete')
        rules = {'allowed_remotes': {'origin': 'https://github.com/lidefend/sce-backend-odoo.git'}}
        with mock.patch.object(history, 'load_policy', return_value=rules), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertNotEqual(history.main(['--root', str(self.root), '--auto-trusted-base']), 0)


    def test_custom_policy_and_authority_fallback_scan_full_history(self):
        rules = {'allowed_remotes': {'origin': 'https://github.com/lidefend/sce-backend-odoo.git'}}
        for custom in (True, False):
            with self.subTest(custom_policy=custom):
                args = ['--root', str(self.root), '--auto-trusted-base']
                if custom:
                    args += ['--policy', str(self.root / 'custom-policy.json')]
                with mock.patch.object(history, 'load_policy', return_value=rules), mock.patch.object(history, 'incremental_authority_changed', return_value=True), mock.patch.object(history, 'object_rows', wraps=history.object_rows) as full_scan, mock.patch.object(scope, 'candidate_blobs', wraps=scope.candidate_blobs) as incremental, contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(history.main(args), 0)
                    full_scan.assert_called_once()
                    incremental.assert_not_called()


if __name__ == '__main__':
    unittest.main()
