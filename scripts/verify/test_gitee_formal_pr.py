import tempfile
import json
import os
import subprocess
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from scripts.ops.gitee_formal_pr import ensure, select

class PRTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.ledger=Path(self.tmp.name)/'ledger'
        self.api=Mock();self.api.call.return_value=[];self.reader=Mock()
        self.reader.get.side_effect=[{'commit':{'sha':'a'*40}},{'commit':{'sha':'b'*40},'protected':True}]
    def test_preview_never_creates(self):
        result=ensure(self.api,self.reader,'a'*40,'b'*40,self.ledger)
        self.assertEqual(result['writes'],0);self.assertFalse(self.ledger.exists());self.api.call.assert_called_once_with('GET','/pulls?state=open&per_page=100')
    def test_changed_sha_stops_before_create(self):
        with self.assertRaises(ValueError):ensure(self.api,self.reader,'c'*40,'b'*40,self.ledger,True)
        self.api.call.assert_not_called()
    def test_uncertain_create_has_durable_no_retry_marker(self):
        self.api.call.side_effect=[[],RuntimeError('lost response')]
        with self.assertRaises(RuntimeError):ensure(self.api,self.reader,'a'*40,'b'*40,self.ledger,True)
        self.assertTrue(self.ledger.exists())
    @patch('scripts.ops.gitee_formal_pr.os.fsync',side_effect=OSError('disk failure'))
    def test_failed_ledger_sync_prevents_post(self,sync):
        with self.assertRaises(OSError):ensure(self.api,self.reader,'a'*40,'b'*40,self.ledger,True)
        self.api.call.assert_called_once_with('GET','/pulls?state=open&per_page=100')

    def test_previous_uncertain_create_not_posted_again(self):
        self.ledger.write_text('creating')
        with self.assertRaises(ValueError):ensure(self.api,self.reader,'a'*40,'b'*40,self.ledger,True)
        self.api.call.assert_called_once_with('GET','/pulls?state=open&per_page=100')
    def test_incomplete_listing_rejected(self):
        with self.assertRaises(ValueError):select([{}]*100)

    def test_topic_preview_uses_explicit_metadata(self):
        result=ensure(self.api,self.reader,'a'*40,'b'*40,self.ledger,branch='feature/project-profile',title='fix: profile validation',body='Real business acceptance.\nSecond paragraph.')
        self.assertEqual(result['branch'],'feature/project-profile')
        self.assertEqual(result['title'],'fix: profile validation')
        self.assertIn('\n',result['body'])
        self.reader.get.assert_any_call('/branches/feature%2Fproject-profile')

    def test_topic_create_and_readback_bind_same_identity(self):
        self.api.call.side_effect=[[],{'number':42}]
        with patch('scripts.ops.gitee_formal_pr.observe',return_value={'verified':True}) as observe:
            result=ensure(self.api,self.reader,'a'*40,'b'*40,self.ledger,True,branch='feature/project-profile',title='fix: profile',body='Acceptance evidence')
        self.api.call.assert_called_with('POST','/pulls',{'title':'fix: profile','head':'feature/project-profile','base':'main','body':'Acceptance evidence','prune_source_branch':'false','draft':'false'})
        observe.assert_called_once_with(self.reader,number=42,source='feature/project-profile',head='a'*40,base='b'*40)
        self.assertEqual(result['status'],'created')

    def test_invalid_topic_or_metadata_never_reaches_api(self):
        for branch,title,body in [('main','Title','Body'),('feature/../main','Title','Body'),('feature/a',' ','Body'),('feature/a','Title\nInjected','Body'),('feature/a','Title',' ')]:
            with self.subTest(branch=branch,title=title,body=body),self.assertRaises((ValueError, subprocess.CalledProcessError)):
                ensure(self.api,self.reader,'a'*40,'b'*40,self.ledger,True,branch=branch,title=title,body=body)
        self.api.call.assert_not_called();self.reader.get.assert_not_called()

    def test_selection_does_not_reuse_other_topic(self):
        rows=[{'number':1,'head':{'ref':'fix/gitee-temporary-integration-v1'},'base':{'ref':'main'}}, {'number':2,'head':{'ref':'feature/project-profile'},'base':{'ref':'main'}}]
        self.assertEqual(select(rows,'feature/project-profile')['number'],2)

    def test_make_wrapper_passes_metadata_as_literal_arguments(self):
        root=Path(__file__).resolve().parents[2]
        folder=Path(self.tmp.name)
        capture=folder/'argv.json'
        marker=folder/'must-not-exist'
        fake=folder/'python3'
        fake.write_text('#!'+sys.executable+'\nimport json,sys\nfrom pathlib import Path\nPath('+repr(str(capture))+').write_text(json.dumps(sys.argv[1:]))\n')
        fake.chmod(0o700)
        guard=folder/'guard.mk';guard.write_text('guard.prod.forbid:\n\t@true\n')
        # Dollar is escaped for Make; the resulting shell argument must remain
        # literal even when it contains substitution syntax and quoted text.
        title='Title "quoted" `touch '+str(marker)+'` $$(touch '+str(marker)+')'
        branch='feature/literal"`touch '+str(marker)+'`'
        body='body "quoted" `touch '+str(marker)+'`'
        env={**os.environ,'PATH':str(folder)+os.pathsep+os.environ['PATH']}
        subprocess.run(['make','--no-print-directory','-f','make/codex.mk','-f',str(guard),'gitee.ci.pr.create','GITEE_PR_TITLE='+title,'GITEE_SOURCE_BRANCH='+branch,'GITEE_PR_BODY_FILE='+body],cwd=root,env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        args=json.loads(capture.read_text())
        self.assertEqual(args[args.index('--title')+1],title.replace('$$','$'))
        self.assertEqual(args[args.index('--source-branch')+1],branch)
        self.assertEqual(args[args.index('--body-file')+1],body)
        self.assertFalse(marker.exists())

if __name__=='__main__':unittest.main()
