import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from scripts.ops import gitee_publication_scope as scope

class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.env={**os.environ,'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null'}
        self.git('init');(self.root/'readme.md').write_text('ordinary code');self.base=self.commit()
    def git(self,*a):return subprocess.check_output(['git','-C',str(self.root),*a],env=self.env,stderr=subprocess.DEVNULL).decode().strip()
    def commit(self):
        self.git('add','-A');self.git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','fixture');return self.git('rev-parse','HEAD')
    def audit(self,head,refs):
        with patch.object(scope,'ROOT',self.root),patch.object(scope,'digest_source',return_value={'test':'fixed'}):return scope.audit(head,refs)
    def test_deleted_historical_secret_is_scanned_without_value_output(self):
        token='ghp_'+'z'*36
        (self.root/'deleted.txt').write_text(token);middle=self.commit();(self.root/'deleted.txt').unlink();head=self.commit()
        r=self.audit(head,self.base+' refs/heads/main\n')
        self.assertIn(middle,r['new_commits']);self.assertEqual(r['new_blob_count'],1)
        self.assertEqual(r['new_contents'][0]['paths_absent_at_candidate'],['deleted.txt'])
        self.assertEqual(r['secret_findings'][0]['rules'],['github_ghp'])
        self.assertNotIn(token,str(r));self.assertEqual(r['publication'],'blocked')
    def test_blob_already_remote_not_new_exposure(self):
        (self.root/'other.md').write_text('existing remote content');head=self.commit()
        r=self.audit(head,head+' refs/heads/other\n'+self.base+' refs/heads/main\n')
        self.assertEqual(r['new_contents'],[]);self.assertEqual(r['new_commits'],[])
    def test_missing_ref_objects_fail_closed(self):
        with self.assertRaises(subprocess.CalledProcessError):self.audit(self.base,'a'*40+' refs/pull/1/MERGE\n')
    def test_binary_not_silently_skipped(self):
        (self.root/'asset.bin').write_bytes(b'\x00binary');head=self.commit();r=self.audit(head,self.base+' refs/heads/main\n')
        self.assertEqual(len(r['binary_review_pending']),1);self.assertEqual(r['new_blob_count'],1)
    def test_authoritative_customer_rule_is_reused(self):
        (self.root/'identity.txt').write_text(scope.CUSTOMER_IDENTITY_TOKENS[0]);head=self.commit()
        r=self.audit(head,self.base+' refs/heads/main\n')
        self.assertEqual(len(r['customer_reference_review']),1)
        self.assertEqual(r['publication'],'blocked')

if __name__=='__main__':unittest.main()
