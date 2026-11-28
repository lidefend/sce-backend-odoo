from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts.ops import close_superseded_pr as tool


class CloseIdentityTests(unittest.TestCase):
    def setUp(self):
        self.old = dict(number=1, state='OPEN', isDraft=True, headRefName='fix/old', headRefOid='a'*40, isCrossRepository=False)
        self.new = dict(number=2, state='MERGED', baseRefName='main', mergeCommit={'oid':'b'*40}, isCrossRepository=False)
        self.entry = SimpleNamespace(branch='fix/old', remote_sha='a'*40)

    def verify(self, old, new, ancestor=True):
        with patch.object(tool.retirement, 'is_ancestor', return_value=ancestor):
            tool.validate_prs(old, new, self.entry, 'c'*40, Path('.'))

    def test_exact_superseded_identity(self):
        self.verify(self.old, self.new)
        self.old['state'] = 'CLOSED'
        self.verify(self.old, self.new)

    def test_independent_identity_failures(self):
        for field, value in [('state','MERGED'), ('isDraft',False), ('headRefName','fix/other'), ('headRefOid','d'*40), ('isCrossRepository',True)]:
            with self.subTest(field=field):
                old = dict(self.old, **{field:value})
                with self.assertRaises(tool.retirement.RetirementError): self.verify(old, self.new)
        for field, value in [('number',1), ('state','OPEN'), ('baseRefName','develop'), ('mergeCommit',None), ('isCrossRepository',True)]:
            with self.subTest(field=field):
                new = dict(self.new, **{field:value})
                with self.assertRaises(tool.retirement.RetirementError): self.verify(self.old, new)

    def test_unknown_or_absent_ancestry_denied(self):
        for value in (False, None):
            with self.assertRaises(tool.retirement.RetirementError): self.verify(self.old, self.new, value)

class ArchiveOrderingTests(unittest.TestCase):
    def test_bundle_failure_prevents_close(self):
        import tempfile
        from contextlib import ExitStack
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            args = SimpleNamespace(manifest=root/'manifest', manifest_sha256='digest', expected_main='c'*40,
                                   pr=1, replacement=2, apply=True, confirm='ARCHIVE_AND_CLOSE_SUPERSEDED_PR',
                                   bundle=root/'recovery.bundle', report=root/'report.json')
            entry = SimpleNamespace(branch='fix/old', remote_sha='a'*40)
            stack.enter_context(patch.object(tool.retirement, 'load_manifest', return_value=({'repository':{'origin_url':'origin'}},(entry,))))
            stack.enter_context(patch.object(tool.retirement, 'manifest_digest', return_value='digest'))
            stack.enter_context(patch.object(tool.retirement, 'run_git', return_value=SimpleNamespace(stdout='origin')))
            stack.enter_context(patch.object(tool.retirement, 'remote_main_sha', return_value='c'*40))
            stack.enter_context(patch.object(tool.retirement, 'github_open_branches', return_value={'fix/old'}))
            stack.enter_context(patch.object(tool.retirement, 'assess_entries', return_value=(SimpleNamespace(reasons=('branch has an open pull request',)),)))
            stack.enter_context(patch.object(tool, 'validate_prs'))
            fake_gh = stack.enter_context(patch.object(tool, 'gh', return_value='{}'))
            stack.enter_context(patch.object(tool.retirement, 'create_recovery_bundle', side_effect=tool.retirement.RetirementError('unrecoverable')))
            with self.assertRaisesRegex(tool.retirement.RetirementError, 'unrecoverable'):
                tool.execute(args, root)
            self.assertFalse(any('close' in call.args for call in fake_gh.call_args_list))
            self.assertFalse(args.report.exists())
