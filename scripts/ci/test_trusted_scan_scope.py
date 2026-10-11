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
        os.environ.pop(scope.COVERAGE_ENV, None)
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
        # The make fixture declares all three governed scans through their own
        # unit prerequisites, plus the guard the history scan depends on, so the
        # digest's executable surface is exercised rather than assumed.
        self.write('make/ci.mk', (
            'ci.local.iteration: guard.prod.forbid\n\t@echo daily\n\n'
            'security.online_capture.unit:\n\t@python3 scripts/ci/test_trusted_scan_scope.py\n\n'
            'security.secrets.scan: security.online_capture.unit\n'
            '\t@python3 scripts/ci/secret_scan.py --scope all --auto-trusted-base\n\n'
            'security.personal_data.unit:\n\t@python3 scripts/ci/test_personal_data_scan.py\n\n'
            'security.personal_data_scan: security.personal_data.unit\n'
            '\t@python3 scripts/ci/personal_data_scan.py --scope all --auto-trusted-base\n\n'
            'repository.clean_history.scan: guard.prod.forbid\n'
            '\t@python3 scripts/verify/repository_clean_history_guard.py --auto-trusted-base\n'))
        self.write('make/guards.mk', 'IS_PROD = 0\n\nguard.prod.forbid:\n\t@test "$(IS_PROD)" != "1"\n')
        self.write('old.txt', 'baseline\n')
        self.commit('base')
        self.base = self.git('rev-parse', 'HEAD').strip()
        self.git('update-ref', 'refs/remotes/origin/main', self.base)
        self.receipt = self.root / '.git/codex/evidence/ci.local.quick' / (self.base + '.json')
        self.receipt.parent.mkdir(parents=True)
        self.receipt.write_text(json.dumps(dict(schema_version=3, suite='ci.local.quick',
            producer=scope.PRODUCER, head=self.base, coverage=scope.coverage_snapshot(self.root),
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

    def test_scanner_proof_requires_complete_actual_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            launch = {'root': str(self.root), 'head': self.git('rev-parse', 'HEAD').strip(),
                      'tree': self.git('rev-parse', 'HEAD^{tree}').strip(), 'coverage': scope.coverage_snapshot(self.root)}
            (folder / 'launch.json').write_text(json.dumps(launch))
            with mock.patch.dict(os.environ, {scope.COVERAGE_ENV: directory}), mock.patch.object(secrets, 'ROOT', self.root), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(secrets.main(['--scope', 'worktree']), 0)
                self.assertFalse((folder / 'secrets.json').exists())
                self.assertEqual(secrets.main(['--scope', 'all']), 0)
                proof = json.loads((folder / 'secrets.json').read_text())
                self.assertEqual(proof['mode'], 'full')
                self.assertIsNone(proof['base'])
                self.assertEqual(proof['coverage'], launch['coverage']['scanners']['secrets'])

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

    def test_governed_scan_declaration_change_invalidates(self):
        # Every way the command that decides coverage can move: the flag itself,
        # an added prerequisite, an appended recipe line, and a dropped recipe.
        path = self.root / 'make/ci.mk'; original = path.read_text()
        for changed in (
            original.replace('--scope all', '--scope worktree'),
            original.replace('security.secrets.scan: security.online_capture.unit',
                             'security.secrets.scan: security.online_capture.unit extra.gate'),
            original + 'security.secrets.scan:\n\t@echo smuggled\n',
            original.replace(
                '\t@python3 scripts/ci/secret_scan.py --scope all --auto-trusted-base\n', ''),
        ):
            path.write_text(changed)
            self.assertIsNone(scope.select_scope(self.root, 'secrets').base)
        path.write_text(original)
        self.assertEqual(scope.select_scope(self.root, 'secrets').base, self.base)

    def test_a_fragment_that_redefines_a_governed_target_invalidates(self):
        self.write('make/other.mk', 'security.secrets.scan: injected.gate\n')
        self.assertIsNone(scope.select_scope(self.root, 'secrets').base)
        self.write('make/other.mk', 'unrelated = true\n')
        self.assertEqual(scope.select_scope(self.root, 'secrets').base, self.base)

    def test_unrelated_make_region_or_fragment_is_reused(self):
        # The over-invalidation this replaces: any make byte used to force a full
        # rescan of all three kinds, so a stable scan was repaid on every edit.
        path = self.root / 'make/ci.mk'; original = path.read_text()
        path.write_text(original + 'UNRELATED_FLAG = unsafe\n')
        self.assertEqual(scope.select_scope(self.root, 'secrets').base, self.base)
        path.write_text(original)
        self.write('make/unrelated-fragment.mk', 'another = true\n')
        self.assertEqual(scope.select_scope(self.root, 'secrets').base, self.base)

    def test_referenced_variable_change_invalidates_only_its_own_kind(self):
        # guard.prod.forbid's recipe reads $(IS_PROD), so the variable is part of
        # the history surface -- and only the history surface.
        path = self.root / 'make/guards.mk'
        path.write_text(path.read_text().replace('IS_PROD = 0', 'IS_PROD = 1'))
        self.assertIsNone(scope.select_scope(self.root, 'history').base)
        self.assertEqual(scope.select_scope(self.root, 'secrets').base, self.base)
        path.write_text(path.read_text().replace('IS_PROD = 1', 'IS_PROD = 0'))
        self.assertEqual(scope.select_scope(self.root, 'history').base, self.base)

    def test_macro_fragment_naming_a_governed_target_is_bound_whole(self):
        # An $(eval)/define body can append to a governed recipe without being a
        # rule the parser can see, so such a fragment is bound by content.
        path = self.root / 'make/generated.mk'
        path.write_text('define APPEND\nsecurity.secrets.scan: extra.gate\nendef\n$(eval $(APPEND))\n')
        self.assertIsNone(scope.select_scope(self.root, 'secrets').base)
        path.write_text('define APPEND\nsecurity.secrets.scan: other.gate\nendef\n$(eval $(APPEND))\n')
        self.assertIsNone(scope.select_scope(self.root, 'secrets').base)
        path.unlink()
        self.assertEqual(scope.select_scope(self.root, 'secrets').base, self.base)

    def test_selector_and_producer_changes_invalidate(self):
        for relative in scope.COMMON_AUTHORITY:
            path = self.root / relative; original = path.read_text()
            path.write_text(original + '\n# authority changed\n')
            self.assertIsNone(scope.select_scope(self.root, 'secrets').base)
            path.write_text(original)

    def test_legacy_schema2_is_not_coverage(self):
        payload = json.loads(self.receipt.read_text())
        payload.pop('coverage'); payload.update(schema_version=2, producer='atomic-ci-local-quick-runner-v1')
        self.receipt.write_text(json.dumps(payload))
        self.assertIsNone(scope.select_scope(self.root, 'secrets').base)
        self.assertIsNone(scope.select_scope(self.root, 'history').base)

    def test_closest_valid_ancestor_not_filename_or_modification_time(self):
        self.write('new.txt', 'safe'); self.commit('closer ancestor')
        closer = self.git('rev-parse', 'HEAD').strip()
        path = self.receipt.with_name(closer + '.json')
        path.write_text(json.dumps(dict(schema_version=3, suite='ci.local.quick', producer=scope.PRODUCER,
            head=closer, tree=self.git('rev-parse', 'HEAD^{tree}').strip(), coverage=scope.coverage_snapshot(self.root))))
        self.write('next.txt', 'next'); self.commit('candidate')
        self.assertEqual(scope.select_scope(self.root, 'secrets').base, closer)
        payload = json.loads(path.read_text()); payload['producer'] = 'forged'
        path.write_text(json.dumps(payload))
        self.assertEqual(scope.select_scope(self.root, 'secrets').base, self.base)

    def test_intermediate_authority_change_then_restore_is_full(self):
        path = self.root / 'scripts/ci/secret_scan.py'; original = path.read_text()
        path.write_text('weakened'); self.commit('change scanner')
        path.write_text(original); self.commit('restore scanner')
        self.assertIsNone(scope.select_scope(self.root, 'secrets').base)
        self.assertEqual(scope.select_scope(self.root, 'personal').base, self.base)

    def test_missing_or_tampered_receipt_falls_back(self):
        for payload in ('{}', '{broken', '[]'):
            self.receipt.write_text(payload)
            self.assertIsNone(scope.select_scope(self.root, 'secrets').base)
        self.receipt.unlink()
        self.assertEqual(scope.select_scope(self.root, 'secrets').reason, 'verified_coverage_receipt_missing')

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
        self.assertEqual(scope.select_scope(self.root, 'secrets').base, source)
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
                    self.assertTrue(all(call.args[1] is None for call in incremental.call_args_list))


    def test_nonancestor_same_tree_receipt_never_proves_history(self):
        self.git('switch', '-c', 'side', self.base); self.git('commit', '--allow-empty', '-m', 'side')
        side = self.git('rev-parse', 'HEAD').strip()
        payload = dict(schema_version=3, suite='ci.local.quick', producer=scope.PRODUCER,
            head=side, tree=self.git('rev-parse', 'HEAD^{tree}').strip(), coverage=scope.coverage_snapshot(self.root))
        self.receipt.unlink(); self.receipt.with_name(side + '.json').write_text(json.dumps(payload))
        self.git('switch', 'fix/scoped')
        self.assertIsNone(scope.select_scope(self.root, 'history').base)

    def test_public_sidebranch_and_stash_scope_occurrences(self):
        self.git('switch', '-c', 'side', self.base)
        self.write('side secret.txt', 'gh' + 'p_' + 'S' * 36); self.commit('add side sensitive')
        self.git('rm', 'side secret.txt'); self.commit('remove side sensitive')
        self.git('tag', 'side-tag')
        self.git('switch', 'fix/scoped')
        for kind in scope.AUTHORITY:
            rows = scope.candidate_blobs(self.root, self.base, scope.revision_args(kind))
            self.assertIn('side secret.txt', [row[1] for row in rows])
        with mock.patch.object(secrets, 'ROOT', self.root):
            self.assertTrue(any('side secret.txt@' in row for row in secrets.history_findings(self.base)))
        self.write('stash-only.txt', 'safe stash'); self.git('add', 'stash-only.txt'); self.git('stash', 'push')
        self.assertIn('stash-only.txt', [row[1] for row in scope.candidate_blobs(self.root, self.base, scope.revision_args('secrets'))])
        self.assertNotIn('stash-only.txt', [row[1] for row in scope.candidate_blobs(self.root, self.base, scope.revision_args('history'))])

    def test_batched_occurrences_equal_per_commit_oracle(self):
        self.git('switch', '-c', 'side', self.base)
        self.write('space side.txt', 'branch'); self.commit('side')
        self.git('switch', 'fix/scoped')
        self.git('mv', 'old.txt', 'renamed file.txt'); self.commit('move reused blob')
        self.write('temporary.txt', 'temporary'); self.commit('add')
        self.git('rm', 'temporary.txt'); self.commit('remove')
        self.git('merge', '--no-ff', 'side', '-m', 'merge')
        expected = set()
        for commit in self.git('rev-list', self.base + '..HEAD').splitlines():
            paths = self.git('diff-tree', '--root', '-m', '--no-commit-id', '--no-renames', '--name-only', '-r', '-z', '--diff-filter=ACMRT', commit).split('\0')
            for path in filter(None, paths):
                for row in self.git('ls-tree', '-r', '-l', '-z', commit, '--', path).split('\0'):
                    if not row: continue
                    meta, name = row.split('\t', 1); _, typ, oid, size = meta.split()
                    if typ == 'blob': expected.add((oid, name, int(size)))
        self.assertEqual(set(scope.candidate_blobs(self.root, self.base)), expected)

    def test_full_scanners_fail_closed_on_noncommit_blob_and_tree_tags(self):
        content = 'gh' + 'p_' + 'Z' * 36 + '\nphone=' + '139' + '1234' + '5678'
        oid = subprocess.check_output(['git', '-C', str(self.root), 'hash-object', '-w', '--stdin'], input=content, text=True).strip()
        tree = subprocess.check_output(['git', '-C', str(self.root), 'mktree'], input='100644 blob ' + oid + '\tunsafe.txt\n', text=True).strip()
        for target in (oid, tree):
            with self.subTest(target=target):
                self.git('update-ref', 'refs/tags/noncommit-fixture', target)
                for module, args in ((secrets, ['--scope', 'all']), (personal, ['--scope', 'all'])):
                    with mock.patch.object(module, 'ROOT', self.root), contextlib.redirect_stdout(io.StringIO()):
                        with self.assertRaisesRegex(ValueError, 'unsupported noncommit scan reference'):
                            module.main(args)
                rules = {'allowed_remotes': {'origin': 'https://github.com/lidefend/sce-backend-odoo.git'}}
                with mock.patch.object(history, 'load_policy', return_value=rules), contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(ValueError, 'unsupported noncommit scan reference'):
                        history.main(['--root', str(self.root)])

    def test_noncommit_tag_requires_full_and_proof_tampering_rejected(self):
        oid = self.git('rev-parse', 'HEAD:old.txt').strip(); self.git('tag', 'blob-tag', oid)
        self.assertIsNone(scope.select_scope(self.root, 'history').base)
        self.git('tag', '-d', 'blob-tag')
        payload = json.loads(self.receipt.read_text())
        payload['coverage']['scanners']['history']['authority'] = 'a' * 64
        self.receipt.write_text(json.dumps(payload))
        self.assertIsNone(scope.select_scope(self.root, 'history').base)

if __name__ == '__main__':
    unittest.main()
