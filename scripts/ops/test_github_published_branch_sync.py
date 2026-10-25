import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from gitee_published_branch_sync import git, out, sync, CONFIRM
from github_published_branch_sync import INDEX, REPORTS, merge_index, resolve_metadata, verify_pr


def index(**branches):
    return {'schema_version': 1, 'branches': branches}


class IndexTests(unittest.TestCase):
    def test_independent_additions_and_deletion(self):
        self.assertEqual(merge_index(index(old='x'), index(ours='a'), index(old='x', theirs='b')),
                         index(ours='a', theirs='b'))

    def test_competing_assignments_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'competing'):
            merge_index(index(a='base'), index(a='ours'), index(a='theirs'))

    def test_unknown_schema_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'schema'):
            merge_index({}, index(), index())

    def test_pr_mismatch_rejected(self):
        for change in ({'state': 'CLOSED'}, {'headRefOid': 'b'*40},
                       {'baseRefName': 'release'}, {'isCrossRepository': True}):
            data = dict(state='OPEN', headRefName='fix/test', headRefOid='a'*40,
                        baseRefName='main', isCrossRepository=False)
            data.update(change)
            with patch('github_published_branch_sync.subprocess.run') as run:
                run.return_value.stdout = json.dumps(data)
                with self.assertRaisesRegex(RuntimeError, 'identity'):
                    verify_pr('.', 1, 'fix/test', 'a'*40)


class GithubSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'repo'
        self.root.mkdir()
        self.remote = str(Path(self.tmp.name) / 'remote.git')
        git(self.root, 'init', '-b', 'main')
        git(self.root, 'config', 'user.email', 'test@example.invalid')
        git(self.root, 'config', 'user.name', 'Test')
        for path in REPORTS | {INDEX}:
            p = self.root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(index(base='base')) if path == INDEX else 'base\n')
        self.commit()
        git(self.root, 'init', '--bare', self.remote)
        git(self.root, 'remote', 'add', 'origin', self.remote)
        git(self.root, 'switch', '-c', 'fix/test')
        (self.root / INDEX).write_text(json.dumps(index(base='base', ours='ours')))
        for path in REPORTS:
            (self.root / path).write_text('ours\n')
        self.head = self.commit()
        git(self.root, 'push', 'origin', 'fix/test')
        git(self.root, 'switch', 'main')
        (self.root / INDEX).write_text(json.dumps(index(base='base', theirs='theirs')))
        for path in REPORTS:
            (self.root / path).write_text('theirs\n')
        self.main = self.commit()
        git(self.root, 'push', 'origin', 'main')
        git(self.root, 'switch', 'fix/test')

    def commit(self):
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'fixture')
        return out(self.root, 'rev-parse', 'HEAD')

    def run_sync(self, **kw):
        return sync(self.root, 'fix/test', self.head, self.main,
                    remote='origin', allowed_urls={self.remote}, resolve_conflicts=resolve_metadata, **kw)

    def test_preview_does_not_merge(self):
        self.assertEqual(self.run_sync()['writes'], 0)
        self.assertEqual(out(self.root, 'rev-parse', 'HEAD'), self.head)

    def test_exact_metadata_merge_preserves_history_and_requires_regeneration(self):
        result = self.run_sync(apply=True, confirm=CONFIRM)
        self.assertEqual(out(self.root, 'show', '-s', '--format=%P', 'HEAD'), self.head+' '+self.main)
        self.assertEqual(json.loads((self.root / INDEX).read_text()), index(base='base', ours='ours', theirs='theirs'))
        self.assertTrue(result['generated_reports_refresh_required'])
        self.assertEqual(set(result['resolved_conflicts']), REPORTS | {INDEX})
        for report in REPORTS:
            self.assertEqual((self.root / report).read_text(), 'ours\n')
        self.assertEqual(out(self.root, 'ls-remote', 'origin', 'refs/heads/fix/test').split()[0], self.head)
        self.assertEqual(out(self.root, 'status', '--porcelain'), '')

    def test_competing_index_restores_original_candidate(self):
        git(self.root, 'switch', 'main')
        (self.root / INDEX).write_text(json.dumps(index(base='base', ours='different')))
        self.main = self.commit()
        git(self.root, 'push', 'origin', 'main')
        git(self.root, 'switch', 'fix/test')
        with self.assertRaisesRegex(RuntimeError, 'competing'):
            self.run_sync(apply=True, confirm=CONFIRM)
        self.assertEqual(out(self.root, 'rev-parse', 'HEAD'), self.head)
        self.assertEqual(out(self.root, 'status', '--porcelain'), '')

    def test_unapproved_conflict_restores_original_candidate(self):
        (self.root / 'business.txt').write_text('ours')
        self.head = self.commit()
        git(self.root, 'push', 'origin', 'fix/test')
        git(self.root, 'switch', 'main')
        (self.root / 'business.txt').write_text('theirs')
        self.main = self.commit()
        git(self.root, 'push', 'origin', 'main')
        git(self.root, 'switch', 'fix/test')
        with self.assertRaisesRegex(RuntimeError, 'unapproved'):
            self.run_sync(apply=True, confirm=CONFIRM)
        self.assertEqual(out(self.root, 'rev-parse', 'HEAD'), self.head)
        self.assertEqual(out(self.root, 'status', '--porcelain'), '')

    def test_remote_drift_during_resolution_aborts(self):
        with patch('gitee_published_branch_sync.remote_refs', side_effect=[
                {'refs/heads/main': self.main, 'refs/heads/fix/test': self.head},
                {'refs/heads/main': self.main, 'refs/heads/fix/test': self.head},
                {'refs/heads/main': 'f'*40, 'refs/heads/fix/test': self.head}]):
            with self.assertRaisesRegex(RuntimeError, 'drift'):
                self.run_sync(apply=True, confirm=CONFIRM)
        self.assertEqual(out(self.root, 'rev-parse', 'HEAD'), self.head)
        self.assertEqual(out(self.root, 'status', '--porcelain'), '')


if __name__ == '__main__':
    unittest.main()
